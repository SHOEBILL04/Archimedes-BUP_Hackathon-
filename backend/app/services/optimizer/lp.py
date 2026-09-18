"""Deterministic 24-hour linear program for campus energy dispatch (PuLP + CBC).

All PuLP/CBC specifics are confined to this module. Callers receive a plain
``OptimizationOutcome`` and never import pulp.

Model summary
-------------
Five continuous variables per hour h in 0..23::

    grid[h]                 grid energy imported          (kWh, >= 0)
    solar_used[h]           solar routed into load        (kWh, >= 0)
    battery_charge[h]       energy into the battery       (kWh, >= 0)
    battery_discharge[h]    energy out of the battery     (kWh, >= 0)
    battery_energy_after[h] state of charge at hour end   (kWh, >= 0)

Objective::

    minimize  sum(grid[h] * tariff[h] for h in 0..23)

Only grid energy costs money: solar and stored energy are already paid for, so
shifting load away from expensive tariff hours is the entire source of savings.
"""

from __future__ import annotations

from collections.abc import Sequence

import pulp

from app.core.config import Settings, get_settings
from app.core.logging import logger
from app.schemas.optimization import HOURS, EnergyScenario, HourSchedule
from app.services.validation import (
    NormalizedDirectives,
    apply_solar_directives,
    required_reserve_kwh,
)

from .models import (
    DEFAULT_CHARGE_EFFICIENCY,
    DEFAULT_DISCHARGE_EFFICIENCY,
    SOLVER_NEGATIVE_TOLERANCE,
    OptimizationOutcome,
    SolverStatus,
)

#: PuLP status code -> normalized status.
_STATUS_MAP: dict[int, SolverStatus] = {
    pulp.LpStatusOptimal: SolverStatus.OPTIMAL,
    pulp.LpStatusInfeasible: SolverStatus.INFEASIBLE,
    pulp.LpStatusUnbounded: SolverStatus.UNBOUNDED,
    pulp.LpStatusUndefined: SolverStatus.UNDEFINED,
    pulp.LpStatusNotSolved: SolverStatus.NOT_SOLVED,
}


class SolverNumericalError(RuntimeError):
    """Raised when a solver value is too negative to be floating-point noise."""


def _read(variable: pulp.LpVariable, label: str) -> float:
    """Read a solved variable, clamping solver noise but never rounding."""
    value = variable.value()
    if value is None:
        raise SolverNumericalError(f"{label} has no value after solving")
    if value < 0.0:
        if value >= -SOLVER_NEGATIVE_TOLERANCE:
            return 0.0
        raise SolverNumericalError(f"{label} is meaningfully negative: {value}")
    return float(value)


