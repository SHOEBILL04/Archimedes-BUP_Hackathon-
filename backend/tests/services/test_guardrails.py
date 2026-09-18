from __future__ import annotations

import pytest

from app.schemas.optimization import BatteryParameters, DirectiveInterpretation, EnergyScenario
from app.services.validation.guardrails import validate_directives


@pytest.fixture
def base_scenario() -> EnergyScenario:
    return EnergyScenario(
        demand_kwh=[30.0] * 24,
        base_solar_kwh=[0.0] * 6 + [20.0] * 12 + [0.0] * 6,
        tariff_bdt_per_kwh=[10.0] * 24,
        battery=BatteryParameters(
            capacity_kwh=100.0,
            initial_energy_kwh=40.0,
            minimum_energy_kwh=10.0,
            max_charge_kwh_per_hour=25.0,
            max_discharge_kwh_per_hour=25.0,
        ),
        operator_notes=["Cut solar by 50% from 10 to 14", "Keep reserve at 30 kWh"],
    )


def test_valid_solar_reduction_passes(base_scenario: EnergyScenario) -> None:
    raw = [
        DirectiveInterpretation(
            note_index=0,
            directive_type="solar_reduction",
            structured_adjustment={"hours": [10, 11, 12, 13], "factor": 0.5},
            applies=True,
        ),
        DirectiveInterpretation(
            note_index=1,
            directive_type="minimum_battery_reserve",
            structured_adjustment={"hours": [10, 11], "minimum_energy_kwh": 30.0},
            applies=True,
        ),
    ]
    validated = validate_directives(base_scenario, raw)
    assert len(validated) == 2
    assert validated[0].applies is True
    assert validated[0].structured_adjustment == {"hours": [10, 11, 12, 13], "factor": 0.5}
    assert validated[1].applies is True
    assert validated[1].structured_adjustment == {"hours": [10, 11], "minimum_energy_kwh": 30.0}


def test_note_count_mismatch_falls_back_to_all_noop(base_scenario: EnergyScenario) -> None:
    # Scenario has 2 notes, raw only provides 1
    raw = [
        DirectiveInterpretation(
            note_index=0,
            directive_type="no_charge_window",
            structured_adjustment={"hours": [18, 19]},
            applies=True,
        )
    ]
    validated = validate_directives(base_scenario, raw)
    assert len(validated) == 2
    assert all(d.directive_type == "no_op" and d.applies is False for d in validated)


def test_note_index_disorder_falls_back_to_all_noop(base_scenario: EnergyScenario) -> None:
    # Wrong indices [1, 0] instead of [0, 1]
    raw = [
        DirectiveInterpretation(
            note_index=1,
            directive_type="no_charge_window",
            structured_adjustment={"hours": [18, 19]},
            applies=True,
        ),
        DirectiveInterpretation(
            note_index=0,
            directive_type="no_discharge_window",
            structured_adjustment={"hours": [10, 11]},
            applies=True,
        ),
    ]
    validated = validate_directives(base_scenario, raw)
    assert len(validated) == 2
    assert all(d.directive_type == "no_op" and d.applies is False for d in validated)


def test_out_of_bounds_reserve_degrades_individual_note(base_scenario: EnergyScenario) -> None:
    # Reserve of 150 kWh exceeds battery capacity of 100 kWh
    raw = [
        DirectiveInterpretation(
            note_index=0,
            directive_type="minimum_battery_reserve",
            structured_adjustment={"hours": [10, 11], "minimum_energy_kwh": 150.0},
            applies=True,
        ),
        DirectiveInterpretation(
            note_index=1,
            directive_type="no_charge_window",
            structured_adjustment={"hours": [18, 19]},
            applies=True,
        ),
    ]
    validated = validate_directives(base_scenario, raw)
    assert validated[0].directive_type == "no_op"
    assert validated[0].applies is False
    assert validated[1].directive_type == "no_charge_window"
    assert validated[1].applies is True


def test_invalid_hours_list_degrades_to_noop(base_scenario: EnergyScenario) -> None:
    # Unsorted or duplicate hours [12, 10]
    raw = [
        DirectiveInterpretation(
            note_index=0,
            directive_type="no_charge_window",
            structured_adjustment={"hours": [12, 10]},
            applies=True,
        ),
        DirectiveInterpretation(
            note_index=1,
            directive_type="max_grid_window",
            structured_adjustment={"hours": [24], "max_grid_kwh": 50.0},  # Hour 24 is out of bounds
            applies=True,
        ),
    ]
    validated = validate_directives(base_scenario, raw)
    assert validated[0].directive_type == "no_op"
    assert validated[1].directive_type == "no_op"


def test_unexpected_keys_rejected(base_scenario: EnergyScenario) -> None:
    raw = [
        DirectiveInterpretation(
            note_index=0,
            directive_type="no_charge_window",
            structured_adjustment={"hours": [18, 19], "malicious_override": True},
            applies=True,
        ),
        DirectiveInterpretation(
            note_index=1,
            directive_type="solar_reduction",
            structured_adjustment={"hours": [12], "factor": 0.5},
            applies=True,
        ),
    ]
    validated = validate_directives(base_scenario, raw)
    assert validated[0].directive_type == "no_op"
    assert validated[1].directive_type == "solar_reduction"
