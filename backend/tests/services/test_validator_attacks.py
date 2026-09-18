"""Single-field corruption sweep and tolerance boundary behaviour.

Each case starts from a genuinely optimal schedule and mutates exactly one field
of one hour, so a detection cannot be attributed to a second, incidental change.
``model_copy(update=...)`` bypasses Pydantic validation, reproducing what a buggy
optimizer could construct internally.
"""

from __future__ import annotations

import pytest

from app.schemas.optimization import HOURS
from app.services.optimizer import solve_dispatch
from app.services.validation import TOLERANCE, NormalizedDirectives, replay_validate

from .conftest import make_battery, make_scenario


def _fixture():
    scenario = make_scenario(
        demand=[10.0] * HOURS,
        base_solar=[4.0] * HOURS,
        tariff=[5.0] * 12 + [15.0] * 12,
        battery=make_battery(minimum_energy_kwh=0.0),
    )
    normalized = NormalizedDirectives.identity()
    outcome = solve_dispatch(scenario, normalized)
    assert outcome.succeeded
    return scenario, normalized, outcome


def _validate(scenario, normalized, schedule, **kwargs):
    return replay_validate(scenario, normalized, schedule, **kwargs)


def _mutate(schedule, hour, field, delta):
    rows = list(schedule)
    current = getattr(rows[hour], field)
    rows[hour] = rows[hour].model_copy(update={field: current + delta})
    return rows


def _rules(result):
    return {issue.rule for issue in result.errors}


# --------------------------------------------------------------------------- #
# Single-field corruption sweep (brief section 10)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("field", "delta", "expected_rule"),
    [
        ("grid_kwh", 5.0, "energy_balance"),
        ("grid_kwh", -3.0, "energy_balance"),
        ("solar_used_kwh", 2.0, "energy_balance"),
        ("solar_used_kwh", -2.0, "energy_balance"),
        ("battery_charge_kwh", 4.0, "energy_balance"),
        ("battery_discharge_kwh", 4.0, "energy_balance"),
        ("battery_energy_after_kwh", 6.0, "battery_state_replay"),
        ("battery_energy_after_kwh", -6.0, "battery_state_replay"),
        ("effective_solar_kwh", 7.0, "effective_solar"),
        ("demand_kwh", 3.0, "demand_integrity"),
        ("tariff_bdt_per_kwh", 2.0, "tariff_integrity"),
        ("grid_cost_bdt", 9.0, "hourly_cost"),
    ],
)
def test_single_field_corruption_is_detected(field, delta, expected_rule):
    scenario, normalized, outcome = _fixture()
    # Hour 9 imports from the grid and carries solar, so every field is live.
    rows = _mutate(outcome.schedule, 9, field, delta)

    result = _validate(scenario, normalized, rows)

    assert not result.valid, f"corrupting {field} went undetected"
    assert expected_rule in _rules(result)
    assert any(issue.hour == 9 for issue in result.errors)


@pytest.mark.parametrize(
    ("kwargs", "expected_rule"),
    [
        ({"reported_total_cost_bdt": 1.0}, "total_cost"),
        ({"reported_total_grid_kwh": 1.0}, "total_grid_energy"),
    ],
)
def test_reported_total_corruption_is_detected(kwargs, expected_rule):
    scenario, normalized, outcome = _fixture()

    result = _validate(scenario, normalized, outcome.schedule, **kwargs)

    assert not result.valid
    assert expected_rule in _rules(result)


def test_uncorrupted_schedule_passes_the_same_harness():
    """Control: the sweep's fixture and harness do not themselves fail."""
    scenario, normalized, outcome = _fixture()

    result = _validate(
        scenario,
        normalized,
        outcome.schedule,
        reported_total_cost_bdt=outcome.total_grid_cost_bdt,
        reported_total_grid_kwh=outcome.total_grid_kwh,
    )

    assert result.valid, [str(e) for e in result.errors]


def test_corruption_is_reported_against_the_right_hour():
    scenario, normalized, outcome = _fixture()
    rows = _mutate(outcome.schedule, 17, "grid_kwh", 8.0)

    result = _validate(scenario, normalized, rows)
    hours = {issue.hour for issue in result.errors if issue.rule == "energy_balance"}

    assert hours == {17}


