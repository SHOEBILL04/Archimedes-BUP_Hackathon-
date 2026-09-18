from __future__ import annotations

import math
from typing import Any

from app.schemas.optimization import EnergyScenario, HourSchedule, VerificationResult
from app.services.validation.exceptions import ReplayValidationError
from app.services.validation.models import CompiledDirectives

TOL = 1e-5


def _check(name: str, hour: int | None, error: float, tolerance: float) -> None:
    if error > tolerance:
        raise ReplayValidationError(
            f"Replay physical verification failed: {name}, violation={error:.12g}",
            constraint_name=name,
            hour=hour,
            violation_error=error,
        )


def replay_validate(
    scenario: EnergyScenario,
    directives: CompiledDirectives,
    schedule: list[HourSchedule] | list[dict[str, Any]],
    reported_total_cost: float,
    tolerance: float = TOL,
) -> VerificationResult:
    """Simulates and verifies the 24-hour dispatch schedule against first-principles physics.

    Guarantees zero physical constraint violations beyond the numerical tolerance threshold.
    Validates:
      1. Hourly energy balance conservation: grid + solar + discharge == demand + charge
      2. Solar generation feasibility: solar_used <= effective_solar
      3. Battery capacity and dynamic reserve limits: min_reserve <= energy_after <= capacity
      4. Battery internal state-of-charge dynamics: energy[t] == energy[t-1] + charge[t] - discharge[t]
      5. Charge and discharge maximum rate constraints and window lockouts
      6. Grid power import limits
      7. End-of-day battery energy neutrality: energy[23] == initial_energy
      8. Total reported cost reconciliation

    Returns:
        VerificationResult with verified=True and maximum constraint error observed.
    Raises:
        ReplayValidationError: if any constraint violation exceeds the tolerance threshold.
    """
    if len(schedule) != 24:
        raise ReplayValidationError(f"Schedule must contain exactly 24 rows, found {len(schedule)}")

    max_error = 0.0
    previous_energy = float(scenario.battery.initial_energy_kwh)
    replay_cost = 0.0

    for h, item in enumerate(schedule):
        # Extract row attributes (supporting both HourSchedule and dict)
        if isinstance(item, HourSchedule):
            hour = item.hour
            g = float(item.grid_kwh)
            s = float(item.solar_used_kwh)
            c = float(item.battery_charge_kwh)
            d = float(item.battery_discharge_kwh)
            e = float(item.battery_energy_after_kwh)
        else:
            hour = int(item["hour"])
            g = float(item["grid_kwh"])
            s = float(item["solar_used_kwh"])
            c = float(item["battery_charge_kwh"])
            d = float(item["battery_discharge_kwh"])
            e = float(item["battery_energy_after_kwh"])

        if hour != h:
            raise ReplayValidationError(
                f"Schedule hour mismatch at index {h}: expected {h}, got {hour}", hour=h
            )

        values = [g, s, c, d, e]
        if any(not math.isfinite(v) for v in values):
            raise ReplayValidationError(
                f"Non-finite numerical value detected in schedule at hour {h}", hour=h
            )

        # 1. Non-negativity
        for var_name, val in [
            ("grid", g),
            ("solar", s),
            ("charge", c),
            ("discharge", d),
            ("energy_after", e),
        ]:
            nonneg_err = max(0.0, -val)
            max_error = max(max_error, nonneg_err)
            _check(f"{var_name}_nonnegative", h, nonneg_err, tolerance)

        # 2. Hourly Energy Conservation Balance: (grid + solar + discharge) == (demand + charge)
        demand = float(scenario.demand_kwh[h])
        balance_err = abs((g + s + d) - (demand + c))
        max_error = max(max_error, balance_err)
        _check("energy_balance", h, balance_err, tolerance)

        # 3. Solar Generation Ceiling
        effective_solar = float(directives.effective_solar[h])
        solar_err = max(0.0, s - effective_solar)
        max_error = max(max_error, solar_err)
        _check("solar_availability", h, solar_err, tolerance)

        # 4. Battery Capacity & Reserve Bounds
        min_reserve = float(directives.min_reserve[h])
        capacity = float(scenario.battery.capacity_kwh)
        lower_err = max(0.0, min_reserve - e)
        upper_err = max(0.0, e - capacity)
        max_error = max(max_error, lower_err, upper_err)
        _check("battery_minimum_reserve", h, lower_err, tolerance)
        _check("battery_maximum_capacity", h, upper_err, tolerance)

        # 5. Battery State Transition Dynamics
        expected_e = previous_energy + c - d
        dynamics_err = abs(e - expected_e)
        max_error = max(max_error, dynamics_err)
        _check("battery_dynamics", h, dynamics_err, tolerance)

        # 6. Hourly Charge / Discharge Rate Limits
        charge_limit = (
            0.0 if directives.no_charge[h] else float(scenario.battery.max_charge_kwh_per_hour)
        )
        discharge_limit = (
            0.0
            if directives.no_discharge[h]
            else float(scenario.battery.max_discharge_kwh_per_hour)
        )

        charge_err = max(0.0, c - charge_limit)
        discharge_err = max(0.0, d - discharge_limit)
        max_error = max(max_error, charge_err, discharge_err)
        _check("charge_limit", h, charge_err, tolerance)
        _check("discharge_limit", h, discharge_err, tolerance)

        # 7. Grid Import Ceiling
        max_grid = directives.max_grid[h]
        if max_grid is not None:
            grid_err = max(0.0, g - float(max_grid))
            max_error = max(max_error, grid_err)
            _check("grid_limit", h, grid_err, tolerance)

        # Accumulate verified replay cost
        tariff = float(scenario.tariff_bdt_per_kwh[h])
        replay_cost += g * tariff
        previous_energy = e

    # 8. End-of-Day Battery Neutrality
    initial_energy = float(scenario.battery.initial_energy_kwh)
    end_err = abs(previous_energy - initial_energy)
    max_error = max(max_error, end_err)
    _check("end_of_day_neutrality", 23, end_err, tolerance)

    # 9. Reported Objective Reconciliation
    objective_err = abs(replay_cost - reported_total_cost)
    max_error = max(max_error, objective_err)
    _check("reported_objective_consistency", None, objective_err, tolerance)

    return VerificationResult(
        verified=True,
        max_constraint_error=max_error,
        total_grid_cost_bdt=replay_cost,
    )
