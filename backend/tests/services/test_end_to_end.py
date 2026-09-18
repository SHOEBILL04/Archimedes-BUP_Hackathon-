"""Full pipeline: guardrails -> optimizer -> replay validator.

Every scenario here runs the three layers exactly as the orchestration layer
will, and asserts that an independently computed validation passes. A failure
means the layers disagree about physics, which no single-layer test would catch.
"""

from __future__ import annotations

import pytest

from app.schemas.optimization import HOURS
from app.services.optimizer import solve_dispatch
from app.services.validation import normalize_directives, replay_validate

from .conftest import directive, make_battery, make_scenario

TOL = 1e-6

# A realistic mid-size campus day, matching the project's documented sample.
CAMPUS_DEMAND = [35, 34, 33, 32, 31, 30, 32, 38, 45, 52, 58, 62,
                 65, 68, 70, 72, 75, 78, 74, 68, 60, 52, 45, 40]
CAMPUS_SOLAR = [0, 0, 0, 0, 0, 0, 3, 8, 15, 22, 30, 38,
                42, 44, 40, 32, 22, 12, 5, 0, 0, 0, 0, 0]
CAMPUS_TARIFF = [8, 8, 8, 8, 8, 8, 9, 9, 10, 10, 11, 12,
                 12, 13, 13, 14, 15, 15, 14, 12, 11, 10, 9, 9]


def run_pipeline(scenario, directives=None):
    """Input -> guardrails -> optimizer -> validator, as Member 2 will call it."""
    report = normalize_directives(scenario, directives or [])
    outcome = solve_dispatch(scenario, report.normalized)
    validation = replay_validate(
        scenario,
        report.normalized,
        outcome.schedule,
        reported_total_cost_bdt=outcome.total_grid_cost_bdt,
        reported_total_grid_kwh=outcome.total_grid_kwh,
    )
    return report, outcome, validation


def campus_scenario(**overrides):
    defaults = {
        "demand": [float(v) for v in CAMPUS_DEMAND],
        "base_solar": [float(v) for v in CAMPUS_SOLAR],
        "tariff": [float(v) for v in CAMPUS_TARIFF],
        "battery": make_battery(),
        "notes": ["operator note"],
    }
    defaults.update(overrides)
    return make_scenario(**defaults)


def assert_pipeline_valid(report, outcome, validation):
    assert report.rejections == (), [r.reason for r in report.rejections]
    assert outcome.succeeded, outcome.message
    assert validation.valid, [str(e) for e in validation.errors]
    assert validation.max_constraint_error == pytest.approx(0.0, abs=TOL)


# --------------------------------------------------------------------------- #
# Realistic scenarios
# --------------------------------------------------------------------------- #


def test_campus_day_without_directives():
    report, outcome, validation = run_pipeline(campus_scenario())

    assert_pipeline_valid(report, outcome, validation)
    assert validation.total_grid_cost_bdt == pytest.approx(outcome.total_grid_cost_bdt, abs=1e-6)


def test_campus_day_with_the_documented_operator_notes():
    """The two sample notes: cut afternoon solar 80%, block evening charging."""
    scenario = campus_scenario(
        notes=[
            "Reduce solar from 1 PM to 3 PM by 80%",
            "Do not charge the battery from 6 PM to 8 PM",
        ]
    )
    directives = [
        directive("solar_reduction", {"hours": [13, 14, 15], "factor": 0.2}, note_index=0),
        directive("no_charge_window", {"hours": [18, 19, 20]}, note_index=1),
    ]

    report, outcome, validation = run_pipeline(scenario, directives)

    assert_pipeline_valid(report, outcome, validation)
    for hour in (13, 14, 15):
        expected = CAMPUS_SOLAR[hour] * 0.2
        assert outcome.schedule[hour].effective_solar_kwh == pytest.approx(expected, abs=TOL)
    for hour in (18, 19, 20):
        assert outcome.schedule[hour].battery_charge_kwh == pytest.approx(0.0, abs=TOL)


def test_high_solar_summer_day():
    scenario = campus_scenario(
        base_solar=[0.0] * 5 + [20.0, 45.0, 70.0, 90.0, 100.0, 110.0, 115.0,
                                115.0, 110.0, 100.0, 85.0, 60.0, 35.0, 15.0] + [0.0] * 5,
    )

    report, outcome, validation = run_pipeline(scenario)

    assert_pipeline_valid(report, outcome, validation)
    # Abundant free solar should crowd out midday grid import entirely.
    assert outcome.schedule[12].grid_kwh == pytest.approx(0.0, abs=TOL)


