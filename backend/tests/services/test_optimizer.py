"""LP optimizer tests.

Objective values are asserted rather than exact schedules: several distinct
schedules can share the same optimal cost, so pinning a specific one would make
the suite brittle without testing anything real.
"""

from __future__ import annotations

import pytest

from app.schemas.optimization import HOURS
from app.services.optimizer import SolverStatus, solve_dispatch
from app.services.validation import NormalizedDirectives, normalize_directives

from .conftest import directive, make_battery, make_scenario

TOL = 1e-6


def _solve(scenario, directives=None):
    normalized = (
        normalize_directives(scenario, directives).normalized
        if directives
        else NormalizedDirectives.identity()
    )
    return solve_dispatch(scenario, normalized)


def _idle_battery():
    """Battery that cannot move energy, isolating pure solar/grid behaviour."""
    return make_battery(
        initial_energy_kwh=0.0,
        minimum_energy_kwh=0.0,
        max_charge_kwh_per_hour=0.0,
        max_discharge_kwh_per_hour=0.0,
    )


# --------------------------------------------------------------------------- #
# Basic dispatch
# --------------------------------------------------------------------------- #


def test_demand_with_no_solar_is_met_entirely_from_grid():
    scenario = make_scenario(
        demand=[10.0] * HOURS, base_solar=[0.0] * HOURS, tariff=[5.0] * HOURS,
        battery=_idle_battery(),
    )

    outcome = _solve(scenario)

    assert outcome.succeeded
    assert outcome.total_grid_kwh == pytest.approx(240.0, abs=TOL)
    assert outcome.total_grid_cost_bdt == pytest.approx(1200.0, abs=TOL)
    assert all(row.grid_kwh == pytest.approx(10.0, abs=TOL) for row in outcome.schedule)


def test_solar_covering_demand_eliminates_grid_import():
    scenario = make_scenario(
        demand=[10.0] * HOURS, base_solar=[20.0] * HOURS, tariff=[5.0] * HOURS,
        battery=_idle_battery(),
    )

    outcome = _solve(scenario)

    assert outcome.succeeded
    assert outcome.total_grid_kwh == pytest.approx(0.0, abs=TOL)
    assert outcome.total_grid_cost_bdt == pytest.approx(0.0, abs=TOL)
    # Surplus solar is curtailed, never exported.
    assert all(row.solar_used_kwh <= row.effective_solar_kwh + TOL for row in outcome.schedule)


def test_varying_tariffs_shift_purchasing_to_cheap_hours():
    cheap_then_expensive = [5.0] * 12 + [15.0] * 12
    scenario = make_scenario(
        demand=[10.0] * HOURS,
        base_solar=[0.0] * HOURS,
        tariff=cheap_then_expensive,
        battery=make_battery(minimum_energy_kwh=0.0),
    )

    outcome = _solve(scenario)

    assert outcome.succeeded
    cheap_kwh = sum(row.grid_kwh for row in outcome.schedule[:12])
    expensive_kwh = sum(row.grid_kwh for row in outcome.schedule[12:])
    assert cheap_kwh > expensive_kwh


def test_objective_matches_reported_cost():
    scenario = make_scenario(tariff=[5.0] * 12 + [15.0] * 12)

    outcome = _solve(scenario)

    assert outcome.objective_value == pytest.approx(outcome.total_grid_cost_bdt, abs=1e-4)


# --------------------------------------------------------------------------- #
# Hand-checkable arbitrage
# --------------------------------------------------------------------------- #


def test_hand_checkable_arbitrage_saving():
    """Manual reasoning:

    240 kWh of flat demand, no solar. Tariff is 5 for hours 0-11 and 15 for
    hours 12-23, so with no battery the bill is 120*5 + 120*15 = 2400.

    The battery holds 100 kWh and must finish the day back at its initial
    40 kWh, so at most 100 - 40 = 60 kWh can be carried out of the cheap window
    and spent in the expensive one. Each shifted kWh saves (15 - 5) = 10.

    Expected optimum: 2400 - 60*10 = 1800.
    """
    scenario = make_scenario(
        demand=[10.0] * HOURS,
        base_solar=[0.0] * HOURS,
        tariff=[5.0] * 12 + [15.0] * 12,
        battery=make_battery(
            capacity_kwh=100.0,
            initial_energy_kwh=40.0,
            minimum_energy_kwh=0.0,
            max_charge_kwh_per_hour=25.0,
            max_discharge_kwh_per_hour=25.0,
        ),
    )

    outcome = _solve(scenario)

    assert outcome.succeeded
    assert outcome.total_grid_cost_bdt == pytest.approx(1800.0, abs=1e-4)
    # Net battery throughput over the day is zero, so grid must cover all demand.
    assert outcome.total_grid_kwh == pytest.approx(240.0, abs=1e-4)


