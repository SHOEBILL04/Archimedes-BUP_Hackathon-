"""Replay validator tests.

Corrupted schedules are built with ``model_copy(update=...)``, which bypasses
Pydantic validation — exactly the situation the validator exists to catch, since
a buggy optimizer could emit such a row internally.
"""

from __future__ import annotations

import pytest

from app.schemas.optimization import HOURS, HourSchedule
from app.services.optimizer import solve_dispatch
from app.services.validation import (
    NormalizedDirectives,
    normalize_directives,
    replay_validate,
)

from .conftest import directive, make_battery, make_scenario


def _scenario(**overrides):
    defaults = {
        "demand": [10.0] * HOURS,
        "base_solar": [4.0] * HOURS,
        "tariff": [5.0] * 12 + [15.0] * 12,
        "battery": make_battery(minimum_energy_kwh=0.0),
    }
    defaults.update(overrides)
    return make_scenario(**defaults)


def _optimized(scenario, directives=None):
    """Solve, then hand the result to the validator exactly as Member 2 would."""
    normalized = (
        normalize_directives(scenario, directives).normalized
        if directives
        else NormalizedDirectives.identity()
    )
    outcome = solve_dispatch(scenario, normalized)
    assert outcome.succeeded
    return normalized, outcome


def _corrupt(schedule, hour: int, **fields) -> list[HourSchedule]:
    rows = list(schedule)
    rows[hour] = rows[hour].model_copy(update=fields)
    return rows


def _validate(scenario, normalized, schedule, **kwargs):
    return replay_validate(scenario, normalized, schedule, **kwargs)


def _rules(result) -> set[str]:
    return {issue.rule for issue in result.errors}


# --------------------------------------------------------------------------- #
# Valid optimizer output
# --------------------------------------------------------------------------- #


def test_valid_optimizer_output_passes():
    scenario = _scenario()
    normalized, outcome = _optimized(scenario)

    result = _validate(
        scenario,
        normalized,
        outcome.schedule,
        reported_total_cost_bdt=outcome.total_grid_cost_bdt,
        reported_total_grid_kwh=outcome.total_grid_kwh,
    )

    assert result.valid, [str(e) for e in result.errors]
    assert result.errors == ()
    assert result.max_constraint_error == pytest.approx(0.0, abs=1e-6)


def test_valid_output_with_every_directive_type_passes():
    scenario = _scenario(base_solar=[9.0] * HOURS)
    directives = [
        directive("solar_reduction", {"hours": [12, 13], "factor": 0.2}, note_index=0),
        directive("no_charge_window", {"hours": [18, 19]}, note_index=1),
        directive(
            "minimum_battery_reserve", {"hours": [5], "minimum_energy_kwh": 20.0}, note_index=2
        ),
    ]
    normalized, outcome = _optimized(scenario, directives)

    result = _validate(scenario, normalized, outcome.schedule)

    assert result.valid, [str(e) for e in result.errors]


def test_validator_recomputes_totals_independently():
    scenario = _scenario()
    normalized, outcome = _optimized(scenario)

    result = _validate(scenario, normalized, outcome.schedule)

    assert result.total_grid_cost_bdt == pytest.approx(outcome.total_grid_cost_bdt, abs=1e-6)
    assert result.total_grid_kwh == pytest.approx(outcome.total_grid_kwh, abs=1e-6)


# --------------------------------------------------------------------------- #
# Schedule shape
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("count", [23, 25])
def test_wrong_schedule_length_rejected(count):
    scenario = _scenario()
    normalized, outcome = _optimized(scenario)
    rows = list(outcome.schedule)
    rows = rows[:count] if count < HOURS else rows + [rows[-1]]

    result = _validate(scenario, normalized, rows)

    assert not result.valid
    assert "schedule_length" in _rules(result)


def test_duplicate_hours_rejected():
    scenario = _scenario()
    normalized, outcome = _optimized(scenario)
    rows = list(outcome.schedule)
    rows[5] = rows[5].model_copy(update={"hour": 4})

    result = _validate(scenario, normalized, rows)

    assert not result.valid
    assert "schedule_hours" in _rules(result)


def test_out_of_order_hours_rejected():
    scenario = _scenario()
    normalized, outcome = _optimized(scenario)
    rows = list(outcome.schedule)
    rows[3], rows[9] = rows[9], rows[3]

    result = _validate(scenario, normalized, rows)

    assert not result.valid
    assert "schedule_hours" in _rules(result)


# --------------------------------------------------------------------------- #
# Deliberately corrupted schedules (brief section 24)
# --------------------------------------------------------------------------- #


def test_energy_imbalance_detected():
    scenario = _scenario()
    normalized, outcome = _optimized(scenario)
    # Add 5 kWh of grid without changing anything else.
    rows = _corrupt(outcome.schedule, 7, grid_kwh=outcome.schedule[7].grid_kwh + 5.0)

    result = _validate(scenario, normalized, rows)

    assert not result.valid
    assert "energy_balance" in _rules(result)
    assert any(e.hour == 7 for e in result.errors)
    assert result.max_constraint_error >= 5.0 - 1e-6