def solve_dispatch(
    scenario: EnergyScenario,
    normalized: NormalizedDirectives,
    *,
    settings: Settings | None = None,
    charge_efficiency: float = DEFAULT_CHARGE_EFFICIENCY,
    discharge_efficiency: float = DEFAULT_DISCHARGE_EFFICIENCY,
) -> OptimizationOutcome:
    """Solve the cheapest feasible 24-hour dispatch schedule.

    Pure computation: no database access, no HTTP, no persistence.
    """
    if not 0.0 < charge_efficiency <= 1.0:
        raise ValueError("charge_efficiency must be within (0, 1]")
    if not 0.0 < discharge_efficiency <= 1.0:
        raise ValueError("discharge_efficiency must be within (0, 1]")

    settings = settings or get_settings()
    battery = scenario.battery
    demand = scenario.demand_kwh
    tariff = scenario.tariff_bdt_per_kwh

    # Usable solar after operator directives. Baseline solar is never mutated.
    effective_solar = apply_solar_directives(scenario.base_solar_kwh, normalized)

    problem = pulp.LpProblem("smart_campus_energy_dispatch", pulp.LpMinimize)

    hours = range(HOURS)
    grid = [pulp.LpVariable(f"grid_{h}", lowBound=0.0) for h in hours]
    solar_used = [
        # Unused solar is simply curtailed; there is no export, so solar_used is
        # capped by availability rather than forced to equal it.
        pulp.LpVariable(f"solar_used_{h}", lowBound=0.0, upBound=effective_solar[h])
        for h in hours
    ]
    charge = [
        pulp.LpVariable(f"charge_{h}", lowBound=0.0, upBound=battery.max_charge_kwh_per_hour)
        for h in hours
    ]
    discharge = [
        pulp.LpVariable(
            f"discharge_{h}", lowBound=0.0, upBound=battery.max_discharge_kwh_per_hour
        )
        for h in hours
    ]
    energy_after = [
        pulp.LpVariable(f"energy_after_{h}", lowBound=0.0, upBound=battery.capacity_kwh)
        for h in hours
    ]

    # ---- Objective: only grid import costs money. -------------------------- #
    problem += pulp.lpSum(grid[h] * tariff[h] for h in hours), "total_grid_cost_bdt"

    for h in hours:
        # ---- Energy balance ------------------------------------------------ #
        # Every kWh reaching the campus in hour h comes from exactly one of three
        # sources (grid, solar, battery discharge) and is consumed by exactly one
        # of two sinks (campus demand, battery charge). Stating it as an equality
        # forbids unexplained energy in either direction: the optimizer cannot
        # invent energy to dodge a tariff, nor discard it to dodge a constraint.
        problem += (
            grid[h] + solar_used[h] + discharge[h] == demand[h] + charge[h],
            f"energy_balance_{h}",
        )

        # ---- Battery state transition -------------------------------------- #
        # Charging adds energy scaled by charge efficiency; discharging removes
        # more than it delivers, hence division by discharge efficiency. Getting
        # these the wrong way round would let the model manufacture energy.
        previous = battery.initial_energy_kwh if h == 0 else energy_after[h - 1]
        problem += (
            energy_after[h]
            == previous
            + charge[h] * charge_efficiency
            - discharge[h] / discharge_efficiency,
            f"battery_state_{h}",
        )

        # ---- Operator directives ------------------------------------------- #
        floor = required_reserve_kwh(h, battery, normalized)
        if floor > 0.0:
            problem += energy_after[h] >= floor, f"minimum_reserve_{h}"

        if normalized.no_charge[h]:
            problem += charge[h] == 0.0, f"no_charge_{h}"

        if normalized.no_discharge[h]:
            problem += discharge[h] == 0.0, f"no_discharge_{h}"

        max_grid = normalized.max_grid[h]
        if max_grid is not None:
            problem += grid[h] <= max_grid, f"max_grid_{h}"

    # ---- End-of-day neutrality -------------------------------------------- #
    # Without this the optimizer would drain the battery for free energy on the
    # last hours and report a cost that no real campus could repeat tomorrow.
    problem += (
        energy_after[HOURS - 1] == battery.initial_energy_kwh,
        "end_of_day_neutrality",
    )

    # ---- Solve ------------------------------------------------------------- #
    timeout = getattr(settings, "solver_timeout_seconds", None)
    solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=timeout)

    try:
        status_code = problem.solve(solver)
    except Exception as exc:  # noqa: BLE001 - any solver failure is reported, never raised
        logger.exception("CBC solver failed")
        return OptimizationOutcome(
            status=SolverStatus.ERROR, message=f"Solver execution failed: {exc}"
        )

    status = _STATUS_MAP.get(status_code, SolverStatus.UNDEFINED)
    if status is not SolverStatus.OPTIMAL:
        logger.warning("Solver returned non-optimal status: %s", status)
        return OptimizationOutcome(
            status=status, message=f"Solver did not reach optimality (status={status})."
        )

    # ---- Extract the schedule --------------------------------------------- #
    try:
        rows: list[HourSchedule] = []
        total_grid_kwh = 0.0
        total_grid_cost = 0.0

        for h in hours:
            grid_kwh = _read(grid[h], f"grid_{h}")
            grid_cost = grid_kwh * tariff[h]
            total_grid_kwh += grid_kwh
            total_grid_cost += grid_cost

            rows.append(
                HourSchedule(
                    hour=h,
                    demand_kwh=demand[h],
                    effective_solar_kwh=effective_solar[h],
                    solar_used_kwh=_read(solar_used[h], f"solar_used_{h}"),
                    battery_charge_kwh=_read(charge[h], f"charge_{h}"),
                    battery_discharge_kwh=_read(discharge[h], f"discharge_{h}"),
                    battery_energy_after_kwh=_read(energy_after[h], f"energy_after_{h}"),
                    grid_kwh=grid_kwh,
                    tariff_bdt_per_kwh=tariff[h],
                    grid_cost_bdt=grid_cost,
                )
            )
    except SolverNumericalError as exc:
        logger.error("Rejecting solver output: %s", exc)
        return OptimizationOutcome(
            status=SolverStatus.ERROR, message=f"Solver produced invalid values: {exc}"
        )

    objective = pulp.value(problem.objective)

    return OptimizationOutcome(
        status=SolverStatus.OPTIMAL,
        schedule=tuple(rows),
        effective_solar_kwh=effective_solar,
        total_grid_kwh=total_grid_kwh,
        total_grid_cost_bdt=total_grid_cost,
        objective_value=float(objective) if objective is not None else 0.0,
        message="Optimal dispatch schedule found.",
    )


def total_cost(schedule: Sequence[HourSchedule]) -> float:
    """Sum grid cost across a schedule. Convenience for callers and tests."""
    return sum(row.grid_cost_bdt for row in schedule)