# --------------------------------------------------------------------------- #
# Battery behaviour
# --------------------------------------------------------------------------- #


def test_battery_charges_and_discharges_when_arbitrage_available():
    scenario = make_scenario(
        demand=[10.0] * HOURS,
        base_solar=[0.0] * HOURS,
        tariff=[5.0] * 12 + [15.0] * 12,
        battery=make_battery(minimum_energy_kwh=0.0),
    )

    outcome = _solve(scenario)

    assert sum(row.battery_charge_kwh for row in outcome.schedule) > TOL
    assert sum(row.battery_discharge_kwh for row in outcome.schedule) > TOL


def test_battery_never_exceeds_capacity_or_drops_below_zero():
    scenario = make_scenario(
        tariff=[5.0] * 12 + [15.0] * 12,
        battery=make_battery(capacity_kwh=60.0, initial_energy_kwh=30.0, minimum_energy_kwh=0.0),
    )

    outcome = _solve(scenario)

    assert outcome.succeeded
    for row in outcome.schedule:
        assert -TOL <= row.battery_energy_after_kwh <= 60.0 + TOL


def test_charge_rate_limit_respected():
    scenario = make_scenario(
        tariff=[5.0] * 12 + [15.0] * 12,
        battery=make_battery(max_charge_kwh_per_hour=5.0, minimum_energy_kwh=0.0),
    )

    outcome = _solve(scenario)

    assert outcome.succeeded
    assert all(row.battery_charge_kwh <= 5.0 + TOL for row in outcome.schedule)


def test_discharge_rate_limit_respected():
    scenario = make_scenario(
        tariff=[5.0] * 12 + [15.0] * 12,
        battery=make_battery(max_discharge_kwh_per_hour=4.0, minimum_energy_kwh=0.0),
    )

    outcome = _solve(scenario)

    assert outcome.succeeded
    assert all(row.battery_discharge_kwh <= 4.0 + TOL for row in outcome.schedule)


def test_tighter_charge_limit_cannot_beat_looser_one():
    """A rate limit can only remove options, so cost must be >= the looser case."""
    base = {
        "demand": [10.0] * HOURS,
        "base_solar": [0.0] * HOURS,
        "tariff": [5.0] * 12 + [15.0] * 12,
    }
    loose = _solve(make_scenario(**base, battery=make_battery(minimum_energy_kwh=0.0)))
    tight = _solve(
        make_scenario(
            **base,
            battery=make_battery(max_charge_kwh_per_hour=5.0, minimum_energy_kwh=0.0),
        )
    )

    assert tight.total_grid_cost_bdt >= loose.total_grid_cost_bdt - 1e-4


def test_initial_energy_is_the_starting_point_of_hour_zero():
    battery = make_battery(initial_energy_kwh=40.0, minimum_energy_kwh=0.0)
    scenario = make_scenario(tariff=[5.0] * 12 + [15.0] * 12, battery=battery)

    outcome = _solve(scenario)
    first = outcome.schedule[0]

    expected = 40.0 + first.battery_charge_kwh - first.battery_discharge_kwh
    assert first.battery_energy_after_kwh == pytest.approx(expected, abs=1e-6)


def test_end_of_day_neutrality_enforced():
    battery = make_battery(initial_energy_kwh=40.0, minimum_energy_kwh=0.0)
    scenario = make_scenario(tariff=[5.0] * 12 + [15.0] * 12, battery=battery)

    outcome = _solve(scenario)

    assert outcome.schedule[-1].battery_energy_after_kwh == pytest.approx(40.0, abs=1e-6)


def test_battery_state_transition_is_consistent_across_all_hours():
    scenario = make_scenario(tariff=[5.0] * 12 + [15.0] * 12,
                             battery=make_battery(minimum_energy_kwh=0.0))

    outcome = _solve(scenario)

    previous = scenario.battery.initial_energy_kwh
    for row in outcome.schedule:
        expected = previous + row.battery_charge_kwh - row.battery_discharge_kwh
        assert row.battery_energy_after_kwh == pytest.approx(expected, abs=1e-6)
        previous = row.battery_energy_after_kwh


# --------------------------------------------------------------------------- #
# Solar
# --------------------------------------------------------------------------- #


def test_zero_solar_leaves_grid_covering_demand():
    scenario = make_scenario(
        demand=[10.0] * HOURS, base_solar=[0.0] * HOURS, tariff=[5.0] * HOURS,
        battery=_idle_battery(),
    )

    outcome = _solve(scenario)

    assert outcome.total_grid_kwh == pytest.approx(240.0, abs=TOL)


