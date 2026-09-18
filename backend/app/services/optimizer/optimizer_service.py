"""Public Orchestration Service for Dispatch Optimization.

Provides a clean, typed boundary between the backend application layer and
the PuLP/CBC linear programming solver. This module is the sole designated entrypoint
for dispatch optimization; higher-level services must never import PuLP directly.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from app.services.optimizer.guardrails import (
    compile_directives,
    validate_interpretations,
)
from app.services.optimizer.lp_optimizer import (
    BatteryInput,
    HourResult,
    OptimizationInput,
    OptimizationResult,
    optimize,
)

logger = logging.getLogger(__name__)

HOURS_IN_DAY: int = 24


def _validate_raw_array(name: str, values: list[float]) -> None:
    """Validate that an hourly array contains exactly 24 finite, non-negative numbers."""
    if len(values) != HOURS_IN_DAY:
        raise ValueError(
            f"All hourly arrays must contain exactly {HOURS_IN_DAY} values (got {len(values)} for '{name}')"
        )
    for idx, v in enumerate(values):
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(float(v)):
            raise ValueError(f"Non-finite values found in input: '{name}' index {idx} = {v}")
        if float(v) < 0.0:
            raise ValueError(f"Hourly values must be non-negative: '{name}' index {idx} = {v}")


def run_optimization(
    demand: list[float],
    base_solar: list[float],
    tariff: list[float],
    battery: BatteryInput,
    raw_interpretations: list[dict[str, Any]],
    note_count: int,
    solver_timeout_seconds: float = 5.0,
) -> OptimizationResult:
    """Execute the end-to-end deterministic energy dispatch optimization pipeline.

    Pipeline Steps:
      1. Pre-validation of input arrays (length 24, finite, non-negative).
      2. Guardrail validation of untrusted LLM directive interpretations.
      3. Compilation of validated directives into hourly physical bounds.
      4. Zero-demand short-circuit check (avoids solver invocation if unnecessary).
      5. Formulation and execution of CBC linear program.
      6. Conversion into structured OptimizationResult.

    Args:
        demand: 24 hourly campus electricity demand values in kWh.
        base_solar: 24 hourly base solar generation forecast values in kWh.
        tariff: 24 hourly grid electricity tariffs in BDT/kWh.
        battery: Battery technical specifications and boundary limits.
        raw_interpretations: Untrusted directive interpretation dicts from LLM.
        note_count: Number of operator notes expected for this scenario.
        solver_timeout_seconds: Time limit in seconds for CBC solver execution.

    Returns:
        OptimizationResult containing hourly schedules, grid energy, and total cost.

    Raises:
        ValueError: If input arrays are invalid, negative, non-finite, or malformed.
        InfeasibleError: If the scenario constraints cannot be satisfied.
        SolverError: If the CBC solver fails to execute or crashes.
        OptimizationError: For general optimization failures.
    """
    # 1. Structural and physical input validation
    _validate_raw_array("demand", demand)
    _validate_raw_array("base_solar", base_solar)
    _validate_raw_array("tariff", tariff)

    if battery.capacity_kwh <= 0.0:
        raise ValueError(f"Battery capacity must be positive (got {battery.capacity_kwh})")
    if battery.initial_energy_kwh < 0.0:
        raise ValueError(f"Battery initial energy cannot be negative (got {battery.initial_energy_kwh})")
    if battery.minimum_energy_kwh < 0.0:
        raise ValueError(f"Battery minimum energy cannot be negative (got {battery.minimum_energy_kwh})")
    if battery.initial_energy_kwh > battery.capacity_kwh:
        raise ValueError(
            f"Battery initial energy ({battery.initial_energy_kwh}) exceeds capacity ({battery.capacity_kwh})"
        )
    if battery.minimum_energy_kwh > battery.capacity_kwh:
        raise ValueError(
            f"Battery minimum energy ({battery.minimum_energy_kwh}) exceeds capacity ({battery.capacity_kwh})"
        )
    if battery.initial_energy_kwh < battery.minimum_energy_kwh:
        raise ValueError(
            f"Battery initial energy ({battery.initial_energy_kwh}) is below minimum reserve ({battery.minimum_energy_kwh})"
        )

    # 2. Guardrail validation of LLM output
    validated_directives = validate_interpretations(
        raw_items=raw_interpretations,
        note_count=note_count,
        battery_capacity=battery.capacity_kwh,
    )

    # 3. Deterministic constraint compilation
    compiled = compile_directives(
        interpretations=validated_directives,
        base_solar=base_solar,
        battery_capacity=battery.capacity_kwh,
        battery_min_energy=battery.minimum_energy_kwh,
    )

    # 4. Zero-demand edge case short-circuit
    if all(d == 0.0 for d in demand):
        logger.info("All hourly demand values are zero; returning trivial zero-cost dispatch schedule.")
        hourly_schedule = [
            HourResult(
                hour=h,
                demand_kwh=0.0,
                effective_solar_kwh=compiled.effective_solar[h],
                solar_used_kwh=0.0,
                battery_charge_kwh=0.0,
                battery_discharge_kwh=0.0,
                battery_energy_after_kwh=battery.initial_energy_kwh,
                grid_kwh=0.0,
                tariff_bdt_per_kwh=tariff[h],
                grid_cost_bdt=0.0,
            )
            for h in range(HOURS_IN_DAY)
        ]
        return OptimizationResult(
            hourly_schedule=hourly_schedule,
            total_grid_kwh=0.0,
            total_grid_cost_bdt=0.0,
            peak_grid_kwh=0.0,
            objective_value=0.0,
            solver_status="Optimal",
        )

    # 5. Build optimization input and solve LP
    opt_input = OptimizationInput(
        demand=demand,
        tariff=tariff,
        battery=battery,
        compiled_directives=compiled,
    )

    return optimize(
        opt_input=opt_input,
        solver_timeout_seconds=solver_timeout_seconds,
    )
