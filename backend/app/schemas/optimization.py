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


class ScenarioHour(BaseModel):
    model_config = ConfigDict(extra="ignore")

    hour: int = Field(ge=0, le=23)
    demand_kwh: float = Field(ge=0)
    solar_kwh: float = Field(ge=0)
    tariff_bdt_per_kwh: float = Field(ge=0)


class EnergyScenario(BaseModel):
    model_config = ConfigDict(extra="ignore")

    scenario_id: str | None = Field(default=None, description="Scenario ID from judge test pack")
    hours: list[ScenarioHour] | None = Field(default=None, description="24 hourly entries")
    demand_kwh: list[float] | None = Field(
        default=None, min_length=HOURS, max_length=HOURS, description="24 hourly demand values in kWh"
    )
    base_solar_kwh: list[float] | None = Field(
        default=None, min_length=HOURS, max_length=HOURS, description="24 hourly baseline solar values in kWh"
    )
    tariff_bdt_per_kwh: list[float] | None = Field(
        default=None, min_length=HOURS, max_length=HOURS, description="24 hourly grid tariffs in BDT/kWh"
    )
    battery: BatteryParameters
    operator_notes: list[str] = Field(
        min_length=1, max_length=3, description="1 to 3 operator natural language notes"
    )

    @model_validator(mode="before")
    @classmethod
    def unpack_hours_if_present(cls, data: Any) -> Any:
        if isinstance(data, dict) and "hours" in data and data["hours"] is not None:
            raw_hours = data["hours"]
            if len(raw_hours) != HOURS:
                raise ValueError(f"hours must have exactly {HOURS} elements")
            sorted_hours = sorted(raw_hours, key=lambda x: x.get("hour", 0) if isinstance(x, dict) else x.hour)
            demand = []
            solar = []
            tariff = []
            for h in sorted_hours:
                if isinstance(h, dict):
                    demand.append(float(h["demand_kwh"]))
                    solar.append(float(h.get("solar_kwh", h.get("base_solar_kwh", 0.0))))
                    tariff.append(float(h["tariff_bdt_per_kwh"]))
                else:
                    demand.append(float(h.demand_kwh))
                    solar.append(float(h.solar_kwh))
                    tariff.append(float(h.tariff_bdt_per_kwh))
            data["demand_kwh"] = demand
            data["base_solar_kwh"] = solar
            data["tariff_bdt_per_kwh"] = tariff
        elif isinstance(data, dict):
            if data.get("demand_kwh") is None or data.get("base_solar_kwh") is None or data.get("tariff_bdt_per_kwh") is None:
                raise ValueError("Must provide either 'hours' (24 items) or 'demand_kwh', 'base_solar_kwh', 'tariff_bdt_per_kwh' (24 floats each)")
        return data

    @field_validator("demand_kwh", "base_solar_kwh", "tariff_bdt_per_kwh")
    @classmethod
    def validate_arrays(cls, values: list[float] | None) -> list[float] | None:
        if values is None:
            return None
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
    model_config = ConfigDict(extra="ignore")

    note_index: int = Field(ge=0, le=2)
    applies: bool = True
    directive_type: DirectiveType
    structured_adjustment: dict[str, Any] | None = None
    explanation: str | None = None


class DirectiveInterpretationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    interpretations: list[DirectiveInterpretation] = Field(min_length=1, max_length=3)


class HourSchedule(BaseModel):
    model_config = ConfigDict(extra="ignore")

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


class HourlyPlanItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    hour: int = Field(ge=0, le=23)
    grid_kwh: float = Field(ge=0)
    solar_used_kwh: float = Field(ge=0)
    battery_action: Literal["charge", "discharge", "idle"]
    battery_kwh: float = Field(ge=0)
    battery_energy_after_kwh: float = Field(ge=0)


class VerificationResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    verified: bool = Field(default=True)
    max_constraint_error: float = Field(ge=0, default=0.0)
    total_grid_cost_bdt: float = Field(ge=0)


class OptimizationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    scenario_id: str | None = None
    directive_interpretation: list[DirectiveInterpretation]
    hourly_plan: list[HourlyPlanItem] | None = None
    schedule: list[HourSchedule] = Field(min_length=HOURS, max_length=HOURS)
    total_grid_cost_bdt: float = Field(ge=0)
    total_cost_bdt: float | None = Field(default=None, ge=0)
    total_grid_kwh: float = Field(ge=0)
    peak_grid_kwh: float | None = Field(default=None, ge=0)
    plan_summary: str | None = None
    verification: VerificationResult
    status_message: str = Field(
        default="Optimal energy dispatch computed and verified via deterministic replay."
    )