def test_solar_reduction_directive_increases_grid_import():
    scenario = make_scenario(
        demand=[10.0] * HOURS, base_solar=[10.0] * HOURS, tariff=[5.0] * HOURS,
        battery=_idle_battery(),
    )
    # 80% reduction -> 20% remains usable, for every hour of the day.
    reduction = [directive("solar_reduction", {"hours": list(range(HOURS)), "factor": 0.2})]

    full = _solve(scenario)
    reduced = _solve(scenario, reduction)

    assert full.total_grid_kwh == pytest.approx(0.0, abs=TOL)
    # Each hour now has 2 kWh of solar against 10 kWh of demand.
    assert reduced.total_grid_kwh == pytest.approx(8.0 * HOURS, abs=1e-4)
    assert all(row.effective_solar_kwh == pytest.approx(2.0, abs=TOL) for row in reduced.schedule)


def test_solar_used_never_exceeds_effective_solar():
    scenario = make_scenario(demand=[5.0] * HOURS, base_solar=[30.0] * HOURS)

    outcome = _solve(scenario)

    assert all(row.solar_used_kwh <= row.effective_solar_kwh + TOL for row in outcome.schedule)


# --------------------------------------------------------------------------- #
# Directive constraints
# --------------------------------------------------------------------------- #


def test_no_charge_window_blocks_charging():
    scenario = make_scenario(
        tariff=[5.0] * 12 + [15.0] * 12, battery=make_battery(minimum_energy_kwh=0.0)
    )
    blocked = list(range(0, 12))

    outcome = _solve(scenario, [directive("no_charge_window", {"hours": blocked})])

    assert outcome.succeeded
    for hour in blocked:
        assert outcome.schedule[hour].battery_charge_kwh == pytest.approx(0.0, abs=TOL)


def test_no_discharge_window_blocks_discharging():
    scenario = make_scenario(
        tariff=[5.0] * 12 + [15.0] * 12, battery=make_battery(minimum_energy_kwh=0.0)
    )
    blocked = list(range(12, HOURS))

    outcome = _solve(scenario, [directive("no_discharge_window", {"hours": blocked})])

    assert outcome.succeeded
    for hour in blocked:
        assert outcome.schedule[hour].battery_discharge_kwh == pytest.approx(0.0, abs=TOL)


def test_minimum_reserve_directive_holds_state_of_charge_up():
    scenario = make_scenario(
        tariff=[5.0] * 12 + [15.0] * 12,
        battery=make_battery(initial_energy_kwh=60.0, minimum_energy_kwh=0.0),
    )
    hours = [20, 21, 22]

    outcome = _solve(
        scenario,
        [directive("minimum_battery_reserve", {"hours": hours, "minimum_energy_kwh": 55.0})],
    )

    assert outcome.succeeded
    for hour in hours:
        assert outcome.schedule[hour].battery_energy_after_kwh >= 55.0 - TOL


def test_battery_minimum_energy_applies_even_without_a_directive():
    """The scenario's own floor is physical, not an operator instruction."""
    scenario = make_scenario(
        tariff=[5.0] * 12 + [15.0] * 12,
        battery=make_battery(initial_energy_kwh=40.0, minimum_energy_kwh=25.0),
    )

    outcome = _solve(scenario)

    assert outcome.succeeded
    assert all(row.battery_energy_after_kwh >= 25.0 - TOL for row in outcome.schedule)


def test_max_grid_window_caps_import():
    scenario = make_scenario(
        demand=[10.0] * HOURS, base_solar=[0.0] * HOURS, tariff=[5.0] * HOURS
    )
    hours = [8, 9, 10]

    outcome = _solve(scenario, [directive("max_grid_window", {"hours": hours, "max_grid_kwh": 4.0})])

    assert outcome.succeeded
    for hour in hours:
        assert outcome.schedule[hour].grid_kwh <= 4.0 + TOL


# --------------------------------------------------------------------------- #
# Combined directives
# --------------------------------------------------------------------------- #


