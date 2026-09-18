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


HourlyEnergyInput = ScenarioHour


class EnergyScenario(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "example": {
                "scenario_id": "SAMPLE-01",
                "operator_notes": [
                    "Facilities will wash the rooftop solar panels from noon until 2 PM. During cleaning, usable solar should be treated as roughly 25% of the forecast.",
                    "The sports office moved next month's registration deadline."
                ],
                "hours": [
                    {"hour": 0, "demand_kwh": 90, "solar_kwh": 0, "tariff_bdt_per_kwh": 6},
                    {"hour": 1, "demand_kwh": 85, "solar_kwh": 0, "tariff_bdt_per_kwh": 6},
                    {"hour": 2, "demand_kwh": 80, "solar_kwh": 0, "tariff_bdt_per_kwh": 5},
                    {"hour": 3, "demand_kwh": 80, "solar_kwh": 0, "tariff_bdt_per_kwh": 5},
                    {"hour": 4, "demand_kwh": 85, "solar_kwh": 0, "tariff_bdt_per_kwh": 5},
                    {"hour": 5, "demand_kwh": 95, "solar_kwh": 0, "tariff_bdt_per_kwh": 6},
                    {"hour": 6, "demand_kwh": 110, "solar_kwh": 5, "tariff_bdt_per_kwh": 8},
                    {"hour": 7, "demand_kwh": 130, "solar_kwh": 20, "tariff_bdt_per_kwh": 10},
                    {"hour": 8, "demand_kwh": 150, "solar_kwh": 50, "tariff_bdt_per_kwh": 12},
                    {"hour": 9, "demand_kwh": 165, "solar_kwh": 90, "tariff_bdt_per_kwh": 14},
                    {"hour": 10, "demand_kwh": 175, "solar_kwh": 130, "tariff_bdt_per_kwh": 16},
                    {"hour": 11, "demand_kwh": 180, "solar_kwh": 160, "tariff_bdt_per_kwh": 16},
                    {"hour": 12, "demand_kwh": 185, "solar_kwh": 180, "tariff_bdt_per_kwh": 15},
                    {"hour": 13, "demand_kwh": 180, "solar_kwh": 170, "tariff_bdt_per_kwh": 14},
                    {"hour": 14, "demand_kwh": 170, "solar_kwh": 140, "tariff_bdt_per_kwh": 13},
                    {"hour": 15, "demand_kwh": 165, "solar_kwh": 90, "tariff_bdt_per_kwh": 14},
                    {"hour": 16, "demand_kwh": 170, "solar_kwh": 45, "tariff_bdt_per_kwh": 18},
                    {"hour": 17, "demand_kwh": 185, "solar_kwh": 10, "tariff_bdt_per_kwh": 22},
                    {"hour": 18, "demand_kwh": 205, "solar_kwh": 0, "tariff_bdt_per_kwh": 28},
                    {"hour": 19, "demand_kwh": 215, "solar_kwh": 0, "tariff_bdt_per_kwh": 30},
                    {"hour": 20, "demand_kwh": 205, "solar_kwh": 0, "tariff_bdt_per_kwh": 26},
                    {"hour": 21, "demand_kwh": 175, "solar_kwh": 0, "tariff_bdt_per_kwh": 18},
                    {"hour": 22, "demand_kwh": 135, "solar_kwh": 0, "tariff_bdt_per_kwh": 10},
                    {"hour": 23, "demand_kwh": 105, "solar_kwh": 0, "tariff_bdt_per_kwh": 7}
                ],
                "battery": {
                    "capacity_kwh": 220,
                    "initial_energy_kwh": 110,
                    "minimum_energy_kwh": 40,
                    "max_charge_kwh_per_hour": 50,
                    "max_discharge_kwh_per_hour": 50
                }
            }
        }
    )

    scenario_id: str | None = Field(default="SCENARIO-01", description="Scenario identifier")
    hours: list[ScenarioHour] | None = Field(default=None, description="24 hourly entries")
    demand_kwh: list[float] | None = Field(
        default=None, description="24 hourly demand values in kWh"
    )
    base_solar_kwh: list[float] | None = Field(
        default=None, description="24 hourly baseline solar values in kWh"
    )
    tariff_bdt_per_kwh: list[float] | None = Field(
        default=None, description="24 hourly grid tariffs in BDT/kWh"
    )
    operator_notes: list[str] = Field(
        min_length=1, max_length=3, description="1 to 3 operator natural language notes"
    )
    battery: BatteryParameters

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

    @model_validator(mode="before")
    @classmethod
    def unpack_hours_if_present(cls, data: Any) -> Any:
        if isinstance(data, dict) and "hours" in data and data["hours"] is not None:
            raw_hours = data["hours"]
            if len(raw_hours) != HOURS:
                raise ValueError(f"hours must have exactly {HOURS} elements")
            sorted_hours = sorted(
                raw_hours,
                key=lambda x: x.get("hour", 0) if isinstance(x, dict) else getattr(x, "hour", 0),
            )
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
            if (
                data.get("demand_kwh") is None
                or data.get("base_solar_kwh") is None
                or data.get("tariff_bdt_per_kwh") is None
            ):
                raise ValueError(
                    "Must provide either 'hours' (24 items) or 'demand_kwh', 'base_solar_kwh', 'tariff_bdt_per_kwh' (24 floats each)"
                )
        return data

    @model_validator(mode="after")
    def validate_and_populate_arrays(self) -> EnergyScenario:
        if (
            self.demand_kwh is None
            or self.base_solar_kwh is None
            or self.tariff_bdt_per_kwh is None
        ):
            raise ValueError("Hourly demand, solar, and tariff arrays must be populated")
        if (
            len(self.demand_kwh) != HOURS
            or len(self.base_solar_kwh) != HOURS
            or len(self.tariff_bdt_per_kwh) != HOURS
        ):
            raise ValueError(f"Hourly arrays must each have exactly {HOURS} elements")
        self.demand_kwh = [_finite_nonnegative(v) for v in self.demand_kwh]
        self.base_solar_kwh = [_finite_nonnegative(v) for v in self.base_solar_kwh]
        self.tariff_bdt_per_kwh = [_finite_nonnegative(v) for v in self.tariff_bdt_per_kwh]

        if self.hours is None:
            self.hours = [
                ScenarioHour(
                    hour=i,
                    demand_kwh=self.demand_kwh[i],
                    solar_kwh=self.base_solar_kwh[i],
                    tariff_bdt_per_kwh=self.tariff_bdt_per_kwh[i],
                )
                for i in range(HOURS)
            ]
        return self