def test_every_error_carries_actionable_detail():
    scenario, normalized, outcome = _fixture()
    rows = _mutate(outcome.schedule, 9, "grid_kwh", 5.0)

    result = _validate(scenario, normalized, rows)

    for issue in result.errors:
        assert issue.rule
        assert issue.message
        if issue.actual is not None:
            assert issue.expected is not None


# --------------------------------------------------------------------------- #
# Tolerance boundary (brief section 11)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("delta", [0.0, TOLERANCE / 100, TOLERANCE / 2])
def test_deviation_inside_tolerance_is_accepted(delta):
    scenario, normalized, outcome = _fixture()
    rows = _mutate(outcome.schedule, 9, "grid_kwh", delta)

    result = _validate(scenario, normalized, rows)

    assert result.valid, [str(e) for e in result.errors]


@pytest.mark.parametrize("multiplier", [10, 1_000, 1_000_000])
def test_deviation_outside_tolerance_is_rejected(multiplier):
    scenario, normalized, outcome = _fixture()
    rows = _mutate(outcome.schedule, 9, "grid_kwh", TOLERANCE * multiplier)

    result = _validate(scenario, normalized, rows)

    assert not result.valid
    assert "energy_balance" in _rules(result)


def test_tolerance_boundary_is_consistent_across_rules():
    """A half-tolerance nudge passes and a ten-times nudge fails, for each rule."""
    scenario, normalized, outcome = _fixture()

    for field in ("grid_kwh", "battery_energy_after_kwh", "effective_solar_kwh"):
        inside = _validate(
            scenario, normalized, _mutate(outcome.schedule, 9, field, TOLERANCE / 2)
        )
        outside = _validate(
            scenario, normalized, _mutate(outcome.schedule, 9, field, TOLERANCE * 10)
        )
        assert inside.valid, f"{field}: half-tolerance nudge should pass"
        assert not outside.valid, f"{field}: 10x-tolerance nudge should fail"


def test_max_constraint_error_reflects_the_violation_size():
    scenario, normalized, outcome = _fixture()

    small = _validate(scenario, normalized, _mutate(outcome.schedule, 9, "grid_kwh", 1.0))
    large = _validate(scenario, normalized, _mutate(outcome.schedule, 9, "grid_kwh", 50.0))

    assert small.max_constraint_error == pytest.approx(1.0, abs=1e-6)
    assert large.max_constraint_error == pytest.approx(50.0, abs=1e-6)


def test_clean_schedule_reports_zero_constraint_error():
    scenario, normalized, outcome = _fixture()

    result = _validate(scenario, normalized, outcome.schedule)

    assert result.valid
    assert result.max_constraint_error == pytest.approx(0.0, abs=1e-9)


def test_custom_tolerance_is_honoured():
    scenario, normalized, outcome = _fixture()
    rows = _mutate(outcome.schedule, 9, "grid_kwh", 0.5)

    strict = _validate(scenario, normalized, rows)
    lenient = _validate(scenario, normalized, rows, tolerance=1.0)

    assert not strict.valid
    assert lenient.valid


# --------------------------------------------------------------------------- #
# Multiple simultaneous corruptions
# --------------------------------------------------------------------------- #


def test_multiple_corruptions_are_all_reported():
    scenario, normalized, outcome = _fixture()
    rows = list(outcome.schedule)
    rows[3] = rows[3].model_copy(update={"grid_kwh": rows[3].grid_kwh + 5.0})
    rows[14] = rows[14].model_copy(update={"effective_solar_kwh": 99.0})

    result = _validate(scenario, normalized, rows)
    hours = {issue.hour for issue in result.errors}

    assert not result.valid
    assert {3, 14} <= hours
    assert {"energy_balance", "effective_solar"} <= _rules(result)


def test_validator_reports_every_failing_hour_not_just_the_first():
    scenario, normalized, outcome = _fixture()
    rows = list(outcome.schedule)
    for hour in (2, 8, 19):
        rows[hour] = rows[hour].model_copy(update={"grid_kwh": rows[hour].grid_kwh + 4.0})

    result = _validate(scenario, normalized, rows)
    hours = {issue.hour for issue in result.errors if issue.rule == "energy_balance"}

    assert hours == {2, 8, 19}
