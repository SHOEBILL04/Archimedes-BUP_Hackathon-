"""Battery state-of-charge behaviour across the parameter space.

Covers the boundary states (empty / full / partial), degenerate rate limits, and
the charge/discharge efficiency terms. Efficiency below 1.0 is not reachable
through the public API today -- ``BatteryParameters`` exposes no efficiency
fields -- but the optimizer and validator both accept it as a parameter, so the
formulation is pinned here to keep the two layers in agreement.
"""

from __future__ import annotations

import pytest

from app.schemas.optimization import HOURS
from app.services.optimizer import SolverStatus, solve_dispatch
from app.services.validation import NormalizedDirectives, replay_validate

from .conftest import make_battery, make_scenario

TOL = 1e-6
CHEAP_THEN_EXPENSIVE = [5.0] * 12 + [15.0] * 12


def _scenario(battery, demand=10.0, solar=0.0, tariff=None):
    return make_scenario(
        demand=[demand] * HOURS,
        base_solar=[solar] * HOURS,
        tariff=tariff if tariff is not None else CHEAP_THEN_EXPENSIVE,
        battery=battery,
    )


def _solve(scenario, **kwargs):
    return solve_dispatch(scenario, NormalizedDirectives.identity(), **kwargs)


def _assert_state_equation(scenario, outcome, charge_eff=1.0, discharge_eff=1.0):
    """The reported trajectory must satisfy the state equation at every hour."""
    previous = scenario.battery.initial_energy_kwh
    for row in outcome.schedule:
        expected = (
            previous
            + row.battery_charge_kwh * charge_eff
            - row.battery_discharge_kwh / discharge_eff
        )
        assert row.battery_energy_after_kwh == pytest.approx(expected, abs=1e-6)
        previous = row.battery_energy_after_kwh


# --------------------------------------------------------------------------- #
# Starting states
# --------------------------------------------------------------------------- #


def test_empty_battery_starts_and_ends_empty():
    battery = make_battery(initial_energy_kwh=0.0, minimum_energy_kwh=0.0)
    scenario = _scenario(battery)

    outcome = _solve(scenario)

    assert outcome.succeeded
    assert outcome.schedule[-1].battery_energy_after_kwh == pytest.approx(0.0, abs=TOL)
    # It may still charge cheap and discharge expensive, provided it returns to 0.
    _assert_state_equation(scenario, outcome)


def test_empty_battery_cannot_discharge_in_hour_zero():
    """There is nothing stored yet, so hour 0 discharge must be zero."""
    battery = make_battery(initial_energy_kwh=0.0, minimum_energy_kwh=0.0)

    outcome = _solve(_scenario(battery))

    assert outcome.schedule[0].battery_discharge_kwh == pytest.approx(0.0, abs=TOL)


def test_full_battery_cannot_charge_in_hour_zero():
    """Already at capacity, so any hour-0 charge would overflow."""
    battery = make_battery(
        capacity_kwh=100.0, initial_energy_kwh=100.0, minimum_energy_kwh=0.0
    )

    outcome = _solve(_scenario(battery))

    assert outcome.succeeded
    assert outcome.schedule[0].battery_charge_kwh == pytest.approx(0.0, abs=TOL)
    assert outcome.schedule[-1].battery_energy_after_kwh == pytest.approx(100.0, abs=TOL)


def test_full_battery_can_discharge_then_refill():
    battery = make_battery(
        capacity_kwh=100.0, initial_energy_kwh=100.0, minimum_energy_kwh=0.0
    )
    scenario = _scenario(battery)

    outcome = _solve(scenario)

    # Starting full, the only arbitrage is to spend into the expensive window and
    # refill; either way it must end full again.
    assert outcome.succeeded
    assert outcome.schedule[-1].battery_energy_after_kwh == pytest.approx(100.0, abs=TOL)
    _assert_state_equation(scenario, outcome)


def test_partially_charged_battery_returns_to_its_start():
    battery = make_battery(initial_energy_kwh=55.0, minimum_energy_kwh=0.0)
    scenario = _scenario(battery)

    outcome = _solve(scenario)

    assert outcome.succeeded
    assert outcome.schedule[-1].battery_energy_after_kwh == pytest.approx(55.0, abs=TOL)


