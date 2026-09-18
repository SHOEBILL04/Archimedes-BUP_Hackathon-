from __future__ import annotations

from dataclasses import dataclass

import pulp

from app.core.logging import logger
from app.schemas.optimization import EnergyScenario, HourSchedule
from app.services.optimizer.exceptions import (
    OptimizationInfeasibleError,
    SolverExecutionError,
)
from app.services.validation.models import CompiledDirectives

EPS = 1e-7


@dataclass
class OptimizationResult:
    """Internal container for raw optimization output."""

    schedule: list[HourSchedule]
    total_grid_cost_bdt: float
    total_grid_kwh: float


class EnergyOptimizer:
    """Linear programming energy dispatch optimizer powered by PuLP / CBC solver.

    Minimizes total 24-hour grid electricity expenditure subject to:
      - Hourly physical power conservation (grid + solar + battery discharge = demand + battery charge)
      - Hourly solar generation ceilings (with directive reduction factors applied)
      - Battery state-of-charge capacity and reserve bounds
      - Charge / discharge hourly rate limits and operator window lockouts
      - Hourly grid power import ceilings
      - 24-hour end-of-day battery neutrality (initial == final energy state)
    """

    def __init__(self, timeout_seconds: float = 5.0) -> None:
        self.timeout_seconds = timeout_seconds

    def solve(
        self,
        scenario: EnergyScenario,
        directives: CompiledDirectives,
    ) -> tuple[list[HourSchedule], float, float]:
        """Formulate and solve the 24-hour linear program.

        Returns:
            tuple of (schedule_rows, total_grid_cost_bdt, total_grid_kwh)
        Raises:
            OptimizationInfeasibleError: if constraints are mathematically contradictory
            OptimizationTimeoutError: if solver execution exceeds timeout
            SolverExecutionError: if solver execution crashes or fails
        """
        problem = pulp.LpProblem("SmartCampusEnergyOptimization", pulp.LpMinimize)

        # 1. Decision Variables (all continuous, non-negative)
        grid = [pulp.LpVariable(f"grid_{h}", lowBound=0) for h in range(24)]
        solar = [
            pulp.LpVariable(
                f"solar_{h}",
                lowBound=0,
                upBound=float(directives.effective_solar[h]),
            )
            for h in range(24)
        ]
        charge = [pulp.LpVariable(f"charge_{h}", lowBound=0) for h in range(24)]
        discharge = [pulp.LpVariable(f"discharge_{h}", lowBound=0) for h in range(24)]
        energy = [
            pulp.LpVariable(
                f"energy_after_{h}",
                lowBound=float(directives.min_reserve[h]),
                upBound=float(scenario.battery.capacity_kwh),
            )
            for h in range(24)
        ]

        # 2. Objective Function: Minimize total grid electricity cost in BDT
        problem += pulp.lpSum(grid[h] * scenario.tariff_bdt_per_kwh[h] for h in range(24))

        # 3. Constraints
        for h in range(24):
            # Energy balance: grid + solar + discharge == demand + charge
            problem += (
                grid[h] + solar[h] + discharge[h] == scenario.demand_kwh[h] + charge[h],
                f"energy_balance_{h}",
            )

            # Battery charge rate limit with directive override
            charge_limit = (
                0.0 if directives.no_charge[h] else float(scenario.battery.max_charge_kwh_per_hour)
            )
            problem += charge[h] <= charge_limit, f"charge_rate_{h}"

            # Battery discharge rate limit with directive override
            discharge_limit = (
                0.0
                if directives.no_discharge[h]
                else float(scenario.battery.max_discharge_kwh_per_hour)
            )
            problem += discharge[h] <= discharge_limit, f"discharge_rate_{h}"

            # Grid power ceiling with directive override
            max_grid = directives.max_grid[h]
            if max_grid is not None:
                problem += grid[h] <= float(max_grid), f"grid_limit_{h}"

            # Battery dynamics
            if h == 0:
                problem += (
                    energy[0] == scenario.battery.initial_energy_kwh + charge[0] - discharge[0],
                    "battery_dynamics_0",
                )
            else:
                problem += (
                    energy[h] == energy[h - 1] + charge[h] - discharge[h],
                    f"battery_dynamics_{h}",
                )

        # End-of-day neutrality (conservation over 24-hour cycle)
        problem += (
            energy[23] == scenario.battery.initial_energy_kwh,
            "end_of_day_neutrality",
        )

        # 4. Invoke Solver
        solver: pulp.LpSolver
        if pulp.COIN_CMD().available():
            solver = pulp.COIN_CMD(msg=False, timeLimit=self.timeout_seconds, threads=1)
        else:
            solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=self.timeout_seconds, threads=1)

        try:
            status = problem.solve(solver)
        except Exception as exc:
            logger.error("PuLP solver execution failed with exception: %s", exc)
            raise SolverExecutionError(f"Solver execution failed: {exc}") from exc

        status_str = pulp.LpStatus.get(status, "Undefined")

        if status_str == "Infeasible":
            logger.warning("Optimization problem is mathematically infeasible")
            raise OptimizationInfeasibleError(
                "Optimization constraints are mutually contradictory or physical limits were exceeded"
            )

        if status_str != "Optimal":
            logger.error("Optimization failed with solver status: %s", status_str)
            raise SolverExecutionError(
                f"Optimization solver returned non-optimal status: {status_str}"
            )

        # 5. Extract Results and Format Schedule
        schedules: list[HourSchedule] = []
        total_cost = 0.0
        total_grid = 0.0

        for h in range(24):
            # Clamp numerical micro-noise from solver (e.g. -1e-14 -> 0.0)
            g = max(0.0, float(pulp.value(grid[h]) or 0.0))
            s = max(0.0, float(pulp.value(solar[h]) or 0.0))
            c = max(0.0, float(pulp.value(charge[h]) or 0.0))
            d = max(0.0, float(pulp.value(discharge[h]) or 0.0))
            e = max(0.0, float(pulp.value(energy[h]) or 0.0))

            tariff = float(scenario.tariff_bdt_per_kwh[h])
            cost = g * tariff

            total_cost += cost
            total_grid += g

            schedules.append(
                HourSchedule(
                    hour=h,
                    demand_kwh=float(scenario.demand_kwh[h]),
                    effective_solar_kwh=float(directives.effective_solar[h]),
                    solar_used_kwh=s,
                    battery_charge_kwh=c,
                    battery_discharge_kwh=d,
                    battery_energy_after_kwh=e,
                    grid_kwh=g,
                    tariff_bdt_per_kwh=tariff,
                    grid_cost_bdt=cost,
                )
            )

        return schedules, total_cost, total_grid
