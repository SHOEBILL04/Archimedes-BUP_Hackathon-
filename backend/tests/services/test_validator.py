"""Tests for the deterministic independent replay validation engine."""

from __future__ import annotations

import pytest

from app.services.optimizer.guardrails import CompiledDirectives
from app.services.optimizer.lp_optimizer import HourResult
from app.services.validation import (
    ReplayValidationError,
    ReplayValidationInput,
    replay_validate,
    validate_and_raise,
)


def make_valid_input(battery_kwh: float = 50.0) -> ReplayValidationInput:
    """Construct a clean, baseline valid 24-hour scenario and schedule."""
    demand = [30.0] * 24
    tariff = [10.0] * 24
    base_solar = [0.0] * 24
    compiled = CompiledDirectives(
        solar_factor=[1.0] * 24,
        effective_solar=base_solar,
        min_reserve=[10.0] * 24,
        no_charge=[False] * 24,
        no_discharge=[False] * 24,
        max_grid=[None] * 24,
    )
    schedule = [
        HourResult(
            hour=h,
            demand_kwh=30.0,
            effective_solar_kwh=0.0,
            solar_used_kwh=0.0,
            battery_charge_kwh=0.0,
            battery_discharge_kwh=0.0,
            battery_energy_after_kwh=battery_kwh,
            grid_kwh=30.0,
            tariff_bdt_per_kwh=10.0,
            grid_cost_bdt=300.0,
        )
        for h in range(24)
    ]
    return ReplayValidationInput(
        demand=demand,
        base_solar=base_solar,
        tariff=tariff,
        battery_capacity=100.0,
        battery_initial_energy=battery_kwh,
        battery_min_energy=10.0,
        battery_max_charge_per_hour=25.0,
        battery_max_discharge_per_hour=25.0,
        compiled_directives=compiled,
        schedule=schedule,
        reported_total_cost=7200.0,
    )


# ── Passing tests ──


def test_valid_schedule_passes():
    val_in = make_valid_input()
    res = replay_validate(val_in)
    assert res.verified is True
    assert len(res.errors) == 0
    assert res.max_constraint_error < 1e-4
    assert res.recalculated_total_cost == 7200.0


def test_zero_cost_schedule_passes():
    val_in = make_valid_input()
    val_in.demand = [0.0] * 24
    val_in.reported_total_cost = 0.0
    for h in val_in.schedule:
        h.demand_kwh = 0.0
        h.grid_kwh = 0.0
        h.grid_cost_bdt = 0.0

    res = replay_validate(val_in)
    assert res.verified is True
    assert res.recalculated_total_cost == 0.0


# ── Failing tests (injected violations) ──


def test_wrong_schedule_length():
    val_in = make_valid_input()
    val_in.schedule = val_in.schedule[:23]
    res = replay_validate(val_in)
    assert res.verified is False
    assert any("must contain 24 hourly entries" in e for e in res.errors)


def test_energy_balance_violation():
    val_in = make_valid_input()
    val_in.schedule[5].grid_kwh += 1.0  # extra supply without demand or charging
    res = replay_validate(val_in)
    assert res.verified is False
    assert any("energy balance error" in e for e in res.errors)


def test_solar_overuse():
    val_in = make_valid_input()
    val_in.schedule[10].solar_used_kwh = 5.0  # base solar is 0.0
    # adjust grid to maintain energy balance to isolate solar overuse check
    val_in.schedule[10].grid_kwh = 25.0
    val_in.reported_total_cost -= 50.0
    res = replay_validate(val_in)
    assert res.verified is False
    assert any("solar overuse" in e for e in res.errors)


def test_negative_grid():
    val_in = make_valid_input()
    val_in.schedule[3].grid_kwh = -1.0
    res = replay_validate(val_in)
    assert res.verified is False
    assert any("negative value in grid_kwh" in e for e in res.errors)


def test_battery_above_capacity():
    val_in = make_valid_input()
    val_in.schedule[7].battery_energy_after_kwh = val_in.battery_capacity + 1.0
    res = replay_validate(val_in)
    assert res.verified is False
    assert any("battery above capacity" in e for e in res.errors)


def test_battery_below_reserve():
    val_in = make_valid_input()
    val_in.schedule[15].battery_energy_after_kwh = val_in.battery_min_energy - 1.0
    res = replay_validate(val_in)
    assert res.verified is False
    assert any("battery below reserve" in e for e in res.errors)


def test_battery_dynamics_violated():
    val_in = make_valid_input()
    # Unexpected jump in state of charge with zero charging
    val_in.schedule[5].battery_energy_after_kwh += 5.0
    res = replay_validate(val_in)
    assert res.verified is False
    assert any("battery dynamics error" in e for e in res.errors)


def test_charge_exceeds_rate():
    val_in = make_valid_input()
    val_in.schedule[3].battery_charge_kwh = val_in.battery_max_charge_per_hour + 5.0
    res = replay_validate(val_in)
    assert res.verified is False
    assert any("charge rate violation" in e for e in res.errors)


def test_discharge_exceeds_rate():
    val_in = make_valid_input()
    val_in.schedule[20].battery_discharge_kwh = val_in.battery_max_discharge_per_hour + 5.0
    res = replay_validate(val_in)
    assert res.verified is False
    assert any("discharge rate violation" in e for e in res.errors)


def test_no_charge_violated():
    val_in = make_valid_input()
    val_in.compiled_directives.no_charge[10] = True
    val_in.schedule[10].battery_charge_kwh = 5.0
    res = replay_validate(val_in)
    assert res.verified is False
    assert any("charge rate violation" in e for e in res.errors)


def test_no_discharge_violated():
    val_in = make_valid_input()
    val_in.compiled_directives.no_discharge[10] = True
    val_in.schedule[10].battery_discharge_kwh = 5.0
    res = replay_validate(val_in)
    assert res.verified is False
    assert any("discharge rate violation" in e for e in res.errors)


def test_end_of_day_neutrality_fail():
    val_in = make_valid_input()
    val_in.schedule[23].battery_energy_after_kwh = val_in.battery_initial_energy + 10.0
    res = replay_validate(val_in)
    assert res.verified is False
    assert any("End-of-day battery mismatch" in e for e in res.errors)


def test_reported_cost_mismatch():
    val_in = make_valid_input()
    val_in.reported_total_cost += 100.0
    res = replay_validate(val_in)
    assert res.verified is False
    assert any("Reported cost" in e for e in res.errors)


def test_max_grid_violated():
    val_in = make_valid_input()
    val_in.compiled_directives.max_grid[5] = 20.0
    # schedule has grid_kwh = 30.0 at hour 5
    res = replay_validate(val_in)
    assert res.verified is False
    assert any("grid exceeds max_grid directive" in e for e in res.errors)


# ── Convenience wrapper tests ──


def test_validate_and_raise_raises():
    val_in = make_valid_input()
    val_in.schedule[5].grid_kwh += 1.0
    with pytest.raises(ReplayValidationError, match="Replay validation failed"):
        validate_and_raise(val_in)


def test_validate_and_raise_passes():
    val_in = make_valid_input()
    res = validate_and_raise(val_in)
    assert res.verified is True
