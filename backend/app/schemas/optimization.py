from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

HOURS = 24
DirectiveType = Literal[
    "solar_reduction",
    "minimum_battery_reserve",
    "no_charge_window",
    "no_discharge_window",
    "max_grid_window",
    "no_op",
]


def _finite_nonnegative(value: float) -> float:
    if not math.isfinite(value) or value < 0:
        raise ValueError("must be a finite non-negative number")
    return value


class BatteryParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capacity_kwh: float = Field(gt=0, description="Total battery capacity in kWh")
    initial_energy_kwh: float = Field(ge=0, description="Battery initial energy in kWh")
    minimum_energy_kwh: float = Field(ge=0, description="Minimum battery reserve in kWh")
    max_charge_kwh_per_hour: float = Field(ge=0, description="Maximum charge rate in kWh/h")
    max_discharge_kwh_per_hour: float = Field(ge=0, description="Maximum discharge rate in kWh/h")

    @field_validator(
        "capacity_kwh",
        "initial_energy_kwh",
        "minimum_energy_kwh",
        "max_charge_kwh_per_hour",
        "max_discharge_kwh_per_hour",
    )
    @classmethod
    def finite(cls, value: float) -> float:
        return _finite_nonnegative(value)

    @model_validator(mode="after")
    def validate_relationships(self) -> BatteryParameters:
        if self.initial_energy_kwh > self.capacity_kwh:
            raise ValueError("initial_energy_kwh cannot exceed capacity_kwh")
        if self.minimum_energy_kwh > self.capacity_kwh:
            raise ValueError("minimum_energy_kwh cannot exceed capacity_kwh")
        if self.initial_energy_kwh < self.minimum_energy_kwh:
            raise ValueError("initial_energy_kwh cannot be below minimum_energy_kwh")
        return self


class EnergyScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    demand_kwh: list[float] = Field(
        min_length=HOURS, max_length=HOURS, description="24 hourly demand values in kWh"
    )
    base_solar_kwh: list[float] = Field(
        min_length=HOURS, max_length=HOURS, description="24 hourly baseline solar values in kWh"
    )
    tariff_bdt_per_kwh: list[float] = Field(
        min_length=HOURS, max_length=HOURS, description="24 hourly grid tariffs in BDT/kWh"
    )
    battery: BatteryParameters
    operator_notes: list[str] = Field(
        min_length=1, max_length=3, description="1 to 3 operator natural language notes"
    )

    @field_validator("demand_kwh", "base_solar_kwh", "tariff_bdt_per_kwh")
    @classmethod
    def validate_arrays(cls, values: list[float]) -> list[float]:
        return [_finite_nonnegative(v) for v in values]

    @field_validator("operator_notes")
    @classmethod
    def validate_notes(cls, notes: list[str]) -> list[str]:
        cleaned: list[str] = []
        for note in notes:
            if not isinstance(note, str) or not note.strip():
                raise ValueError("operator notes must be non-empty strings")
            if len(note) > 2000:
                raise ValueError("each operator note must be at most 2000 characters")
            cleaned.append(note.strip())
        return cleaned


class DirectiveInterpretation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note_index: int = Field(ge=0, le=2)
    directive_type: DirectiveType
    structured_adjustment: dict[str, Any] | None = None
    applies: bool = True


class DirectiveInterpretationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interpretations: list[DirectiveInterpretation] = Field(min_length=1, max_length=3)


class HourSchedule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hour: int = Field(ge=0, le=23)
    demand_kwh: float = Field(ge=0)
    effective_solar_kwh: float = Field(ge=0)
    solar_used_kwh: float = Field(ge=0)
    battery_charge_kwh: float = Field(ge=0)
    battery_discharge_kwh: float = Field(ge=0)
    battery_energy_after_kwh: float = Field(ge=0)
    grid_kwh: float = Field(ge=0)
    tariff_bdt_per_kwh: float = Field(ge=0)
    grid_cost_bdt: float = Field(ge=0)


class VerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verified: bool = Field(default=True)
    max_constraint_error: float = Field(ge=0, default=0.0)
    total_grid_cost_bdt: float = Field(ge=0)


class OptimizationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    directive_interpretation: list[DirectiveInterpretation]
    schedule: list[HourSchedule] = Field(min_length=HOURS, max_length=HOURS)
    total_grid_cost_bdt: float = Field(ge=0)
    total_grid_kwh: float = Field(ge=0)
    verification: VerificationResult
    status_message: str = Field(
        default="[SCAFFOLD_PLACEHOLDER] Optimization pipeline scaffold response. Business logic will be implemented in next phase."
    )