def test_multiple_directives_applied_simultaneously():
    scenario = make_scenario(
        demand=[10.0] * HOURS,
        base_solar=[8.0] * HOURS,
        tariff=[5.0] * 12 + [15.0] * 12,
        battery=make_battery(minimum_energy_kwh=0.0),
    )
    directives = [
        directive("solar_reduction", {"hours": [13, 14, 15], "factor": 0.2}, note_index=0),
        directive("no_charge_window", {"hours": [18, 19, 20]}, note_index=1),
        directive("max_grid_window", {"hours": [21], "max_grid_kwh": 6.0}, note_index=2),
    ]

    outcome = _solve(scenario, directives)

    assert outcome.succeeded
    for hour in (13, 14, 15):
        assert outcome.schedule[hour].effective_solar_kwh == pytest.approx(1.6, abs=TOL)
    for hour in (18, 19, 20):
        assert outcome.schedule[hour].battery_charge_kwh == pytest.approx(0.0, abs=TOL)
    assert outcome.schedule[21].grid_kwh <= 6.0 + TOL


def test_energy_balance_holds_for_every_hour():
    scenario = make_scenario(
        demand=[12.0] * HOURS,
        base_solar=[6.0] * HOURS,
        tariff=[5.0] * 12 + [15.0] * 12,
        battery=make_battery(minimum_energy_kwh=0.0),
    )

    outcome = _solve(scenario)

    for row in outcome.schedule:
        supply = row.grid_kwh + row.solar_used_kwh + row.battery_discharge_kwh
        consumption = row.demand_kwh + row.battery_charge_kwh
        assert supply == pytest.approx(consumption, abs=1e-6)


# --------------------------------------------------------------------------- #
# Simultaneous charge / discharge investigation (brief section 19)
# --------------------------------------------------------------------------- #


def test_simultaneous_charge_and_discharge_never_occurs():
    """Investigate whether the LP needs a binary to forbid simultaneous cycling.

    With a round-trip efficiency of 1.0 the pair (charge += d, discharge += d)
    leaves both the energy balance and the battery state equation unchanged, so
    it cannot alter the objective: simultaneous operation is cost-NEUTRAL, never
    cost-IMPROVING. There is therefore no incentive for the solver to use it, and
    no binary variable is required. The model stays a pure LP.

    Were any efficiency below 1.0 introduced, simultaneous operation would
    strictly destroy energy and thus be actively penalised -- still no binary.

    Because it is merely neutral rather than forbidden, a degenerate optimum
    containing both could in principle be returned. This test pins the observed
    CBC behaviour so that a regression would surface as a failure here rather
    than as a physically odd schedule downstream.
    """
    scenario = make_scenario(
        demand=[10.0] * HOURS,
        base_solar=[5.0] * HOURS,
        tariff=[5.0] * 6 + [20.0] * 6 + [5.0] * 6 + [20.0] * 6,
        battery=make_battery(minimum_energy_kwh=0.0),
    )

    outcome = _solve(scenario)

    assert outcome.succeeded
    overlapping = [
        row.hour
        for row in outcome.schedule
        if row.battery_charge_kwh > 1e-6 and row.battery_discharge_kwh > 1e-6
    ]
    assert overlapping == [], f"simultaneous charge/discharge at hours {overlapping}"


# --------------------------------------------------------------------------- #
# Solver status handling
# --------------------------------------------------------------------------- #


def test_infeasible_scenario_reports_infeasible_and_no_schedule():
    # Grid capped at zero all day, battery must end where it started, and there
    # is no solar: the demand simply cannot be served.
    scenario = make_scenario(demand=[10.0] * HOURS, base_solar=[0.0] * HOURS)
    capped = [directive("max_grid_window", {"hours": list(range(HOURS)), "max_grid_kwh": 0.0})]

    outcome = _solve(scenario, capped)

    assert outcome.status is SolverStatus.INFEASIBLE
    assert not outcome.succeeded
    # An invalid schedule must never be returned as a success.
    assert outcome.schedule == ()
    assert outcome.total_grid_cost_bdt == pytest.approx(0.0)


def test_invalid_efficiency_rejected():
    scenario = make_scenario()

    with pytest.raises(ValueError, match="charge_efficiency"):
        solve_dispatch(scenario, NormalizedDirectives.identity(), charge_efficiency=0.0)

    with pytest.raises(ValueError, match="discharge_efficiency"):
        solve_dispatch(scenario, NormalizedDirectives.identity(), discharge_efficiency=1.5)


def test_optimizer_is_deterministic():
    scenario = make_scenario(tariff=[5.0] * 12 + [15.0] * 12)

    costs = [_solve(scenario).total_grid_cost_bdt for _ in range(3)]

    assert all(cost == pytest.approx(costs[0], abs=1e-9) for cost in costs)


def test_optimizer_does_not_mutate_scenario():
    scenario = make_scenario(base_solar=[9.0] * HOURS, tariff=[5.0] * 12 + [15.0] * 12)
    before = scenario.model_dump()

    _solve(scenario, [directive("solar_reduction", {"hours": [10], "factor": 0.3})])

    assert scenario.model_dump() == before