# --------------------------------------------------------------------------- #
# Degenerate rate limits
# --------------------------------------------------------------------------- #


def _no_battery_cost(scenario) -> float:
    """Cost when the battery cannot move any energy at all."""
    return sum(
        scenario.demand_kwh[h] * scenario.tariff_bdt_per_kwh[h] for h in range(HOURS)
    )


def test_zero_charge_rate_makes_the_battery_unusable():
    """It could discharge, but end-of-day neutrality forbids a net drain, and it
    can never refill -- so the battery must stay idle and saves nothing."""
    battery = make_battery(max_charge_kwh_per_hour=0.0, minimum_energy_kwh=0.0)
    scenario = _scenario(battery)

    outcome = _solve(scenario)

    assert outcome.succeeded
    assert all(row.battery_charge_kwh == pytest.approx(0.0, abs=TOL) for row in outcome.schedule)
    assert all(
        row.battery_discharge_kwh == pytest.approx(0.0, abs=TOL) for row in outcome.schedule
    )
    assert outcome.total_grid_cost_bdt == pytest.approx(_no_battery_cost(scenario), abs=1e-4)


def test_zero_discharge_rate_makes_the_battery_unusable():
    """Charging alone only raises the state of charge, which neutrality forbids."""
    battery = make_battery(max_discharge_kwh_per_hour=0.0, minimum_energy_kwh=0.0)
    scenario = _scenario(battery)

    outcome = _solve(scenario)

    assert outcome.succeeded
    assert all(row.battery_charge_kwh == pytest.approx(0.0, abs=TOL) for row in outcome.schedule)
    assert outcome.total_grid_cost_bdt == pytest.approx(_no_battery_cost(scenario), abs=1e-4)


def test_both_rates_zero_is_still_feasible_and_idle():
    battery = make_battery(
        max_charge_kwh_per_hour=0.0, max_discharge_kwh_per_hour=0.0, minimum_energy_kwh=0.0
    )
    scenario = _scenario(battery)

    outcome = _solve(scenario)

    assert outcome.succeeded
    assert all(
        row.battery_energy_after_kwh == pytest.approx(battery.initial_energy_kwh, abs=TOL)
        for row in outcome.schedule
    )


def test_high_rates_make_capacity_the_binding_constraint():
    """With rates far above capacity, the carryable energy is capped by headroom."""
    battery = make_battery(
        capacity_kwh=100.0,
        initial_energy_kwh=40.0,
        minimum_energy_kwh=0.0,
        max_charge_kwh_per_hour=500.0,
        max_discharge_kwh_per_hour=500.0,
    )
    scenario = _scenario(battery)

    outcome = _solve(scenario)

    assert outcome.succeeded
    assert all(row.battery_energy_after_kwh <= 100.0 + TOL for row in outcome.schedule)
    # Headroom above the mandated final state is 100 - 40 = 60 kWh, saving 10/kWh.
    assert outcome.total_grid_cost_bdt == pytest.approx(2400.0 - 600.0, abs=1e-4)


def test_raising_the_rate_limit_never_increases_cost():
    """Relaxing a constraint can only help; a monotonicity guard on the model."""
    costs = []
    for rate in (5.0, 10.0, 25.0):
        battery = make_battery(
            max_charge_kwh_per_hour=rate,
            max_discharge_kwh_per_hour=rate,
            minimum_energy_kwh=0.0,
        )
        costs.append(_solve(_scenario(battery)).total_grid_cost_bdt)

    assert costs[0] >= costs[1] - 1e-4
    assert costs[1] >= costs[2] - 1e-4


# --------------------------------------------------------------------------- #
# Capacity
# --------------------------------------------------------------------------- #


def test_capacity_limit_is_never_exceeded():
    battery = make_battery(capacity_kwh=45.0, initial_energy_kwh=20.0, minimum_energy_kwh=0.0)

    outcome = _solve(_scenario(battery))

    assert outcome.succeeded
    assert all(row.battery_energy_after_kwh <= 45.0 + TOL for row in outcome.schedule)


