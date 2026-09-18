from __future__ import annotations

from app.schemas.optimization import BatteryParameters, DirectiveInterpretation, EnergyScenario
from app.services.validation.compiler import compile_directives


def get_scenario() -> EnergyScenario:
    return EnergyScenario(
        demand_kwh=[50.0] * 24,
        base_solar_kwh=[0.0] * 6 + [30.0] * 12 + [0.0] * 6,
        tariff_bdt_per_kwh=[10.0] * 24,
        battery=BatteryParameters(
            capacity_kwh=100.0,
            initial_energy_kwh=40.0,
            minimum_energy_kwh=10.0,
            max_charge_kwh_per_hour=25.0,
            max_discharge_kwh_per_hour=25.0,
        ),
        operator_notes=["note 1", "note 2", "note 3"],
    )


def test_empty_directives_yields_baseline() -> None:
    scenario = get_scenario()
    compiled = compile_directives(scenario, [])
    assert len(compiled.solar_factor) == 24
    assert all(f == 1.0 for f in compiled.solar_factor)
    assert compiled.effective_solar == scenario.base_solar_kwh
    assert all(r == 10.0 for r in compiled.min_reserve)
    assert all(not c for c in compiled.no_charge)
    assert all(not d for d in compiled.no_discharge)
    assert all(g is None for g in compiled.max_grid)


def test_overlapping_solar_reductions_multiply() -> None:
    scenario = get_scenario()
    directives = [
        DirectiveInterpretation(
            note_index=0,
            directive_type="solar_reduction",
            structured_adjustment={"hours": [11, 12, 13], "factor": 0.5},
            applies=True,
        ),
        DirectiveInterpretation(
            note_index=1,
            directive_type="solar_reduction",
            structured_adjustment={"hours": [12, 13, 14], "factor": 0.8},
            applies=True,
        ),
    ]
    compiled = compile_directives(scenario, directives)
    assert compiled.solar_factor[11] == 0.5
    assert abs(compiled.solar_factor[12] - 0.4) < 1e-9  # 0.5 * 0.8
    assert abs(compiled.solar_factor[13] - 0.4) < 1e-9
    assert compiled.solar_factor[14] == 0.8
    assert compiled.solar_factor[10] == 1.0


def test_overlapping_battery_reserves_takes_max() -> None:
    scenario = get_scenario()
    directives = [
        DirectiveInterpretation(
            note_index=0,
            directive_type="minimum_battery_reserve",
            structured_adjustment={"hours": [8, 9], "minimum_energy_kwh": 30.0},
            applies=True,
        ),
        DirectiveInterpretation(
            note_index=1,
            directive_type="minimum_battery_reserve",
            structured_adjustment={"hours": [9, 10], "minimum_energy_kwh": 50.0},
            applies=True,
        ),
    ]
    compiled = compile_directives(scenario, directives)
    assert compiled.min_reserve[8] == 30.0
    assert compiled.min_reserve[9] == 50.0  # max(30, 50)
    assert compiled.min_reserve[10] == 50.0
    assert compiled.min_reserve[11] == 10.0  # baseline


def test_no_charge_window_union() -> None:
    scenario = get_scenario()
    directives = [
        DirectiveInterpretation(
            note_index=0,
            directive_type="no_charge_window",
            structured_adjustment={"hours": [18, 19]},
            applies=True,
        ),
        DirectiveInterpretation(
            note_index=1,
            directive_type="no_charge_window",
            structured_adjustment={"hours": [19, 20]},
            applies=True,
        ),
    ]
    compiled = compile_directives(scenario, directives)
    assert compiled.no_charge[18] is True
    assert compiled.no_charge[19] is True
    assert compiled.no_charge[20] is True
    assert compiled.no_charge[21] is False


def test_overlapping_max_grid_takes_min() -> None:
    scenario = get_scenario()
    directives = [
        DirectiveInterpretation(
            note_index=0,
            directive_type="max_grid_window",
            structured_adjustment={"hours": [14, 15], "max_grid_kwh": 40.0},
            applies=True,
        ),
        DirectiveInterpretation(
            note_index=1,
            directive_type="max_grid_window",
            structured_adjustment={"hours": [15, 16], "max_grid_kwh": 30.0},
            applies=True,
        ),
    ]
    compiled = compile_directives(scenario, directives)
    assert compiled.max_grid[14] == 40.0
    assert compiled.max_grid[15] == 30.0  # min(40, 30)
    assert compiled.max_grid[16] == 30.0
    assert compiled.max_grid[17] is None
