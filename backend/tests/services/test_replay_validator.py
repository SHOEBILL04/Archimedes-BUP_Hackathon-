from __future__ import annotations

import pytest

from app.schemas.optimization import BatteryParameters, EnergyScenario, HourSchedule
from app.services.optimizer.solver import EnergyOptimizer
from app.services.validation.compiler import compile_directives
from app.services.validation.exceptions import ReplayValidationError
from app.services.validation.replay import replay_validate


@pytest.fixture
def baseline_setup():
    scenario = EnergyScenario(
        demand_kwh=[30.0] * 24,
        base_solar_kwh=[0.0] * 6 + [25.0] * 12 + [0.0] * 6,
        tariff_bdt_per_kwh=[10.0] * 24,
        battery=BatteryParameters(
            capacity_kwh=100.0,
            initial_energy_kwh=40.0,
            minimum_energy_kwh=10.0,
            max_charge_kwh_per_hour=25.0,
            max_discharge_kwh_per_hour=25.0,
        ),
        operator_notes=["Baseline test"],
    )
    compiled = compile_directives(scenario, [])
    optimizer = EnergyOptimizer()
    schedules, total_cost, total_grid = optimizer.solve(scenario, compiled)
    return scenario, compiled, schedules, total_cost


def test_valid_schedule_replay_passes(baseline_setup):
    scenario, compiled, schedules, total_cost = baseline_setup
    result = replay_validate(
        scenario=scenario,
        directives=compiled,
        schedule=schedules,
        reported_total_cost=total_cost,
    )
    assert result.verified is True
    assert result.max_constraint_error < 1e-5
    assert abs(result.total_grid_cost_bdt - total_cost) < 1e-5


def test_energy_balance_violation_raises(baseline_setup):
    scenario, compiled, schedules, total_cost = baseline_setup
    # Artificially alter grid import at hour 5 to create an imbalance
    corrupted_schedule = [
        HourSchedule(
            hour=s.hour,
            demand_kwh=s.demand_kwh,
            effective_solar_kwh=s.effective_solar_kwh,
            solar_used_kwh=s.solar_used_kwh,
            battery_charge_kwh=s.battery_charge_kwh,
            battery_discharge_kwh=s.battery_discharge_kwh,
            battery_energy_after_kwh=s.battery_energy_after_kwh,
            grid_kwh=s.grid_kwh + (5.0 if s.hour == 5 else 0.0),
            tariff_bdt_per_kwh=s.tariff_bdt_per_kwh,
            grid_cost_bdt=s.grid_cost_bdt,
        )
        for s in schedules
    ]
    with pytest.raises(ReplayValidationError) as exc_info:
        replay_validate(
            scenario=scenario,
            directives=compiled,
            schedule=corrupted_schedule,
            reported_total_cost=total_cost,
        )
    assert "energy_balance" in str(exc_info.value)


def test_battery_dynamics_violation_raises(baseline_setup):
    scenario, compiled, schedules, total_cost = baseline_setup
    # Artificially alter battery state of charge at hour 2
    corrupted_schedule = [
        HourSchedule(
            hour=s.hour,
            demand_kwh=s.demand_kwh,
            effective_solar_kwh=s.effective_solar_kwh,
            solar_used_kwh=s.solar_used_kwh,
            battery_charge_kwh=s.battery_charge_kwh,
            battery_discharge_kwh=s.battery_discharge_kwh,
            battery_energy_after_kwh=s.battery_energy_after_kwh + (10.0 if s.hour == 2 else 0.0),
            grid_kwh=s.grid_kwh,
            tariff_bdt_per_kwh=s.tariff_bdt_per_kwh,
            grid_cost_bdt=s.grid_cost_bdt,
        )
        for s in schedules
    ]
    with pytest.raises(ReplayValidationError) as exc_info:
        replay_validate(
            scenario=scenario,
            directives=compiled,
            schedule=corrupted_schedule,
            reported_total_cost=total_cost,
        )
    assert "battery_dynamics" in str(exc_info.value)


def test_end_of_day_neutrality_violation_raises(baseline_setup):
    scenario, compiled, schedules, total_cost = baseline_setup
    # Artificially change hour 23 battery energy to not match initial
    corrupted_schedule = [
        HourSchedule(
            hour=s.hour,
            demand_kwh=s.demand_kwh,
            effective_solar_kwh=s.effective_solar_kwh,
            solar_used_kwh=s.solar_used_kwh,
            battery_charge_kwh=s.battery_charge_kwh,
            battery_discharge_kwh=s.battery_discharge_kwh,
            battery_energy_after_kwh=s.battery_energy_after_kwh + (5.0 if s.hour == 23 else 0.0),
            grid_kwh=s.grid_kwh,
            tariff_bdt_per_kwh=s.tariff_bdt_per_kwh,
            grid_cost_bdt=s.grid_cost_bdt,
        )
        for s in schedules
    ]
    with pytest.raises(ReplayValidationError) as exc_info:
        replay_validate(
            scenario=scenario,
            directives=compiled,
            schedule=corrupted_schedule,
            reported_total_cost=total_cost,
        )
    assert "end_of_day_neutrality" in str(exc_info.value) or "battery_dynamics" in str(
        exc_info.value
    )


def test_reported_cost_mismatch_raises(baseline_setup):
    scenario, compiled, schedules, total_cost = baseline_setup
    # Pass a wrong reported_total_cost
    with pytest.raises(ReplayValidationError) as exc_info:
        replay_validate(
            scenario=scenario,
            directives=compiled,
            schedule=schedules,
            reported_total_cost=total_cost + 500.0,
        )
    assert "reported_objective_consistency" in str(exc_info.value)