class DirectiveInterpretation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    note_index: int = Field(ge=0, le=2)
    applies: bool = True
    directive_type: DirectiveType
    structured_adjustment: dict[str, Any] | None = None
    explanation: str = Field(default="")


class HourlyPlanItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    hour: int = Field(ge=0, le=23)
    grid_kwh: float = Field(ge=0)
    solar_used_kwh: float = Field(ge=0)
    battery_action: Literal["charge", "discharge", "idle"]
    battery_kwh: float = Field(ge=0)
    battery_energy_after_kwh: float = Field(ge=0)


HourlyPlanEntry = HourlyPlanItem
DirectiveInterpretationResponse = DirectiveInterpretation


class HourlyScheduleOutput(BaseModel):
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


HourSchedule = HourlyScheduleOutput


class VerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verified: bool = True
    max_constraint_error: float = Field(ge=0)
    total_grid_cost_bdt: float = Field(ge=0)


class OptimizationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # Official Judge Top-Level Canonical Fields (Section 10)
    scenario_id: str | None = Field(default=None, description="Identifier of the scenario.")
    directive_interpretation: list[DirectiveInterpretation] = Field(
        ..., description="List of structured interpretations for each operator note."
    )
    hourly_plan: list[HourlyPlanItem] = Field(
        default_factory=list, description="24-hour canonical hourly dispatch plan."
    )
    total_grid_kwh: float = Field(..., description="Total grid energy purchased (kWh).")
    total_cost_bdt: float = Field(..., description="Total grid energy cost (BDT).")
    peak_grid_kwh: float = Field(default=0.0, description="Peak hourly grid energy purchase (kWh).")
    plan_summary: str = Field(
        default="", description="Human-readable summary of the dispatch schedule."
    )

    # Legacy / UI Dashboard Fields (preserved for backward compatibility with frontend)
    schedule: list[HourlyScheduleOutput] = Field(
        default_factory=list, description="Detailed hourly schedule for dashboard visualization."
    )
    total_grid_cost_bdt: float = Field(
        default=0.0, description="Alias for total_cost_bdt for UI compatibility."
    )
    verification: VerificationResult | None = Field(
        default=None, description="Deterministic replay verification summary."
    )
    status_message: str = Field(
        default="Optimization completed successfully.", description="Status message."
    )
