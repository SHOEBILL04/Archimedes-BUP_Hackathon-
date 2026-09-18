"""Intentionally impossible problems.

Two distinct failure channels are exercised here and must not be confused:

  * Semantically impossible *directives* are stopped by the guardrail layer and
    never reach the solver -- the optimization still succeeds, minus that
    directive.
  * Physically impossible *scenarios* reach the solver and come back INFEASIBLE
    with no schedule attached.
"""

from __future__ import annotations

import pytest

from app.schemas.optimization import HOURS
from app.services.optimizer import SolverStatus, solve_dispatch
from app.services.validation import NormalizedDirectives, normalize_directives

from .conftest import directive, make_battery, make_scenario

ALL_HOURS = list(range(HOURS))


def _run(scenario, directives=None):
    report = (
        normalize_directives(scenario, directives)
        if directives
        else normalize_directives(scenario, [])
    )
    return report, solve_dispatch(scenario, report.normalized)


def _assert_infeasible(outcome):
    assert outcome.status is SolverStatus.INFEASIBLE
    assert not outcome.succeeded
    # A failed solve must never carry a schedule that could be mistaken for one.
    assert outcome.schedule == ()
    assert outcome.total_grid_cost_bdt == pytest.approx(0.0)
    assert outcome.total_grid_kwh == pytest.approx(0.0)


# --------------------------------------------------------------------------- #
# Grid cap too low
# --------------------------------------------------------------------------- #


def test_zero_grid_cap_with_no_solar_is_infeasible():
    scenario = make_scenario(demand=[10.0] * HOURS, base_solar=[0.0] * HOURS)
    capped = [directive("max_grid_window", {"hours": ALL_HOURS, "max_grid_kwh": 0.0})]

    _, outcome = _run(scenario, capped)

    _assert_infeasible(outcome)


def test_grid_cap_below_demand_exceeds_what_the_battery_can_bridge():
    """Cap the whole day below demand: the shortfall over 24 h far exceeds the
    battery's usable energy, and neutrality forbids a net drain anyway."""
    scenario = make_scenario(
        demand=[10.0] * HOURS,
        base_solar=[0.0] * HOURS,
        battery=make_battery(capacity_kwh=100.0, initial_energy_kwh=40.0,
                             minimum_energy_kwh=0.0),
    )
    capped = [directive("max_grid_window", {"hours": ALL_HOURS, "max_grid_kwh": 5.0})]

    _, outcome = _run(scenario, capped)

    _assert_infeasible(outcome)


def test_grid_cap_within_battery_reach_stays_feasible():
    """Boundary counterpart: a shortfall the battery can actually cover."""
    scenario = make_scenario(
        demand=[10.0] * HOURS,
        base_solar=[0.0] * HOURS,
        tariff=[5.0] * 12 + [15.0] * 12,
        battery=make_battery(capacity_kwh=100.0, initial_energy_kwh=40.0,
                             minimum_energy_kwh=0.0),
    )
    # Only six capped hours, needing 6 x 5 = 30 kWh from a battery with 60 spare.
    capped = [directive("max_grid_window", {"hours": [12, 13, 14, 15, 16, 17],
                                            "max_grid_kwh": 5.0})]

    _, outcome = _run(scenario, capped)

    assert outcome.succeeded
    for hour in (12, 13, 14, 15, 16, 17):
        assert outcome.schedule[hour].grid_kwh <= 5.0 + 1e-6


# --------------------------------------------------------------------------- #
# Impossible reserve is stopped by guardrails, not by the solver
# --------------------------------------------------------------------------- #


def test_reserve_above_capacity_is_rejected_before_optimization():
    scenario = make_scenario(
        demand=[10.0] * HOURS,
        base_solar=[0.0] * HOURS,
        battery=make_battery(capacity_kwh=100.0),
    )
    impossible = [
        directive("minimum_battery_reserve", {"hours": [5], "minimum_energy_kwh": 500.0})
    ]

    report, outcome = _run(scenario, impossible)

    # Guardrails drop it, so the solve still succeeds with no reserve applied.
    assert len(report.rejections) == 1
    assert "exceeds battery capacity" in report.rejections[0].reason
    assert report.normalized.minimum_reserve[5] == pytest.approx(0.0)
    assert outcome.succeeded