def test_winter_day_with_no_solar_at_all():
    scenario = campus_scenario(base_solar=[0.0] * HOURS)

    report, outcome, validation = run_pipeline(scenario)

    assert_pipeline_valid(report, outcome, validation)
    assert all(row.solar_used_kwh == pytest.approx(0.0, abs=TOL) for row in outcome.schedule)
    assert outcome.total_grid_kwh == pytest.approx(sum(CAMPUS_DEMAND), abs=1e-4)


def test_constrained_grid_day():
    scenario = campus_scenario(battery=make_battery(minimum_energy_kwh=0.0))
    directives = [
        directive("max_grid_window", {"hours": [16, 17, 18], "max_grid_kwh": 55.0})
    ]

    report, outcome, validation = run_pipeline(scenario, directives)

    assert_pipeline_valid(report, outcome, validation)
    for hour in (16, 17, 18):
        assert outcome.schedule[hour].grid_kwh <= 55.0 + TOL


def test_day_with_every_directive_type_at_once():
    scenario = campus_scenario(
        battery=make_battery(capacity_kwh=120.0, initial_energy_kwh=50.0,
                             minimum_energy_kwh=10.0)
    )
    directives = [
        directive("solar_reduction", {"hours": [11, 12, 13], "factor": 0.5}, note_index=0),
        directive("no_discharge_window", {"hours": [6, 7]}, note_index=1),
        directive(
            "minimum_battery_reserve", {"hours": [15], "minimum_energy_kwh": 60.0},
            note_index=2,
        ),
    ]

    report, outcome, validation = run_pipeline(scenario, directives)

    assert_pipeline_valid(report, outcome, validation)
    for hour in (6, 7):
        assert outcome.schedule[hour].battery_discharge_kwh == pytest.approx(0.0, abs=TOL)
    assert outcome.schedule[15].battery_energy_after_kwh >= 60.0 - TOL


def test_pipeline_survives_a_malformed_directive():
    """A rejected directive must not stop the rest of the pipeline."""
    scenario = campus_scenario()
    directives = [
        directive("solar_reduction", {"hours": [9], "factor": 4.0}, note_index=0),
        directive("no_charge_window", {"hours": [20, 21]}, note_index=1),
    ]

    report, outcome, validation = run_pipeline(scenario, directives)

    assert len(report.rejections) == 1
    assert report.rejections[0].note_index == 0
    assert outcome.succeeded
    assert validation.valid, [str(e) for e in validation.errors]
    # The surviving directive still took effect.
    for hour in (20, 21):
        assert outcome.schedule[hour].battery_charge_kwh == pytest.approx(0.0, abs=TOL)


# --------------------------------------------------------------------------- #
# Economic behaviour (brief section 6)
# --------------------------------------------------------------------------- #


def test_battery_reduces_cost_under_a_large_price_spread():
    """Objective-level assertion: no specific schedule is required."""
    spread = [4.0] * 12 + [40.0] * 12
    without = campus_scenario(
        tariff=spread,
        battery=make_battery(capacity_kwh=1.0, initial_energy_kwh=1.0,
                             minimum_energy_kwh=1.0,
                             max_charge_kwh_per_hour=0.0,
                             max_discharge_kwh_per_hour=0.0),
    )
    with_battery = campus_scenario(
        tariff=spread,
        battery=make_battery(capacity_kwh=200.0, initial_energy_kwh=50.0,
                             minimum_energy_kwh=0.0,
                             max_charge_kwh_per_hour=50.0,
                             max_discharge_kwh_per_hour=50.0),
    )

    _, idle, _ = run_pipeline(without)
    _, active, validation = run_pipeline(with_battery)

    assert validation.valid
    assert active.total_grid_cost_bdt < idle.total_grid_cost_bdt


def test_cheaper_hours_carry_more_import_than_expensive_hours():
    scenario = campus_scenario(
        tariff=[4.0] * 12 + [40.0] * 12,
        battery=make_battery(capacity_kwh=200.0, initial_energy_kwh=50.0,
                             minimum_energy_kwh=0.0,
                             max_charge_kwh_per_hour=50.0,
                             max_discharge_kwh_per_hour=50.0),
    )

    _, outcome, _ = run_pipeline(scenario)
    cheap = sum(row.grid_kwh for row in outcome.schedule[:12])
    expensive = sum(row.grid_kwh for row in outcome.schedule[12:])

    assert cheap > expensive


