"""Linear Programming Dispatch Optimizer for Smart Campus Energy Management.

Formulates and solves the 24-hour cost minimization linear program using PuLP and CBC.

Mathematical Formulation:
-------------------------
For hour h in 0..23, continuous decision variables:
  grid[h]                  >= 0   (kWh purchased from grid)
  solar_used[h]            >= 0   (kWh consumed from solar generation)
  battery_charge[h]        >= 0   (kWh stored into battery)
  battery_discharge[h]     >= 0   (kWh supplied from battery)
  battery_energy_after[h]  >= 0   (kWh stored in battery at the end of hour h)

Objective:
  Minimize sum(grid[h] * tariff[h] for h in 0..23)

Constraints:
  1. Energy Balance (every hour):
       grid[h] + solar_used[h] + battery_discharge[h] == demand[h] + battery_charge[h]
  2. Solar Curtailment Bound (every hour):
       0 <= solar_used[h] <= effective_solar[h]
  3. Battery State Bounds (every hour):
       min_reserve[h] <= battery_energy_after[h] <= capacity_kwh
  4. Battery State Dynamics:
       Hour 0:    battery_energy_after[0]  == initial_energy_kwh + charge[0] - discharge[0]
       Hour 1..23: battery_energy_after[h] == battery_energy_after[h-1] + charge[h] - discharge[h]
       (Lossless round-trip efficiency = 1.0 assumed in accordance with challenge spec)
  5. Charge Rate Limits:
       charge[h] == 0 if no_charge[h] else charge[h] <= max_charge_kwh_per_hour
  6. Discharge Rate Limits:
       discharge[h] == 0 if no_discharge[h] else discharge[h] <= max_discharge_kwh_per_hour
  7. Grid Ceiling (if specified):
       grid[h] <= max_grid[h]
  8. End-of-Day Neutrality:
       battery_energy_after[23] == initial_energy_kwh

Solvers:
  PuLP abstraction with CBC (COIN-OR Branch and Cut).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import pulp

from app.services.optimizer.guardrails import CompiledDirectives

logger = logging.getLogger(__name__)

# Floating-point threshold for interpreting near-zero solver variables
EPS: float = 1e-7
HOURS_IN_DAY: int = 24


class OptimizationError(Exception):
    """Base exception for optimization pipeline errors."""


class InfeasibleError(OptimizationError):
    """Raised when the optimization problem is mathematically infeasible or unbounded."""


class SolverError(OptimizationError):
    """Raised when the underlying LP solver crashes, fails to execute, or times out."""


@dataclass
class BatteryInput:
    """Physical battery specification and boundary limits."""

    capacity_kwh: float
    initial_energy_kwh: float
    minimum_energy_kwh: float
    max_charge_kwh_per_hour: float
    max_discharge_kwh_per_hour: float


@dataclass
class OptimizationInput:
    """Input parameters required to construct the 24-hour dispatch LP."""

    demand: list[float]
    tariff: list[float]
    battery: BatteryInput
    compiled_directives: CompiledDirectives


@dataclass
class HourResult:
    """Hourly optimization dispatch results."""

    hour: int
    demand_kwh: float
    effective_solar_kwh: float
    solar_used_kwh: float
    battery_charge_kwh: float
    battery_discharge_kwh: float
    battery_energy_after_kwh: float
    grid_kwh: float
    tariff_bdt_per_kwh: float
    grid_cost_bdt: float


@dataclass
class OptimizationResult:
    """Full 24-hour schedule and performance metrics returned by the optimizer."""

    hourly_schedule: list[HourResult]
    total_grid_kwh: float
    total_grid_cost_bdt: float
    peak_grid_kwh: float
    objective_value: float
    solver_status: str


def _clean_val(val: Any) -> float:
    """Convert solver variable value to clean float, clamping tiny negative numerical noise to zero."""
    if val is None:
        return 0.0
    f = float(val)
    return 0.0 if abs(f) < EPS else f


def optimize(
    opt_input: OptimizationInput,
    solver_timeout_seconds: float = 5.0,
) -> OptimizationResult:
    """Solve the 24-hour smart campus energy dispatch LP model.

    Args:
        opt_input: Complete scenario data, battery parameters, and compiled directives.
        solver_timeout_seconds: Maximum allowed solve time for the CBC solver.

    Returns:
        OptimizationResult containing 24-hour dispatch schedule and summary costs.

    Raises:
        InfeasibleError: If the model cannot be solved to optimality (e.g. Infeasible, Unbounded).
        SolverError: If the solver execution fails or encounters a critical error.
    """
    directives = opt_input.compiled_directives
    battery = opt_input.battery
    demand = opt_input.demand
    tariff = opt_input.tariff

    # Structural feasibility pre-check: reserve exceeding capacity
    for h in range(HOURS_IN_DAY):
        if directives.min_reserve[h] > battery.capacity_kwh:
            raise InfeasibleError(
                f"Hour {h}: minimum reserve ({directives.min_reserve[h]} kWh) "
                f"exceeds battery capacity ({battery.capacity_kwh} kWh)"
            )

    # 1. Initialize minimization LP problem
    problem = pulp.LpProblem("SmartCampusEnergyOptimization", pulp.LpMinimize)

    # 2. Decision Variables (24 hours)
    grid = [
        pulp.LpVariable(f"grid_{h}", lowBound=0.0)
        for h in range(HOURS_IN_DAY)
    ]
    solar_used = [
        pulp.LpVariable(
            f"solar_used_{h}",
            lowBound=0.0,
            upBound=directives.effective_solar[h],
        )
        for h in range(HOURS_IN_DAY)
    ]
    charge = [
        pulp.LpVariable(f"charge_{h}", lowBound=0.0)
        for h in range(HOURS_IN_DAY)
    ]
    discharge = [
        pulp.LpVariable(f"discharge_{h}", lowBound=0.0)
        for h in range(HOURS_IN_DAY)
    ]
    energy_after = [
        pulp.LpVariable(
            f"energy_after_{h}",
            lowBound=directives.min_reserve[h],
            upBound=battery.capacity_kwh,
        )
        for h in range(HOURS_IN_DAY)
    ]

    # 3. Objective: Minimize total grid electricity purchasing cost
    problem += pulp.lpSum(
        grid[h] * tariff[h]
        for h in range(HOURS_IN_DAY)
    ), "MinimizeTotalGridCost"

    # 4. Hourly Constraints
    for h in range(HOURS_IN_DAY):
        # Energy balance: grid + solar + battery discharge == demand + battery charge
        problem += (
            grid[h] + solar_used[h] + discharge[h] == demand[h] + charge[h],
            f"EnergyBalance_{h}",
        )

        # Charge rate limit
        charge_limit = 0.0 if directives.no_charge[h] else battery.max_charge_kwh_per_hour
        problem += charge[h] <= charge_limit, f"ChargeRateLimit_{h}"

        # Discharge rate limit
        discharge_limit = 0.0 if directives.no_discharge[h] else battery.max_discharge_kwh_per_hour
        problem += discharge[h] <= discharge_limit, f"DischargeRateLimit_{h}"

        # Max grid ceiling directive constraint
        if directives.max_grid[h] is not None:
            problem += grid[h] <= float(directives.max_grid[h]), f"MaxGridLimit_{h}"

        # Battery dynamics (Lossless 100% round-trip efficiency)
        if h == 0:
            problem += (
                energy_after[0] == battery.initial_energy_kwh + charge[0] - discharge[0],
                "BatteryDynamics_0",
            )
        else:
            problem += (
                energy_after[h] == energy_after[h - 1] + charge[h] - discharge[h],
                f"BatteryDynamics_{h}",
            )

    # 5. End-of-day neutrality: final state of charge must match initial state of charge
    problem += (
        energy_after[HOURS_IN_DAY - 1] == battery.initial_energy_kwh,
        "EndOfDayNeutrality",
    )

    # 6. Configure and execute CBC solver
    solver = pulp.PULP_CBC_CMD(
        msg=False,
        timeLimit=solver_timeout_seconds,
        threads=1,
    )

    try:
        status_code = problem.solve(solver)
    except Exception as exc:
        logger.error("LP solver execution encountered an unexpected failure: %s", exc)
        raise SolverError(f"Solver execution failed: {exc}") from exc

    status_str = pulp.LpStatus.get(status_code, "Unknown")
    logger.info("LP solver terminated with status: %s", status_str)

    if status_str != "Optimal":
        raise InfeasibleError(
            f"Optimization failed to find an optimal solution. Solver status: {status_str}"
        )

    # 7. Extract solution values and construct response
    hourly_schedule: list[HourResult] = []
    total_grid_kwh = 0.0
    total_grid_cost_bdt = 0.0
    peak_grid_kwh = 0.0

    for h in range(HOURS_IN_DAY):
        g = _clean_val(pulp.value(grid[h]))
        s = _clean_val(pulp.value(solar_used[h]))
        c = _clean_val(pulp.value(charge[h]))
        d = _clean_val(pulp.value(discharge[h]))
        e = _clean_val(pulp.value(energy_after[h]))
        cost = g * tariff[h]

        total_grid_kwh += g
        total_grid_cost_bdt += cost
        if g > peak_grid_kwh:
            peak_grid_kwh = g

        hourly_schedule.append(
            HourResult(
                hour=h,
                demand_kwh=demand[h],
                effective_solar_kwh=directives.effective_solar[h],
                solar_used_kwh=s,
                battery_charge_kwh=c,
                battery_discharge_kwh=d,
                battery_energy_after_kwh=e,
                grid_kwh=g,
                tariff_bdt_per_kwh=tariff[h],
                grid_cost_bdt=cost,
            )
        )

    obj_val = float(pulp.value(problem.objective) or total_grid_cost_bdt)

    return OptimizationResult(
        hourly_schedule=hourly_schedule,
        total_grid_kwh=total_grid_kwh,
        total_grid_cost_bdt=total_grid_cost_bdt,
        peak_grid_kwh=peak_grid_kwh,
        objective_value=obj_val,
        solver_status=status_str,
    )


__all__ = [
    "BatteryInput",
    "HourResult",
    "InfeasibleError",
    "OptimizationError",
    "OptimizationInput",
    "OptimizationResult",
    "SolverError",
    "optimize",
]
