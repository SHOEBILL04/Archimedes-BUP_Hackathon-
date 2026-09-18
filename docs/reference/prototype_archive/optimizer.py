from __future__ import annotations

from dataclasses import dataclass

import pulp

from guardrails import compile_directives
from models import DirectiveInterpretation, EnergyScenario


EPS = 1e-7


class OptimizationError(RuntimeError):
    pass


@dataclass
class OptimizationResult:
    schedule: list[dict]
    total_grid_cost_bdt: float
    total_grid_kwh: float


def optimize_energy(
    scenario: EnergyScenario,
    interpretations: list[DirectiveInterpretation],
    solver_timeout_seconds: float = 5.0,
) -> OptimizationResult:
    directives = compile_directives(interpretations, scenario)

    problem = pulp.LpProblem("SmartCampusEnergyOptimization", pulp.LpMinimize)

    grid = [
        pulp.LpVariable(f"grid_{h}", lowBound=0)
        for h in range(24)
    ]
    solar = [
        pulp.LpVariable(
            f"solar_{h}",
            lowBound=0,
            upBound=directives["effective_solar"][h],
        )
        for h in range(24)
    ]
    charge = [
        pulp.LpVariable(f"charge_{h}", lowBound=0)
        for h in range(24)
    ]
    discharge = [
        pulp.LpVariable(f"discharge_{h}", lowBound=0)
        for h in range(24)
    ]
    energy = [
        pulp.LpVariable(
            f"energy_after_{h}",
            lowBound=directives["min_reserve"][h],
            upBound=scenario.battery.capacity_kwh,
        )
        for h in range(24)
    ]

    # Objective: minimize purchased grid electricity cost.
    problem += pulp.lpSum(
        grid[h] * scenario.tariff_bdt_per_kwh[h]
        for h in range(24)
    )

    for h in range(24):
        # Energy balance:
        # grid + solar + battery discharge = demand + battery charge
        problem += (
            grid[h] + solar[h] + discharge[h]
            == scenario.demand_kwh[h] + charge[h],
            f"energy_balance_{h}",
        )

        charge_limit = (
            0.0
            if directives["no_charge"][h]
            else scenario.battery.max_charge_kwh_per_hour
        )
        discharge_limit = (
            0.0
            if directives["no_discharge"][h]
            else scenario.battery.max_discharge_kwh_per_hour
        )

        problem += charge[h] <= charge_limit, f"charge_rate_{h}"
        problem += discharge[h] <= discharge_limit, f"discharge_rate_{h}"

        max_grid = directives["max_grid"][h]
        if max_grid is not None:
            problem += grid[h] <= float(max_grid), f"grid_limit_{h}"

        if h == 0:
            problem += (
                energy[h]
                == scenario.battery.initial_energy_kwh
                + charge[h]
                - discharge[h],
                "battery_dynamics_0",
            )
        else:
            problem += (
                energy[h]
                == energy[h - 1] + charge[h] - discharge[h],
                f"battery_dynamics_{h}",
            )

    # End-of-day neutrality.
    problem += (
        energy[23] == scenario.battery.initial_energy_kwh,
        "end_of_day_neutrality",
    )

    solver = pulp.COIN_CMD(
        msg=False,
        timeLimit=solver_timeout_seconds,
        threads=1,
    )

    try:
        status = problem.solve(solver)
    except Exception as exc:
        raise OptimizationError(f"LP solver execution failed: {exc}") from exc

    if pulp.LpStatus[status] != "Optimal":
        raise OptimizationError(
            f"optimization failed with solver status: {pulp.LpStatus[status]}"
        )

    rows: list[dict] = []
    total_cost = 0.0
    total_grid = 0.0

    for h in range(24):
        g = float(pulp.value(grid[h]) or 0.0)
        s = float(pulp.value(solar[h]) or 0.0)
        c = float(pulp.value(charge[h]) or 0.0)
        d = float(pulp.value(discharge[h]) or 0.0)
        e = float(pulp.value(energy[h]) or 0.0)
        tariff = scenario.tariff_bdt_per_kwh[h]
        cost = g * tariff

        total_cost += cost
        total_grid += g

        rows.append(
            {
                "hour": h,
                "demand_kwh": scenario.demand_kwh[h],
                "effective_solar_kwh": float(directives["effective_solar"][h]),
                "solar_used_kwh": s,
                "battery_charge_kwh": c,
                "battery_discharge_kwh": d,
                "battery_energy_after_kwh": e,
                "grid_kwh": g,
                "tariff_bdt_per_kwh": tariff,
                "grid_cost_bdt": cost,
            }
        )

    return OptimizationResult(
        schedule=rows,
        total_grid_cost_bdt=total_cost,
        total_grid_kwh=total_grid,
    )