def test_larger_capacity_enables_more_saving():
    small = _solve(
        _scenario(make_battery(capacity_kwh=50.0, initial_energy_kwh=10.0, minimum_energy_kwh=0.0))
    )
    large = _solve(
        _scenario(make_battery(capacity_kwh=150.0, initial_energy_kwh=10.0, minimum_energy_kwh=0.0))
    )

    assert large.total_grid_cost_bdt <= small.total_grid_cost_bdt + 1e-4


# --------------------------------------------------------------------------- #
# Efficiency
# --------------------------------------------------------------------------- #


def _arbitrage_battery():
    return make_battery(
        capacity_kwh=100.0,
        initial_energy_kwh=40.0,
        minimum_energy_kwh=0.0,
        max_charge_kwh_per_hour=25.0,
        max_discharge_kwh_per_hour=25.0,
    )


def test_unit_efficiency_baseline():
    """Reference point for the efficiency cases: 60 kWh shifted, saving 10 each."""
    outcome = _solve(_scenario(_arbitrage_battery()))

    assert outcome.total_grid_cost_bdt == pytest.approx(1800.0, abs=1e-4)


def test_charge_efficiency_costs_extra_input_energy():
    """Hand-checked: at 50% charge efficiency, storing 60 kWh draws 120 kWh.

    Bill = (120 demand + 120 charge) * 5 + (120 - 60 delivered) * 15
         = 1200 + 900 = 2100, versus 1800 at unit efficiency.
    """
    scenario = _scenario(_arbitrage_battery())

    outcome = _solve(scenario, charge_efficiency=0.5)

    assert outcome.succeeded
    assert outcome.total_grid_cost_bdt == pytest.approx(2100.0, abs=1e-4)
    _assert_state_equation(scenario, outcome, charge_eff=0.5)


def test_discharge_efficiency_reduces_delivered_energy():
    """Hand-checked: at 50% discharge efficiency, 60 kWh stored delivers 30 kWh.

    Bill = (120 demand + 60 charge) * 5 + (120 - 30 delivered) * 15
         = 900 + 1350 = 2250.
    """
    scenario = _scenario(_arbitrage_battery())

    outcome = _solve(scenario, discharge_efficiency=0.5)

    assert outcome.succeeded
    assert outcome.total_grid_cost_bdt == pytest.approx(2250.0, abs=1e-4)
    _assert_state_equation(scenario, outcome, discharge_eff=0.5)


def test_lower_efficiency_never_beats_higher_efficiency():
    scenario = _scenario(_arbitrage_battery())

    perfect = _solve(scenario)
    lossy = _solve(scenario, charge_efficiency=0.8, discharge_efficiency=0.8)

    assert lossy.total_grid_cost_bdt >= perfect.total_grid_cost_bdt - 1e-4


def test_efficiency_so_poor_that_arbitrage_is_abandoned():
    """Round-trip 10% makes a delivered kWh cost 50 at a tariff of 5 -- worse than
    buying at 15, so the optimizer should leave the battery alone."""
    scenario = _scenario(_arbitrage_battery())

    outcome = _solve(scenario, charge_efficiency=0.1, discharge_efficiency=1.0)

    assert outcome.succeeded
    assert outcome.total_grid_cost_bdt == pytest.approx(_no_battery_cost(scenario), abs=1e-4)


def test_validator_agrees_with_optimizer_on_matching_efficiency():
    scenario = _scenario(_arbitrage_battery())
    normalized = NormalizedDirectives.identity()
    outcome = solve_dispatch(scenario, normalized, charge_efficiency=0.8, discharge_efficiency=0.9)
    assert outcome.succeeded

    result = replay_validate(
        scenario,
        normalized,
        outcome.schedule,
        reported_total_cost_bdt=outcome.total_grid_cost_bdt,
        reported_total_grid_kwh=outcome.total_grid_kwh,
        charge_efficiency=0.8,
        discharge_efficiency=0.9,
    )

    assert result.valid, [str(e) for e in result.errors]