def test_solar_violation_detected():
    scenario = _scenario()
    normalized, outcome = _optimized(scenario)
    row = outcome.schedule[10]
    rows = _corrupt(
        outcome.schedule,
        10,
        solar_used_kwh=row.effective_solar_kwh + 3.0,
        # Keep the balance intact so solar availability is the only failure.
        grid_kwh=max(0.0, row.grid_kwh - 3.0),
    )

    result = _validate(scenario, normalized, rows)

    assert not result.valid
    assert "solar_availability" in _rules(result)


def test_tampered_effective_solar_detected():
    """The validator recomputes effective solar rather than trusting it."""
    scenario = _scenario()
    normalized, outcome = _optimized(scenario)
    rows = _corrupt(outcome.schedule, 6, effective_solar_kwh=999.0)

    result = _validate(scenario, normalized, rows)

    assert not result.valid
    assert "effective_solar" in _rules(result)


def test_battery_overflow_detected():
    scenario = _scenario()
    normalized, outcome = _optimized(scenario)
    capacity = scenario.battery.capacity_kwh
    rows = _corrupt(outcome.schedule, 8, battery_energy_after_kwh=capacity + 10.0)

    result = _validate(scenario, normalized, rows)

    assert not result.valid
    assert "battery_capacity" in _rules(result)


def test_charge_rate_violation_detected():
    scenario = _scenario()
    normalized, outcome = _optimized(scenario)
    limit = scenario.battery.max_charge_kwh_per_hour
    rows = _corrupt(outcome.schedule, 4, battery_charge_kwh=limit + 7.0)

    result = _validate(scenario, normalized, rows)

    assert not result.valid
    assert "charge_rate" in _rules(result)


def test_discharge_rate_violation_detected():
    scenario = _scenario()
    normalized, outcome = _optimized(scenario)
    limit = scenario.battery.max_discharge_kwh_per_hour
    rows = _corrupt(outcome.schedule, 15, battery_discharge_kwh=limit + 7.0)

    result = _validate(scenario, normalized, rows)

    assert not result.valid
    assert "discharge_rate" in _rules(result)


def test_reserve_violation_detected():
    scenario = _scenario(battery=make_battery(initial_energy_kwh=60.0, minimum_energy_kwh=0.0))
    directives = [
        directive("minimum_battery_reserve", {"hours": [9], "minimum_energy_kwh": 50.0})
    ]
    normalized, outcome = _optimized(scenario, directives)
    rows = _corrupt(outcome.schedule, 9, battery_energy_after_kwh=5.0)

    result = _validate(scenario, normalized, rows)

    assert not result.valid
    assert "minimum_reserve" in _rules(result)


def test_no_charge_violation_detected():
    scenario = _scenario()
    directives = [directive("no_charge_window", {"hours": [3]})]
    normalized, outcome = _optimized(scenario, directives)
    rows = _corrupt(outcome.schedule, 3, battery_charge_kwh=6.0)

    result = _validate(scenario, normalized, rows)

    assert not result.valid
    assert "no_charge" in _rules(result)


def test_no_discharge_violation_detected():
    scenario = _scenario()
    directives = [directive("no_discharge_window", {"hours": [20]})]
    normalized, outcome = _optimized(scenario, directives)
    rows = _corrupt(outcome.schedule, 20, battery_discharge_kwh=6.0)

    result = _validate(scenario, normalized, rows)

    assert not result.valid
    assert "no_discharge" in _rules(result)


def test_max_grid_violation_detected():
    scenario = _scenario()
    directives = [directive("max_grid_window", {"hours": [11], "max_grid_kwh": 4.0})]
    normalized, outcome = _optimized(scenario, directives)
    rows = _corrupt(outcome.schedule, 11, grid_kwh=25.0)

    result = _validate(scenario, normalized, rows)

    assert not result.valid
    assert "max_grid" in _rules(result)


def test_final_state_violation_detected():
    scenario = _scenario()
    normalized, outcome = _optimized(scenario)
    rows = _corrupt(outcome.schedule, HOURS - 1, battery_energy_after_kwh=5.0)

    result = _validate(scenario, normalized, rows)

    assert not result.valid
    assert "end_of_day_neutrality" in _rules(result)


def test_objective_manipulation_detected():
    """Changing only the reported total must not pass validation."""
    scenario = _scenario()
    normalized, outcome = _optimized(scenario)

    result = _validate(
        scenario,
        normalized,
        outcome.schedule,
        reported_total_cost_bdt=outcome.total_grid_cost_bdt - 500.0,
        reported_total_grid_kwh=outcome.total_grid_kwh,
    )

    assert not result.valid
    assert "total_cost" in _rules(result)