def test_tightening_any_directive_never_lowers_cost():
    """Each directive only removes options, so cost is monotone non-decreasing."""
    scenario = campus_scenario(battery=make_battery(minimum_energy_kwh=0.0))
    _, baseline, _ = run_pipeline(scenario)

    for directives in (
        [directive("solar_reduction", {"hours": [10, 11, 12], "factor": 0.1})],
        [directive("no_charge_window", {"hours": list(range(0, 8))})],
        [directive("no_discharge_window", {"hours": list(range(16, 22))})],
        [directive("max_grid_window", {"hours": [17, 18], "max_grid_kwh": 50.0})],
        [directive("minimum_battery_reserve",
                   {"hours": [20], "minimum_energy_kwh": 80.0})],
    ):
        _, constrained, validation = run_pipeline(scenario, directives)
        assert constrained.succeeded
        assert validation.valid
        assert constrained.total_grid_cost_bdt >= baseline.total_grid_cost_bdt - 1e-4


# --------------------------------------------------------------------------- #
# Determinism (brief section 12)
# --------------------------------------------------------------------------- #


def test_repeated_runs_give_a_stable_objective():
    scenario = campus_scenario()
    directives = [
        directive("solar_reduction", {"hours": [13, 14], "factor": 0.3}, note_index=0),
        directive("no_charge_window", {"hours": [19, 20]}, note_index=1),
    ]

    runs = [run_pipeline(scenario, directives) for _ in range(5)]
    costs = [outcome.total_grid_cost_bdt for _, outcome, _ in runs]

    assert all(cost == pytest.approx(costs[0], abs=1e-9) for cost in costs)
    # Every run must also stay feasible, not merely equal in cost.
    assert all(validation.valid for _, _, validation in runs)


def test_normalization_is_stable_across_repeated_runs():
    scenario = campus_scenario()
    directives = [
        directive("solar_reduction", {"hours": [13, 14], "factor": 0.3}, note_index=0),
        directive("max_grid_window", {"hours": [2], "max_grid_kwh": 30.0}, note_index=1),
    ]

    reports = [normalize_directives(scenario, directives) for _ in range(5)]

    assert all(r.normalized == reports[0].normalized for r in reports)


def test_directive_ordering_does_not_change_the_objective():
    """note_index ordering is normalized away before the LP is built."""
    scenario = campus_scenario(battery=make_battery(minimum_energy_kwh=0.0))
    a = directive("solar_reduction", {"hours": [12], "factor": 0.5}, note_index=0)
    b = directive("no_charge_window", {"hours": [18]}, note_index=1)

    _, forward, _ = run_pipeline(scenario, [a, b])
    _, reverse, _ = run_pipeline(
        scenario,
        [
            directive("no_charge_window", {"hours": [18]}, note_index=0),
            directive("solar_reduction", {"hours": [12], "factor": 0.5}, note_index=1),
        ],
    )

    assert forward.total_grid_cost_bdt == pytest.approx(reverse.total_grid_cost_bdt, abs=1e-9)


# --------------------------------------------------------------------------- #
# Regression
# --------------------------------------------------------------------------- #


def test_max_constraint_error_stays_in_energy_units():
    """Regression: kWh and BDT violations were once collapsed into one scalar.

    Corrupting grid by 1 kWh at an hour priced above 1 BDT/kWh breaks both the
    energy balance (1 kWh) and the hourly cost (tariff BDT). The physical figure
    must report the kWh violation; the monetary one is tracked separately.
    """
    scenario = campus_scenario()
    report = normalize_directives(scenario, [])
    outcome = solve_dispatch(scenario, report.normalized)
    assert outcome.succeeded

    hour = 16  # tariff 15 BDT/kWh, well above 1
    rows = list(outcome.schedule)
    rows[hour] = rows[hour].model_copy(update={"grid_kwh": rows[hour].grid_kwh + 1.0})

    validation = replay_validate(scenario, report.normalized, rows)

    assert not validation.valid
    assert validation.max_constraint_error == pytest.approx(1.0, abs=1e-6)
    assert validation.max_cost_error_bdt == pytest.approx(15.0, abs=1e-6)


def test_sub_tolerance_energy_nudge_does_not_trip_the_cost_check():
    """Regression: an absolute BDT tolerance made cost checks tariff-sensitive.

    Half a tolerance of energy error is acceptable by definition; multiplying it
    by a large tariff must not turn it into a failure.
    """
    scenario = campus_scenario(tariff=[500.0] * HOURS)
    report = normalize_directives(scenario, [])
    outcome = solve_dispatch(scenario, report.normalized)
    assert outcome.succeeded

    rows = list(outcome.schedule)
    rows[8] = rows[8].model_copy(update={"grid_kwh": rows[8].grid_kwh + 5e-7})

    validation = replay_validate(scenario, report.normalized, rows)

    assert validation.valid, [str(e) for e in validation.errors]