def test_validator_rejects_a_schedule_replayed_with_the_wrong_efficiency():
    """Proof that the validator genuinely replays rather than trusting the report.

    The optimizer runs lossy; the validator is told the battery is lossless, so
    its independent trajectory diverges and the mismatch is reported.
    """
    scenario = _scenario(_arbitrage_battery())
    normalized = NormalizedDirectives.identity()
    outcome = solve_dispatch(scenario, normalized, charge_efficiency=0.5)
    assert outcome.succeeded

    result = replay_validate(scenario, normalized, outcome.schedule)

    assert not result.valid
    assert "battery_state_replay" in {issue.rule for issue in result.errors}


def test_solver_rejects_nonsensical_efficiency():
    scenario = _scenario(_arbitrage_battery())

    for kwargs in ({"charge_efficiency": -0.1}, {"discharge_efficiency": 0.0}):
        with pytest.raises(ValueError):
            solve_dispatch(scenario, NormalizedDirectives.identity(), **kwargs)


# --------------------------------------------------------------------------- #
# Reserve interaction
# --------------------------------------------------------------------------- #


def test_battery_floor_blocks_discharge_below_the_minimum():
    """A floor equal to the starting charge still permits arbitrage.

    The battery may charge above the floor during cheap hours and fall back to
    it later, so the floor caps how deep it can go, not whether it can cycle.
    Headroom is 100 - 40 = 60 kWh, the same as the unconstrained case.
    """
    battery = make_battery(initial_energy_kwh=40.0, minimum_energy_kwh=40.0)
    scenario = _scenario(battery)

    outcome = _solve(scenario)

    assert outcome.succeeded
    assert all(row.battery_energy_after_kwh >= 40.0 - TOL for row in outcome.schedule)
    assert outcome.total_grid_cost_bdt == pytest.approx(1800.0, abs=1e-4)


def test_floor_at_capacity_immobilises_the_battery():
    """When the floor leaves no headroom, no energy can move at all."""
    battery = make_battery(
        capacity_kwh=40.0, initial_energy_kwh=40.0, minimum_energy_kwh=40.0
    )
    scenario = _scenario(battery)

    outcome = _solve(scenario)

    assert outcome.succeeded
    assert all(
        row.battery_energy_after_kwh == pytest.approx(40.0, abs=TOL)
        for row in outcome.schedule
    )
    assert outcome.total_grid_cost_bdt == pytest.approx(_no_battery_cost(scenario), abs=1e-4)


def test_raising_the_floor_never_reduces_cost():
    """A tighter reserve can only remove options."""
    costs = [
        _solve(
            _scenario(
                make_battery(
                    capacity_kwh=100.0, initial_energy_kwh=60.0, minimum_energy_kwh=floor
                )
            )
        ).total_grid_cost_bdt
        for floor in (0.0, 30.0, 60.0)
    ]

    assert costs[1] >= costs[0] - 1e-4
    assert costs[2] >= costs[1] - 1e-4


def test_flat_tariff_removes_any_incentive_to_cycle():
    """With no price spread there is nothing to arbitrage; cost is demand-driven."""
    scenario = _scenario(_arbitrage_battery(), tariff=[7.0] * HOURS)

    outcome = _solve(scenario)

    assert outcome.succeeded
    assert outcome.total_grid_cost_bdt == pytest.approx(_no_battery_cost(scenario), abs=1e-4)


def test_solar_surplus_charges_the_battery_instead_of_being_curtailed():
    """Free surplus solar in cheap hours should be stored rather than wasted."""
    solar = [0.0] * 8 + [40.0] * 6 + [0.0] * 10
    scenario = make_scenario(
        demand=[10.0] * HOURS,
        base_solar=solar,
        tariff=[5.0] * 14 + [30.0] * 10,
        battery=_arbitrage_battery(),
    )

    outcome = _solve(scenario)

    assert outcome.succeeded
    charged_during_surplus = sum(outcome.schedule[h].battery_charge_kwh for h in range(8, 14))
    assert charged_during_surplus > TOL
    assert outcome.status is SolverStatus.OPTIMAL