def test_total_grid_energy_manipulation_detected():
    scenario = _scenario()
    normalized, outcome = _optimized(scenario)

    result = _validate(
        scenario,
        normalized,
        outcome.schedule,
        reported_total_grid_kwh=outcome.total_grid_kwh + 25.0,
    )

    assert not result.valid
    assert "total_grid_energy" in _rules(result)


def test_hourly_cost_manipulation_detected():
    scenario = _scenario()
    normalized, outcome = _optimized(scenario)
    # Pick an hour that actually imports, otherwise zeroing the cost is a no-op.
    hour = next(row.hour for row in outcome.schedule if row.grid_kwh > 1.0)
    rows = _corrupt(outcome.schedule, hour, grid_cost_bdt=0.0)

    result = _validate(scenario, normalized, rows)

    assert not result.valid
    assert "hourly_cost" in _rules(result)


def test_negative_value_detected():
    scenario = _scenario()
    normalized, outcome = _optimized(scenario)
    rows = _corrupt(outcome.schedule, 1, grid_kwh=-5.0)

    result = _validate(scenario, normalized, rows)

    assert not result.valid
    assert "grid_non_negative" in _rules(result)


# --------------------------------------------------------------------------- #
# Input integrity
# --------------------------------------------------------------------------- #


def test_tampered_tariff_detected():
    """Tariff is taken from the request, so restating it in the schedule fails."""
    scenario = _scenario()
    normalized, outcome = _optimized(scenario)
    rows = _corrupt(outcome.schedule, 14, tariff_bdt_per_kwh=0.01)

    result = _validate(scenario, normalized, rows)

    assert not result.valid
    assert "tariff_integrity" in _rules(result)


def test_tampered_demand_detected():
    scenario = _scenario()
    normalized, outcome = _optimized(scenario)
    rows = _corrupt(outcome.schedule, 16, demand_kwh=0.0)

    result = _validate(scenario, normalized, rows)

    assert not result.valid
    assert "demand_integrity" in _rules(result)


def test_battery_state_replay_mismatch_detected():
    """Charge/discharge that do not explain the reported state of charge."""
    scenario = _scenario()
    normalized, outcome = _optimized(scenario)
    row = outcome.schedule[5]
    rows = _corrupt(
        outcome.schedule, 5, battery_energy_after_kwh=row.battery_energy_after_kwh + 3.0
    )

    result = _validate(scenario, normalized, rows)

    assert not result.valid
    assert "battery_state_replay" in _rules(result)


# --------------------------------------------------------------------------- #
# Tolerance, warnings and determinism
# --------------------------------------------------------------------------- #


def test_sub_tolerance_noise_is_accepted():
    scenario = _scenario()
    normalized, outcome = _optimized(scenario)
    row = outcome.schedule[9]
    rows = _corrupt(outcome.schedule, 9, grid_kwh=row.grid_kwh + 1e-9)

    result = _validate(scenario, normalized, rows)

    assert result.valid, [str(e) for e in result.errors]


def test_simultaneous_charge_discharge_warns_but_stays_valid():
    """Energy- and cost-neutral at unit efficiency, so a warning rather than an error."""
    scenario = _scenario()
    normalized, outcome = _optimized(scenario)
    row = outcome.schedule[6]
    # Add an equal amount to both sides: balance and state of charge are unchanged.
    delta = 2.0
    rows = _corrupt(
        outcome.schedule,
        6,
        battery_charge_kwh=row.battery_charge_kwh + delta,
        battery_discharge_kwh=row.battery_discharge_kwh + delta,
    )

    result = _validate(scenario, normalized, rows)

    assert result.valid, [str(e) for e in result.errors]
    assert "simultaneous_charge_discharge" in {w.rule for w in result.warnings}


def test_errors_identify_hour_rule_actual_and_expected():
    scenario = _scenario()
    normalized, outcome = _optimized(scenario)
    rows = _corrupt(outcome.schedule, 7, grid_kwh=outcome.schedule[7].grid_kwh + 5.0)

    result = _validate(scenario, normalized, rows)
    balance = next(e for e in result.errors if e.rule == "energy_balance")

    assert balance.hour == 7
    assert balance.actual is not None
    assert balance.expected is not None
    assert "energy_balance" in str(balance)


def test_validation_is_deterministic():
    scenario = _scenario()
    normalized, outcome = _optimized(scenario)
    rows = _corrupt(outcome.schedule, 7, grid_kwh=outcome.schedule[7].grid_kwh + 5.0)

    results = [_validate(scenario, normalized, rows) for _ in range(3)]

    assert all(r.valid == results[0].valid for r in results)
    assert all(r.errors == results[0].errors for r in results)


def test_validator_does_not_mutate_inputs():
    scenario = _scenario()
    normalized, outcome = _optimized(scenario)
    before_scenario = scenario.model_dump()
    before_schedule = [row.model_dump() for row in outcome.schedule]

    _validate(scenario, normalized, outcome.schedule)

    assert scenario.model_dump() == before_scenario
    assert [row.model_dump() for row in outcome.schedule] == before_schedule
