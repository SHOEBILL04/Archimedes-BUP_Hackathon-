"""Integrated Optimization Workstream Engine & Pipeline Facade.

Integrates the optimization workstream components:
    validated directives
    ↓
    directive preprocessing (compiler)
    ↓
    optimization input
    ↓
    LP optimizer (PuLP + CBC)
    ↓
    candidate schedule
    ↓
    independent replay validator
    ↓
    final optimization result

Guarantees:
- Pure deterministic execution across all pipeline stages.
- Replay validation is executed independently after solving.
- Never returns a schedule that fails replay validation.
- Never manufactures fallback or synthetic values to hide optimizer failures.
- Provides a clean, typed boundary for the orchestration layer.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from app.services.optimizer.exceptions import (
    OptimizationInfeasibleError,
    OptimizationTimeoutError,
    SolverExecutionError,
)
from app.services.optimizer.interface import IOptimizer
from app.services.optimizer.models import (
    HOURS_IN_DAY,
    BatteryConfig,
    CompiledDirectives,
    HourlyScheduleOutput,
    NormalizedDirective,
    OptimizationInput,
    OptimizationResult,
    SolverStatus,
)
from app.services.optimizer.pulp_solver import PuLpEnergyOptimizer
from app.services.validation.compiler import DeterministicDirectiveCompiler
from app.services.validation.deterministic_replay_validator import DeterministicReplayValidator
from app.services.validation.exceptions import ReplayValidationError
from app.services.validation.interface import IDirectiveCompiler, IReplayValidator

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Pipeline Input & Result Contracts
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class OptimizationPipelineInput:
    """Input specification provided to the integrated optimization pipeline."""

    demand_kwh: list[float]
    base_solar_kwh: list[float]
    tariff_bdt_per_kwh: list[float]
    battery: BatteryConfig
    directives: list[NormalizedDirective] = field(default_factory=list)
    solver_timeout_seconds: float = 10.0
    tolerance: float = 1e-4
    enforce_eod_neutrality: bool = True
    strict: bool = False

    def __post_init__(self) -> None:
        for name, arr in [
            ("demand_kwh", self.demand_kwh),
            ("base_solar_kwh", self.base_solar_kwh),
            ("tariff_bdt_per_kwh", self.tariff_bdt_per_kwh),
        ]:
            if len(arr) != HOURS_IN_DAY:
                raise ValueError(
                    f"{name} must contain exactly {HOURS_IN_DAY} hourly values, got {len(arr)}"
                )
            for idx, val in enumerate(arr):
                if (
                    not isinstance(val, (int, float))
                    or isinstance(val, bool)
                    or not math.isfinite(float(val))
                ):
                    raise ValueError(f"{name}[{idx}] must be a finite number, got {val}")
                if float(val) < 0.0:
                    raise ValueError(f"{name}[{idx}] cannot be negative, got {val}")

    @classmethod
    def from_arrays(
        cls,
        demand_kwh: list[float],
        base_solar_kwh: list[float],
        tariff_bdt_per_kwh: list[float],
        battery: BatteryConfig,
        directives: list[NormalizedDirective] | None = None,
        solver_timeout_seconds: float = 10.0,
        tolerance: float = 1e-4,
        enforce_eod_neutrality: bool = True,
        strict: bool = False,
    ) -> OptimizationPipelineInput:
        """Create a pipeline input payload from raw arrays and battery specification."""
        return cls(
            demand_kwh=demand_kwh,
            base_solar_kwh=base_solar_kwh,
            tariff_bdt_per_kwh=tariff_bdt_per_kwh,
            battery=battery,
            directives=directives or [],
            solver_timeout_seconds=solver_timeout_seconds,
            tolerance=tolerance,
            enforce_eod_neutrality=enforce_eod_neutrality,
            strict=strict,
        )


@dataclass(frozen=True)
class OptimizationPipelineResult:
    """Final, audited outcome of the integrated optimization and validation pipeline."""

    success: bool
    status: SolverStatus
    message: str
    schedule: list[HourlyScheduleOutput] = field(default_factory=list)
    total_grid_kwh: float = 0.0
    total_grid_cost_bdt: float = 0.0
    objective_value: float = 0.0
    optimization_result: OptimizationResult | None = None
    validation_result: Any | None = None
    compiled_directives: CompiledDirectives | None = None
    errors: list[str] = field(default_factory=list)
    execution_time_seconds: float = 0.0

    @property
    def is_success(self) -> bool:
        """Return True if both optimization solved and replay validation verified."""
        return self.success

    @property
    def is_valid(self) -> bool:
        """Return True if candidate schedule verified against replay physics."""
        return self.validation_result.is_valid if self.validation_result else False

    @property
    def is_optimal(self) -> bool:
        """Return True if solver found mathematically optimal solution."""
        return self.status == SolverStatus.OPTIMAL

    @property
    def total_cost(self) -> float:
        """Total grid electricity expenditure in BDT."""
        return self.total_grid_cost_bdt

    def to_dict(self) -> dict[str, Any]:
        """Convert pipeline outcome to a JSON-serializable dictionary."""
        return {
            "success": self.success,
            "status": self.status.value,
            "message": self.message,
            "total_grid_kwh": self.total_grid_kwh,
            "total_grid_cost_bdt": self.total_grid_cost_bdt,
            "objective_value": self.objective_value,
            "execution_time_seconds": self.execution_time_seconds,
            "schedule": [asdict(s) for s in self.schedule],
            "errors": self.errors,
            "verified": self.is_valid,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 2. Integrated Optimization Engine Facade
# ─────────────────────────────────────────────────────────────────────────────


class OptimizationEngine:
    """Internal service facade coordinating directive preprocessing, LP solving, and validation."""

    def __init__(
        self,
        solver: IOptimizer | None = None,
        validator: IReplayValidator | None = None,
        compiler: IDirectiveCompiler | None = None,
    ) -> None:
        self.solver = solver or PuLpEnergyOptimizer()
        self.validator = validator or DeterministicReplayValidator()
        self.compiler = compiler or DeterministicDirectiveCompiler()

    def optimize_and_validate(
        self,
        pipeline_input: OptimizationPipelineInput | OptimizationInput,
        solver_timeout_seconds: float | None = None,
        tolerance: float | None = None,
        enforce_eod_neutrality: bool | None = None,
        strict: bool | None = None,
    ) -> OptimizationPipelineResult:
        """Execute the end-to-end deterministic energy dispatch pipeline.

        Pipeline stages:
          1. Ingest structured input.
          2. Apply deterministic directive preprocessing (effective solar, reserve, rate bounds).
          3. Formulate OptimizationInput payload.
          4. Solve 24-hour cost-minimization LP with PuLP + CBC.
          5. Retrieve candidate dispatch schedule.
          6. Independently audit candidate schedule with deterministic replay physics simulator.
          7. If solver or validation fails: return structured failure without manufactured values.
          8. If verified: return schedule, costs, and audit proofs.

        Args:
            pipeline_input: Input scenario parameters and validated directives.
            solver_timeout_seconds: Optional override for CBC solver timeout.
            tolerance: Optional override for floating-point validation threshold.
            enforce_eod_neutrality: Optional override for end-of-day battery neutrality.
            strict: If True, raises exceptions on failure instead of returning structured result.

        Returns:
            OptimizationPipelineResult with full schedule, objective value, and audit status.
        """
        start_time = time.perf_counter()

        # Step 1: Input unpacking and parameter resolution
        if isinstance(pipeline_input, OptimizationPipelineInput):
            demand = pipeline_input.demand_kwh
            solar = pipeline_input.base_solar_kwh
            tariff = pipeline_input.tariff_bdt_per_kwh
            battery = pipeline_input.battery
            directives = pipeline_input.directives
            timeout = (
                solver_timeout_seconds
                if solver_timeout_seconds is not None
                else pipeline_input.solver_timeout_seconds
            )
            tol = tolerance if tolerance is not None else pipeline_input.tolerance
            eod_neutral = (
                enforce_eod_neutrality
                if enforce_eod_neutrality is not None
                else pipeline_input.enforce_eod_neutrality
            )
            is_strict = strict if strict is not None else pipeline_input.strict
            compiled_premade = None
        elif isinstance(pipeline_input, OptimizationInput):
            demand = pipeline_input.energy_profile.demand_kwh
            solar = pipeline_input.energy_profile.base_solar_kwh
            tariff = pipeline_input.energy_profile.tariff_bdt_per_kwh
            battery = pipeline_input.battery
            directives = []
            compiled_premade = pipeline_input.compiled_directives
            timeout = solver_timeout_seconds or 10.0
            tol = tolerance or 1e-4
            eod_neutral = enforce_eod_neutrality if enforce_eod_neutrality is not None else True
            is_strict = strict if strict is not None else False
        else:
            err_msg = f"Unsupported input type '{type(pipeline_input).__name__}'"
            if is_strict:
                raise ValueError(err_msg)
            return OptimizationPipelineResult(
                success=False,
                status=SolverStatus.ERROR,
                message=err_msg,
                errors=[err_msg],
            )

        # Step 2 & 3: Directive preprocessing and effective solar calculation
        if compiled_premade is not None:
            compiled = compiled_premade
        else:
            try:
                compiled = self.compiler.compile(
                    directives=directives,
                    base_solar=solar,
                    battery=battery,
                )
            except Exception as e:
                err_msg = f"Deterministic directive preprocessing failed: {e}"
                logger.error(err_msg, exc_info=True)
                if is_strict:
                    raise
                return OptimizationPipelineResult(
                    success=False,
                    status=SolverStatus.ERROR,
                    message=err_msg,
                    errors=[str(e)],
                    execution_time_seconds=time.perf_counter() - start_time,
                )

        # Step 4: Build solver input
        try:
            opt_input = OptimizationInput.from_arrays(
                demand_kwh=demand,
                base_solar_kwh=solar,
                tariff_bdt_per_kwh=tariff,
                battery=battery,
                compiled_directives=compiled,
            )
        except Exception as e:
            err_msg = f"Failed to construct OptimizationInput: {e}"
            logger.error(err_msg, exc_info=True)
            if is_strict:
                raise
            return OptimizationPipelineResult(
                success=False,
                status=SolverStatus.ERROR,
                message=err_msg,
                compiled_directives=compiled,
                errors=[str(e)],
                execution_time_seconds=time.perf_counter() - start_time,
            )

        # Step 5: Solve with PuLP + CBC
        try:
            opt_result: OptimizationResult = self.solver.solve(
                opt_input=opt_input,
                timeout_seconds=timeout,
                raise_on_error=is_strict,
            )
        except (OptimizationInfeasibleError, OptimizationTimeoutError, SolverExecutionError) as e:
            logger.warning("Optimization solver raised known solver exception: %s", e)
            if is_strict:
                raise
            status_map = {
                OptimizationInfeasibleError: SolverStatus.INFEASIBLE,
                OptimizationTimeoutError: SolverStatus.TIMEOUT,
                SolverExecutionError: SolverStatus.ERROR,
            }
            mapped_status = status_map.get(type(e), SolverStatus.ERROR)
            return OptimizationPipelineResult(
                success=False,
                status=mapped_status,
                message=str(e),
                compiled_directives=compiled,
                errors=[str(e)],
                execution_time_seconds=time.perf_counter() - start_time,
            )
        except Exception as e:
            logger.error("Unexpected error in LP solver: %s", e, exc_info=True)
            if is_strict:
                raise
            return OptimizationPipelineResult(
                success=False,
                status=SolverStatus.ERROR,
                message=f"Solver execution encountered unexpected error: {e}",
                compiled_directives=compiled,
                errors=[str(e)],
                execution_time_seconds=time.perf_counter() - start_time,
            )

        # Check solver status
        if opt_result.solver_status != SolverStatus.OPTIMAL:
            msg = (
                opt_result.message
                or f"Optimization solver terminated with status {opt_result.solver_status.value}"
            )
            logger.warning("Optimization failed solver status check: %s", msg)
            return OptimizationPipelineResult(
                success=False,
                status=opt_result.solver_status,
                message=msg,
                schedule=[],  # Rule: never manufacture fallback values
                total_grid_kwh=0.0,
                total_grid_cost_bdt=0.0,
                objective_value=0.0,
                optimization_result=opt_result,
                compiled_directives=compiled,
                errors=[msg],
                execution_time_seconds=opt_result.execution_time_seconds,
            )

        # Step 6 & 7: Independent replay validation of candidate schedule
        candidate_schedule = opt_result.schedule
        val_result = self.validator.validate(
            opt_input=opt_input,
            schedule=candidate_schedule,
            reported_total_cost=opt_result.total_grid_cost_bdt,
            tolerance=tol,
            enforce_eod_neutrality=eod_neutral,
            strict=False,
        )

        # Step 8: Validation failure handling
        # Rule: Never return a schedule that fails replay validation. Never manufacture fallback values.
        if not val_result.is_valid:
            err_msg = (
                f"Candidate schedule failed independent replay validation "
                f"({len(val_result.violations)} violation(s)). First: {val_result.violations[0]}"
            )
            logger.error("Replay validation rejected candidate schedule: %s", err_msg)
            if is_strict:
                raise ReplayValidationError(err_msg, details={"violations": val_result.violations})

            return OptimizationPipelineResult(
                success=False,
                status=SolverStatus.ERROR,
                message=err_msg,
                schedule=[],  # Rule: reject invalid schedule completely
                total_grid_kwh=0.0,
                total_grid_cost_bdt=0.0,
                objective_value=0.0,
                optimization_result=opt_result,
                validation_result=val_result,
                compiled_directives=compiled,
                errors=val_result.violations,
                execution_time_seconds=opt_result.execution_time_seconds,
            )

        # Step 9: Success - return verified schedule and objective information
        elapsed = time.perf_counter() - start_time
        return OptimizationPipelineResult(
            success=True,
            status=SolverStatus.OPTIMAL,
            message="Optimal energy dispatch computed and verified via independent deterministic replay.",
            schedule=opt_result.schedule,
            total_grid_kwh=opt_result.total_grid_kwh,
            total_grid_cost_bdt=opt_result.total_grid_cost_bdt,
            objective_value=opt_result.objective_value,
            optimization_result=opt_result,
            validation_result=val_result,
            compiled_directives=compiled,
            errors=[],
            execution_time_seconds=round(elapsed, 4),
        )

    def optimize_arrays(
        self,
        demand: list[float],
        base_solar: list[float],
        tariff: list[float],
        battery: BatteryConfig,
        directives: list[NormalizedDirective] | None = None,
        solver_timeout_seconds: float = 10.0,
        tolerance: float = 1e-4,
        enforce_eod_neutrality: bool = True,
        strict: bool = False,
    ) -> OptimizationPipelineResult:
        """Convenience method accepting raw arrays and battery specification."""
        p_input = OptimizationPipelineInput.from_arrays(
            demand_kwh=demand,
            base_solar_kwh=base_solar,
            tariff_bdt_per_kwh=tariff,
            battery=battery,
            directives=directives,
            solver_timeout_seconds=solver_timeout_seconds,
            tolerance=tolerance,
            enforce_eod_neutrality=enforce_eod_neutrality,
            strict=strict,
        )
        return self.optimize_and_validate(p_input)


# Standalone functional entrypoint
def optimize_and_validate(
    pipeline_input: OptimizationPipelineInput | OptimizationInput,
    solver_timeout_seconds: float | None = None,
    tolerance: float | None = None,
    enforce_eod_neutrality: bool | None = None,
    strict: bool | None = None,
) -> OptimizationPipelineResult:
    """Execute the end-to-end optimization and validation pipeline."""
    engine = OptimizationEngine()
    return engine.optimize_and_validate(
        pipeline_input=pipeline_input,
        solver_timeout_seconds=solver_timeout_seconds,
        tolerance=tolerance,
        enforce_eod_neutrality=enforce_eod_neutrality,
        strict=strict,
    )