def test_reserve_at_exactly_capacity_is_accepted_and_binds():
    scenario = make_scenario(
        demand=[10.0] * HOURS,
        base_solar=[0.0] * HOURS,
        tariff=[5.0] * 12 + [15.0] * 12,
        battery=make_battery(capacity_kwh=100.0, initial_energy_kwh=40.0,
                             minimum_energy_kwh=0.0),
    )
    # Hour 10 leaves 13 further hours of demand to absorb the drop back to 40.
    at_capacity = [
        directive("minimum_battery_reserve", {"hours": [10], "minimum_energy_kwh": 100.0})
    ]

    report, outcome = _run(scenario, at_capacity)

    assert report.rejections == ()
    assert outcome.succeeded
    assert outcome.schedule[10].battery_energy_after_kwh == pytest.approx(100.0, abs=1e-6)


def test_no_export_bounds_net_discharge_by_demand():
    """Regression: stored energy can only leave the battery by serving demand.

    There is no export, so the balance grid + solar + discharge == demand + charge
    with grid >= 0 forces (discharge - charge) <= demand + solar in every hour.
    A late full-capacity reserve is therefore unreachable not because of the
    discharge *rate* but because there is not enough remaining demand to absorb
    the energy before end-of-day neutrality applies.

    Reserve of 100 kWh at hour 20 leaves hours 21-23 to shed 60 kWh into only
    3 x 10 = 30 kWh of demand, so the scenario is genuinely infeasible.
    """
    scenario = make_scenario(
        demand=[10.0] * HOURS,
        base_solar=[0.0] * HOURS,
        tariff=[5.0] * 12 + [15.0] * 12,
        battery=make_battery(
            capacity_kwh=100.0,
            initial_energy_kwh=40.0,
            minimum_energy_kwh=0.0,
            max_discharge_kwh_per_hour=25.0,
        ),
    )
    late_reserve = [
        directive("minimum_battery_reserve", {"hours": [20], "minimum_energy_kwh": 100.0})
    ]

    report, outcome = _run(scenario, late_reserve)

    assert report.rejections == ()
    _assert_infeasible(outcome)


def test_net_discharge_never_exceeds_demand_plus_solar_in_any_hour():
    """The same property, asserted directly on a normal optimal schedule."""
    scenario = make_scenario(
        demand=[10.0] * HOURS,
        base_solar=[4.0] * HOURS,
        tariff=[5.0] * 12 + [15.0] * 12,
        battery=make_battery(minimum_energy_kwh=0.0),
    )

    _, outcome = _run(scenario)

    assert outcome.succeeded
    for row in outcome.schedule:
        net_discharge = row.battery_discharge_kwh - row.battery_charge_kwh
        assert net_discharge <= row.demand_kwh + row.solar_used_kwh + 1e-6


def test_reserve_unreachable_within_the_day_is_infeasible():
    """Accepted by guardrails (it is within capacity) but physically out of reach:
    the battery cannot climb from 10 kWh to 100 kWh by hour 1 at 25 kWh/h."""
    scenario = make_scenario(
        demand=[10.0] * HOURS,
        base_solar=[0.0] * HOURS,
        battery=make_battery(
            capacity_kwh=100.0,
            initial_energy_kwh=10.0,
            minimum_energy_kwh=0.0,
            max_charge_kwh_per_hour=25.0,
        ),
    )
    unreachable = [
        directive("minimum_battery_reserve", {"hours": [1], "minimum_energy_kwh": 100.0})
    ]

    report, outcome = _run(scenario, unreachable)

    assert report.rejections == ()  # semantically fine, physically impossible
    _assert_infeasible(outcome)


# --------------------------------------------------------------------------- #
# Frozen battery
# --------------------------------------------------------------------------- #


def test_no_charge_and_no_discharge_with_a_grid_cap_is_infeasible():
    """The battery is the only way to cover the capped hours, and both directives
    together freeze it."""
    scenario = make_scenario(
        demand=[10.0] * HOURS,
        base_solar=[0.0] * HOURS,
        tariff=[5.0] * 12 + [15.0] * 12,
        battery=make_battery(capacity_kwh=100.0, initial_energy_kwh=40.0,
                             minimum_energy_kwh=0.0),
    )
    directives = [
        directive("no_charge_window", {"hours": ALL_HOURS}, note_index=0),
        directive("no_discharge_window", {"hours": ALL_HOURS}, note_index=1),
        directive(
            "max_grid_window", {"hours": [12, 13, 14], "max_grid_kwh": 5.0}, note_index=2
        ),
    ]

    report, outcome = _run(scenario, directives)

    assert report.rejections == ()
    _assert_infeasible(outcome)


