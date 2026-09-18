"""Shared fixtures and builders for the guardrail / optimizer / validator suites."""

from __future__ import annotations

from typing import Any

import pytest

from app.schemas.optimization import (
    HOURS,
    BatteryParameters,
    DirectiveInterpretation,
    EnergyScenario,
)


def make_battery(**overrides: float) -> BatteryParameters:
    """Battery with sane defaults; override individual fields per test."""
    params: dict[str, float] = {
        "capacity_kwh": 100.0,
        "initial_energy_kwh": 40.0,
        "minimum_energy_kwh": 10.0,
        "max_charge_kwh_per_hour": 25.0,
        "max_discharge_kwh_per_hour": 25.0,
    }
    params.update(overrides)
    return BatteryParameters(**params)


def make_scenario(
    demand: list[float] | None = None,
    base_solar: list[float] | None = None,
    tariff: list[float] | None = None,
    battery: BatteryParameters | None = None,
    notes: list[str] | None = None,
) -> EnergyScenario:
    """Flat 24-hour scenario; every series defaults to a constant profile."""
    return EnergyScenario(
        demand_kwh=demand if demand is not None else [10.0] * HOURS,
        base_solar_kwh=base_solar if base_solar is not None else [0.0] * HOURS,
        tariff_bdt_per_kwh=tariff if tariff is not None else [5.0] * HOURS,
        battery=battery or make_battery(),
        operator_notes=notes or ["placeholder operator note"],
    )


def directive(
    directive_type: str,
    adjustment: dict[str, Any] | None = None,
    note_index: int = 0,
    applies: bool = True,
) -> DirectiveInterpretation:
    return DirectiveInterpretation(
        note_index=note_index,
        directive_type=directive_type,  # type: ignore[arg-type]
        structured_adjustment=adjustment,
        applies=applies,
    )


@pytest.fixture
def battery() -> BatteryParameters:
    return make_battery()


@pytest.fixture
def scenario() -> EnergyScenario:
    return make_scenario()
