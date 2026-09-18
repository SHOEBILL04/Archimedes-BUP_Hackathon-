from __future__ import annotations

import math

from guardrails import compile_directives
from models import DirectiveInterpretation, EnergyScenario, VerificationResult


TOL = 1e-5


class ReplayValidationError(RuntimeError):
    pass


def _check(name: str, error: float) -> None:
    if error > TOL:
        raise ReplayValidationError(
            f"replay validation failed: {name}, error={error:.12g}"
        )


def replay_validate(
    scenario: EnergyScenario,
    interpretations: list[DirectiveInterpretation],
    schedule: list[dict],
    reported_total_cost: float,
) -> VerificationResult:
    if len(schedule) != 24:
        raise ReplayValidationError("schedule must contain exactly 24 rows")

    directives = compile_directives(interpretations, scenario)
    max_error = 0.0
    previous_energy = scenario.battery.initial_energy_kwh
    replay_cost = 0.0

    for h, row in enumerate(schedule):
        if row["hour"] != h:
            raise ReplayValidationError(f"schedule hour mismatch at index {h}")

        g = float(row["grid_kwh"])
        s = float(row["solar_used_kwh"])
        c = float(row["battery_charge_kwh"])
        d = float(row["battery_discharge_kwh"])
        e = float(row["battery_energy_after_kwh"])

        values = [g, s, c, d, e]
        if any(not math.isfinite(v) for v in values):
            raise ReplayValidationError(f"non-finite schedule value at hour {h}")

        # Non-negativity.
        for name, value in [("grid", g), ("solar", s), ("charge", c), ("discharge", d)]:
            _check(f"{name}_nonnegative_{h}", max(0.0, -value))

        # Energy balance.
        balance_error = abs(
            (g + s + d) - (scenario.demand_kwh[h] + c)
        )
        max_error = max(max_error, balance_error)
        _check(f"energy_balance_{h}", balance_error)

        # Solar availability.
        solar_error = max(0.0, s - directives["effective_solar"][h])
        max_error = max(max_error, solar_error)
        _check(f"solar_availability_{h}", solar_error)

        # Battery bounds.
        lower_error = max(0.0, directives["min_reserve"][h] - e)
        upper_error = max(0.0, e - scenario.battery.capacity_kwh)
        max_error = max(max_error, lower_error, upper_error)
        _check(f"battery_lower_bound_{h}", lower_error)
        _check(f"battery_upper_bound_{h}", upper_error)

        # Battery dynamics.
        expected_e = previous_energy + c - d
        dynamics_error = abs(e - expected_e)
        max_error = max(max_error, dynamics_error)
        _check(f"battery_dynamics_{h}", dynamics_error)

        # Hourly charge/discharge limits.
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

        charge_error = max(0.0, c - charge_limit)
        discharge_error = max(0.0, d - discharge_limit)
        max_error = max(max_error, charge_error, discharge_error)
        _check(f"charge_limit_{h}", charge_error)
        _check(f"discharge_limit_{h}", discharge_error)

        # Grid limit.
        if directives["max_grid"][h] is not None:
            grid_error = max(0.0, g - float(directives["max_grid"][h]))
            max_error = max(max_error, grid_error)
            _check(f"grid_limit_{h}", grid_error)

        replay_cost += g * scenario.tariff_bdt_per_kwh[h]
        previous_energy = e

    end_error = abs(previous_energy - scenario.battery.initial_energy_kwh)
    max_error = max(max_error, end_error)
    _check("end_of_day_neutrality", end_error)

    objective_error = abs(replay_cost - reported_total_cost)
    max_error = max(max_error, objective_error)
    _check("reported_objective", objective_error)

    return VerificationResult(
        verified=True,
        max_constraint_error=max_error,
        total_grid_cost_bdt=replay_cost,
    )