def test_the_same_grid_cap_is_feasible_once_discharge_is_allowed():
    """Control for the test above: only the no-discharge directive is removed."""
    scenario = make_scenario(
        demand=[10.0] * HOURS,
        base_solar=[0.0] * HOURS,
        tariff=[5.0] * 12 + [15.0] * 12,
        battery=make_battery(capacity_kwh=100.0, initial_energy_kwh=40.0,
                             minimum_energy_kwh=0.0),
    )
    directives = [
        directive("max_grid_window", {"hours": [12, 13, 14], "max_grid_kwh": 5.0})
    ]

    _, outcome = _run(scenario, directives)

    assert outcome.succeeded


def test_frozen_battery_alone_remains_feasible():
    """Freezing the battery is only fatal when something else needs it."""
    scenario = make_scenario(demand=[10.0] * HOURS, base_solar=[0.0] * HOURS)
    directives = [
        directive("no_charge_window", {"hours": ALL_HOURS}, note_index=0),
        directive("no_discharge_window", {"hours": ALL_HOURS}, note_index=1),
    ]

    _, outcome = _run(scenario, directives)

    assert outcome.succeeded
    assert all(row.battery_charge_kwh == pytest.approx(0.0, abs=1e-6)
               for row in outcome.schedule)


def test_no_charge_with_a_reserve_above_the_initial_state_is_infeasible():
    """The reserve demands more energy than the battery starts with, and charging
    to reach it is forbidden."""
    scenario = make_scenario(
        demand=[10.0] * HOURS,
        base_solar=[0.0] * HOURS,
        battery=make_battery(capacity_kwh=100.0, initial_energy_kwh=30.0,
                             minimum_energy_kwh=0.0),
    )
    directives = [
        directive("no_charge_window", {"hours": ALL_HOURS}, note_index=0),
        directive(
            "minimum_battery_reserve", {"hours": [10], "minimum_energy_kwh": 80.0},
            note_index=1,
        ),
    ]

    _, outcome = _run(scenario, directives)

    _assert_infeasible(outcome)


# --------------------------------------------------------------------------- #
# Feasible extremes that must not be mistaken for failures
# --------------------------------------------------------------------------- #


def test_zero_demand_is_feasible_and_free():
    scenario = make_scenario(demand=[0.0] * HOURS, base_solar=[0.0] * HOURS)

    _, outcome = _run(scenario)

    assert outcome.succeeded
    assert outcome.total_grid_cost_bdt == pytest.approx(0.0, abs=1e-9)
    assert outcome.total_grid_kwh == pytest.approx(0.0, abs=1e-9)


def test_zero_tariff_is_feasible_and_free():
    scenario = make_scenario(demand=[10.0] * HOURS, tariff=[0.0] * HOURS)

    _, outcome = _run(scenario)

    assert outcome.succeeded
    assert outcome.total_grid_cost_bdt == pytest.approx(0.0, abs=1e-9)
    assert outcome.total_grid_kwh > 0.0


def test_solar_exceeding_demand_is_feasible_with_curtailment():
    scenario = make_scenario(demand=[5.0] * HOURS, base_solar=[100.0] * HOURS)

    _, outcome = _run(scenario)

    assert outcome.succeeded
    assert outcome.total_grid_cost_bdt == pytest.approx(0.0, abs=1e-9)
    # Surplus is curtailed rather than exported.
    assert all(row.solar_used_kwh <= row.effective_solar_kwh + 1e-6
               for row in outcome.schedule)


def test_infeasible_result_carries_a_message():
    scenario = make_scenario(demand=[10.0] * HOURS, base_solar=[0.0] * HOURS)
    capped = [directive("max_grid_window", {"hours": ALL_HOURS, "max_grid_kwh": 0.0})]

    _, outcome = _run(scenario, capped)

    assert outcome.message
    assert "optimal" in outcome.message.lower()


def test_identity_directives_never_make_a_solvable_scenario_infeasible():
    scenario = make_scenario(demand=[10.0] * HOURS, base_solar=[3.0] * HOURS)

    outcome = solve_dispatch(scenario, NormalizedDirectives.identity())

    assert outcome.succeeded
