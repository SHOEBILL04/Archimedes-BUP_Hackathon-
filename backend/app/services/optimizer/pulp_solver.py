"""Deterministic 24-hour linear programming energy dispatch optimizer using PuLP + CBC.

Formulates and solves the cost-minimization energy dispatch problem:
- 24 continuous decision variables per hour (grid, solar_used, battery_charge, battery_discharge, battery_energy_after)
- First-principles energy balance conservation
- Solar availability bounds and operator reduction factors
- Battery state dynamics, capacity bounds, rate limits, and end-of-day neutrality
- Deterministic operator directives (no-charge, no-discharge, minimum reserve, max grid)
- Graceful, structured failure reporting without fake schedules
"""

from __future__ import annotations

import math
import time
from typing import Any

import pulp

from app.core.logging import logger
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
    HourlyEnergyProfile,
    HourlyScheduleOutput,
    OptimizationInput,
    OptimizationResult,
    SolverStatus,
)

NUMERICAL_TOLERANCE: float = 1e-7


def _clean_val(val: Any) -> float:
    """Clamp tiny floating-point numerical solver noise to 0.0."""
    if val is None:
        return 0.0
    f = float(val)
    return 0.0 if abs(f) < NUMERICAL_TOLERANCE else f


class PuLpEnergyOptimizer(IOptimizer):
    """Deterministic 24-hour LP energy dispatch optimizer implemented via PuLP and CBC.

    Conforms to the IOptimizer interface protocol.
    """

    def __init__(self, default_timeout_seconds: float = 5.0) -> None:
        self.default_timeout_seconds = default_timeout_seconds

    def optimize(
        self,
        opt_input: OptimizationInput,
        timeout_seconds: float | None = None,
        raise_on_error: bool = False,
    ) -> OptimizationResult:
        """Alias for solve."""
        return self.solve(
            opt_input=opt_input,
            timeout_seconds=timeout_seconds,
            raise_on_error=raise_on_error,
        )

    def solve(
        self,
        opt_input: OptimizationInput,
        timeout_seconds: float | None = None,
        raise_on_error: bool = False,
    ) -> OptimizationResult:
        """Formulate and solve the 24-hour linear program using PuLP + CBC.

        Args:
            opt_input: Complete scenario profile, battery configuration, and compiled directives.
            timeout_seconds: Maximum allowed solve time in seconds.
            raise_on_error: If True, raises domain exceptions on infeasible, timeout, or error.

        Returns:
            OptimizationResult containing 24-hour schedule, costs, and solver status.
        """
        start_time = time.perf_counter()
        timeout = timeout_seconds if timeout_seconds is not None else self.default_timeout_seconds

        # 1. Input structural validation
        self._validate_input(opt_input)

        profile: HourlyEnergyProfile = opt_input.energy_profile
        battery: BatteryConfig = opt_input.battery
        directives: CompiledDirectives = opt_input.compiled_directives

        demand: list[float] = profile.demand_kwh
        tariff: list[float] = profile.tariff_bdt_per_kwh
        effective_solar: list[float] = directives.effective_solar

        # 2. Structural feasibility pre-checks
        for h in range(HOURS_IN_DAY):
            if directives.min_reserve[h] > battery.capacity_kwh:
                msg = (
                    f"Hour {h}: Required minimum reserve ({directives.min_reserve[h]} kWh) "
                    f"exceeds battery capacity ({battery.capacity_kwh} kWh)."
                )
                logger.warning("Infeasibility detected during pre-check: %s", msg)
                if raise_on_error:
                    raise OptimizationInfeasibleError(msg)
                return OptimizationResult(
                    schedule=[],
                    total_grid_kwh=0.0,
                    total_grid_cost_bdt=0.0,
                    objective_value=0.0,
                    solver_status=SolverStatus.INFEASIBLE,
                    message=msg,
                    execution_time_seconds=time.perf_counter() - start_time,
                )

        # 3. Model formulation
        problem = pulp.LpProblem("SmartCampusEnergyOptimization", pulp.LpMinimize)

        # Decision Variables (all continuous, physical energy >= 0)
        grid = [pulp.LpVariable(f"grid_{h}", lowBound=0.0) for h in range(HOURS_IN_DAY)]
        solar_used = [
            pulp.LpVariable(
                f"solar_used_{h}",
                lowBound=0.0,
                upBound=float(effective_solar[h]),
            )
            for h in range(HOURS_IN_DAY)
        ]
        charge = [pulp.LpVariable(f"charge_{h}", lowBound=0.0) for h in range(HOURS_IN_DAY)]
        discharge = [pulp.LpVariable(f"discharge_{h}", lowBound=0.0) for h in range(HOURS_IN_DAY)]
        energy_after = [
            pulp.LpVariable(
                f"energy_after_{h}",
                lowBound=float(directives.min_reserve[h]),
                upBound=float(battery.capacity_kwh),
            )
            for h in range(HOURS_IN_DAY)
        ]

        # Objective: Minimize total grid electricity purchasing cost
        problem += (
            pulp.lpSum(grid[h] * float(tariff[h]) for h in range(HOURS_IN_DAY)),
            "MinimizeTotalGridCost",
        )

        charge_eff = float(battery.charge_efficiency)
        discharge_eff = float(battery.discharge_efficiency)

        # Constraints
        for h in range(HOURS_IN_DAY):
            # Energy Balance: grid + solar_used + battery_discharge == demand + battery_charge
            problem += (
                grid[h] + solar_used[h] + discharge[h] == float(demand[h]) + charge[h],
                f"EnergyBalance_{h}",
            )

            # Charge rate limit
            charge_cap = 0.0 if directives.no_charge[h] else float(battery.max_charge_kwh_per_hour)
            problem += charge[h] <= charge_cap, f"ChargeRateLimit_{h}"

            # Discharge rate limit
            discharge_cap = (
                0.0 if directives.no_discharge[h] else float(battery.max_discharge_kwh_per_hour)
            )
            problem += discharge[h] <= discharge_cap, f"DischargeRateLimit_{h}"

            # Max grid ceiling
            if directives.max_grid[h] is not None:
                problem += grid[h] <= float(directives.max_grid[h]), f"MaxGridLimit_{h}"

            # Battery state dynamics
            if h == 0:
                problem += (
                    energy_after[0]
                    == float(battery.initial_energy_kwh)
                    + charge[0] * charge_eff
                    - discharge[0] / discharge_eff,
                    "BatteryDynamics_0",
                )
            else:
                problem += (
                    energy_after[h]
                    == energy_after[h - 1] + charge[h] * charge_eff - discharge[h] / discharge_eff,
                    f"BatteryDynamics_{h}",
                )

        # End-of-day condition: final energy state must match initial energy state
        problem += (
            energy_after[HOURS_IN_DAY - 1] == float(battery.initial_energy_kwh),
            "EndOfDayBatteryNeutrality",
        )

        # 4. Solver invocation via CBC
        cbc_solver = pulp.PULP_CBC_CMD(
            timeLimit=timeout,
            msg=False,
            threads=1,
        )

        try:
            status_code = problem.solve(cbc_solver)
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            logger.error("PuLP solver execution raised exception: %s", e)
            if raise_on_error:
                raise SolverExecutionError(f"Solver crashed: {e}") from e
            return OptimizationResult(
                schedule=[],
                total_grid_kwh=0.0,
                total_grid_cost_bdt=0.0,
                objective_value=0.0,
                solver_status=SolverStatus.ERROR,
                message=f"Solver execution error: {e}",
                execution_time_seconds=elapsed,
            )

        elapsed = time.perf_counter() - start_time

        # 5. Result status mapping
        if status_code == pulp.LpStatusOptimal:
            solver_status = SolverStatus.OPTIMAL
            message = "Optimal energy dispatch computed successfully."
        elif status_code == pulp.LpStatusInfeasible:
            solver_status = SolverStatus.INFEASIBLE
            message = "Optimization problem is mathematically infeasible."
        elif status_code == pulp.LpStatusUnbounded:
            solver_status = SolverStatus.UNBOUNDED
            message = "Optimization problem is mathematically unbounded."
        elif status_code == pulp.LpStatusNotSolved:
            solver_status = SolverStatus.TIMEOUT
            message = "Solver timed out before reaching a verifiable optimal solution."
        else:
            solver_status = SolverStatus.ERROR
            message = f"Solver returned unrecognized status code {status_code}."

        if solver_status != SolverStatus.OPTIMAL:
            logger.warning("Optimization failed: %s (status=%s)", message, solver_status)
            if raise_on_error:
                if solver_status == SolverStatus.INFEASIBLE:
                    raise OptimizationInfeasibleError(message)
                elif solver_status == SolverStatus.TIMEOUT:
                    raise OptimizationTimeoutError(message)
                else:
                    raise SolverExecutionError(message)

            return OptimizationResult(
                schedule=[],
                total_grid_kwh=0.0,
                total_grid_cost_bdt=0.0,
                objective_value=0.0,
                solver_status=solver_status,
                message=message,
                execution_time_seconds=elapsed,
            )

        # 6. Extract solution variables into clean schedule outputs
        schedule_rows: list[HourlyScheduleOutput] = []
        total_grid_kwh = 0.0
        total_cost = 0.0

        for h in range(HOURS_IN_DAY):
            g = _clean_val(pulp.value(grid[h]))
            s = _clean_val(pulp.value(solar_used[h]))
            c = _clean_val(pulp.value(charge[h]))
            d = _clean_val(pulp.value(discharge[h]))
            e = _clean_val(pulp.value(energy_after[h]))

            cost_h = g * float(tariff[h])
            total_grid_kwh += g
            total_cost += cost_h

            schedule_rows.append(
                HourlyScheduleOutput(
                    hour=h,
                    grid_kwh=g,
                    solar_used_kwh=s,
                    battery_charge_kwh=c,
                    battery_discharge_kwh=d,
                    battery_energy_after_kwh=e,
                    demand_kwh=float(demand[h]),
                    effective_solar_kwh=float(effective_solar[h]),
                    tariff_bdt_per_kwh=float(tariff[h]),
                    grid_cost_bdt=round(cost_h, 6),
                )
            )

        obj_val = float(pulp.value(problem.objective))

        return OptimizationResult(
            schedule=schedule_rows,
            total_grid_kwh=round(total_grid_kwh, 4),
            total_grid_cost_bdt=round(total_cost, 4),
            objective_value=round(obj_val, 4),
            solver_status=SolverStatus.OPTIMAL,
            message=message,
            execution_time_seconds=elapsed,
        )

    def _validate_input(self, opt_input: OptimizationInput) -> None:
        """Validate structural and numerical sanity of optimizer input."""
        if not isinstance(opt_input, OptimizationInput):
            raise ValueError(f"Expected OptimizationInput instance, got {type(opt_input).__name__}")

        profile = opt_input.energy_profile
        battery = opt_input.battery
        directives = opt_input.compiled_directives

        for name, arr in [
            ("demand_kwh", profile.demand_kwh),
            ("base_solar_kwh", profile.base_solar_kwh),
            ("tariff_bdt_per_kwh", profile.tariff_bdt_per_kwh),
        ]:
            if len(arr) != HOURS_IN_DAY:
                raise ValueError(
                    f"{name} must contain exactly {HOURS_IN_DAY} elements, got {len(arr)}"
                )
            for idx, val in enumerate(arr):
                if (
                    not isinstance(val, (int, float))
                    or isinstance(val, bool)
                    or not math.isfinite(val)
                ):
                    raise ValueError(f"Non-finite numeric value in {name}[{idx}]: {val!r}")
                if val < 0.0:
                    raise ValueError(f"Negative value not permitted in {name}[{idx}]: {val}")

        if battery.capacity_kwh <= 0.0:
            raise ValueError(f"Battery capacity must be positive, got {battery.capacity_kwh}")

        for name, arr in [
            ("solar_factor", directives.solar_factor),
            ("effective_solar", directives.effective_solar),
            ("min_reserve", directives.min_reserve),
            ("no_charge", directives.no_charge),
            ("no_discharge", directives.no_discharge),
            ("max_grid", directives.max_grid),
        ]:
            if len(arr) != HOURS_IN_DAY:
                raise ValueError(
                    f"Compiled directive {name} must have length {HOURS_IN_DAY}, got {len(arr)}"
                )


# Convenience function for direct solver invocation
def optimize(
    opt_input: OptimizationInput,
    timeout_seconds: float = 5.0,
    raise_on_error: bool = False,
) -> OptimizationResult:
    """Execute optimization dispatch on the provided input payload."""
    optimizer = PuLpEnergyOptimizer(default_timeout_seconds=timeout_seconds)
    return optimizer.solve(
        opt_input, timeout_seconds=timeout_seconds, raise_on_error=raise_on_error
    )
