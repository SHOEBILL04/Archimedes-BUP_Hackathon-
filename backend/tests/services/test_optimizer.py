from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.schemas.optimization import BatteryParameters, EnergyScenario
from app.services.optimizer.exceptions import OptimizationInfeasibleError
from app.services.optimizer.solver import EnergyOptimizer
from app.services.validation.compiler import compile_directives


@pytest.fixture
def sample_scenario() -> EnergyScenario:
    sample_path = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "docs"
        / "reference"
        / "sample_request.json"
    )
    with open(sample_path, encoding="utf-8") as f:
        data = json.load(f)
    return EnergyScenario.model_validate(data)


def test_solve_sample_scenario_success(sample_scenario: EnergyScenario) -> None:
    optimizer = EnergyOptimizer(timeout_seconds=5.0)
    compiled = compile_directives(sample_scenario, [])
    schedules, total_cost, total_grid = optimizer.solve(sample_scenario, compiled)

    assert len(schedules) == 24
    assert total_cost > 0.0
    assert total_grid > 0.0

    # Ensure end-of-day neutrality
    initial_energy = sample_scenario.battery.initial_energy_kwh
    final_energy = schedules[23].battery_energy_after_kwh
    assert abs(final_energy - initial_energy) < 1e-5

    # Check non-negativity across all variables
    for row in schedules:
        assert row.grid_kwh >= 0.0
        assert row.solar_used_kwh >= 0.0
        assert row.battery_charge_kwh >= 0.0
        assert row.battery_discharge_kwh >= 0.0
        assert row.battery_energy_after_kwh >= sample_scenario.battery.minimum_energy_kwh - 1e-5
        assert row.battery_energy_after_kwh <= sample_scenario.battery.capacity_kwh + 1e-5


def test_solve_battery_arbitrage() -> None:
    # High tariff at hours 18-20, very cheap tariff at hours 1-3
    tariffs = [10.0] * 24
    for h in [1, 2, 3]:
        tariffs[h] = 2.0  # cheap
    for h in [18, 19, 20]:
        tariffs[h] = 30.0  # peak

    scenario = EnergyScenario(
        demand_kwh=[20.0] * 24,
        base_solar_kwh=[0.0] * 24,  # no solar to isolate battery behavior
        tariff_bdt_per_kwh=tariffs,
        battery=BatteryParameters(
            capacity_kwh=100.0,
            initial_energy_kwh=30.0,
            minimum_energy_kwh=10.0,
            max_charge_kwh_per_hour=20.0,
            max_discharge_kwh_per_hour=20.0,
        ),
        operator_notes=["Arbitrage test"],
    )
    optimizer = EnergyOptimizer()
    compiled = compile_directives(scenario, [])
    schedules, total_cost, total_grid = optimizer.solve(scenario, compiled)

    # Battery should charge during cheap hours
    cheap_charges = sum(schedules[h].battery_charge_kwh for h in [1, 2, 3])
    assert cheap_charges > 0.0

    # Battery should discharge during peak hours
    peak_discharges = sum(schedules[h].battery_discharge_kwh for h in [18, 19, 20])
    assert peak_discharges > 0.0


def test_infeasible_scenario_raises_error() -> None:
    # Demand is 100 kWh, solar is 0, battery max discharge is 10 kWh, grid import ceiling is 20 kWh
    # Total possible supply is 30 kWh, which cannot meet 100 kWh demand.
    scenario = EnergyScenario(
        demand_kwh=[100.0] * 24,
        base_solar_kwh=[0.0] * 24,
        tariff_bdt_per_kwh=[10.0] * 24,
        battery=BatteryParameters(
            capacity_kwh=100.0,
            initial_energy_kwh=50.0,
            minimum_energy_kwh=10.0,
            max_charge_kwh_per_hour=10.0,
            max_discharge_kwh_per_hour=10.0,
        ),
        operator_notes=["Test note"],
    )
    from app.services.validation.models import CompiledDirectives

    # Inject an impossible grid ceiling of 20 kWh
    compiled = CompiledDirectives(
        solar_factor=[1.0] * 24,
        effective_solar=[0.0] * 24,
        min_reserve=[10.0] * 24,
        no_charge=[False] * 24,
        no_discharge=[False] * 24,
        max_grid=[20.0] * 24,
    )

    optimizer = EnergyOptimizer()
    with pytest.raises(OptimizationInfeasibleError):
        optimizer.solve(scenario, compiled)
