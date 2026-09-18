"""Domain models for energy dispatch optimization and validation.

These pure-Python typed representations are completely decoupled from any underlying
solver engine (such as PuLP or CBC). The API, database, repository, and orchestration
layers interact solely with these models.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

HOURS_IN_DAY: int = 24

DirectiveType = Literal[
    "solar_reduction",
    "minimum_battery_reserve",
    "no_charge_window",
    "no_discharge_window",
    "max_grid_window",
    "no_op",
]

SUPPORTED_DIRECTIVE_TYPES: frozenset[DirectiveType] = frozenset(
    [
        "solar_reduction",
        "minimum_battery_reserve",
        "no_charge_window",
        "no_discharge_window",
        "max_grid_window",
        "no_op",
    ]
)


class SolverStatus(StrEnum):
    """Standardized optimization solver execution status."""

    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    UNBOUNDED = "UNBOUNDED"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


# ─────────────────────────────────────────────────────────────────────────────
# 1. Hourly Energy Input
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class HourlyEnergyData:
    """Individual hour's energy snapshot and price signal."""

    hour: int
    demand_kwh: float
    base_solar_kwh: float
    tariff_bdt_per_kwh: float

    def __post_init__(self) -> None:
        if not (0 <= self.hour < HOURS_IN_DAY):
            raise ValueError(f"Hour must be in range [0, {HOURS_IN_DAY - 1}], got {self.hour}")
        for field_name, value in [
            ("demand_kwh", self.demand_kwh),
            ("base_solar_kwh", self.base_solar_kwh),
            ("tariff_bdt_per_kwh", self.tariff_bdt_per_kwh),
        ]:
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
            ):
                raise ValueError(f"{field_name} must be a finite number, got {value}")
            if value < 0.0:
                raise ValueError(f"{field_name} must be non-negative, got {value}")


@dataclass(frozen=True)
class HourlyEnergyProfile:
    """Complete 24-hour campus energy telemetry and tariff vectors."""

    demand_kwh: list[float]
    base_solar_kwh: list[float]
    tariff_bdt_per_kwh: list[float]

    def __post_init__(self) -> None:
        for name, arr in [
            ("demand_kwh", self.demand_kwh),
            ("base_solar_kwh", self.base_solar_kwh),
            ("tariff_bdt_per_kwh", self.tariff_bdt_per_kwh),
        ]:
            if len(arr) != HOURS_IN_DAY:
                raise ValueError(
                    f"{name} must contain exactly {HOURS_IN_DAY} values, got {len(arr)}"
                )
            for idx, val in enumerate(arr):
                if (
                    not isinstance(val, (int, float))
                    or isinstance(val, bool)
                    or not math.isfinite(val)
                ):
                    raise ValueError(f"{name} at hour {idx} is non-finite: {val}")
                if val < 0.0:
                    raise ValueError(f"{name} at hour {idx} is negative: {val}")

    def get_hour(self, hour: int) -> HourlyEnergyData:
        """Retrieve energy data for a specific hour."""
        return HourlyEnergyData(
            hour=hour,
            demand_kwh=float(self.demand_kwh[hour]),
            base_solar_kwh=float(self.base_solar_kwh[hour]),
            tariff_bdt_per_kwh=float(self.tariff_bdt_per_kwh[hour]),
        )

    def to_hourly_list(self) -> list[HourlyEnergyData]:
        """Convert vectors into a list of 24 hourly snapshots."""
        return [self.get_hour(h) for h in range(HOURS_IN_DAY)]


# ─────────────────────────────────────────────────────────────────────────────
# 2. Battery Configuration
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class BatteryConfig:
    """Technical specification and physical operating bounds for the battery storage."""

    capacity_kwh: float
    initial_energy_kwh: float
    minimum_energy_kwh: float
    max_charge_kwh_per_hour: float
    max_discharge_kwh_per_hour: float
    charge_efficiency: float = 1.0
    discharge_efficiency: float = 1.0

    def __post_init__(self) -> None:
        for field_name, value in [
            ("capacity_kwh", self.capacity_kwh),
            ("initial_energy_kwh", self.initial_energy_kwh),
            ("minimum_energy_kwh", self.minimum_energy_kwh),
            ("max_charge_kwh_per_hour", self.max_charge_kwh_per_hour),
            ("max_discharge_kwh_per_hour", self.max_discharge_kwh_per_hour),
            ("charge_efficiency", self.charge_efficiency),
            ("discharge_efficiency", self.discharge_efficiency),
        ]:
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
            ):
                raise ValueError(f"{field_name} must be a finite number, got {value}")

        if self.capacity_kwh <= 0.0:
            raise ValueError(f"capacity_kwh must be positive, got {self.capacity_kwh}")
        if self.initial_energy_kwh < 0.0:
            raise ValueError(
                f"initial_energy_kwh must be non-negative, got {self.initial_energy_kwh}"
            )
        if self.minimum_energy_kwh < 0.0:
            raise ValueError(
                f"minimum_energy_kwh must be non-negative, got {self.minimum_energy_kwh}"
            )
        if self.max_charge_kwh_per_hour < 0.0:
            raise ValueError(
                f"max_charge_kwh_per_hour must be non-negative, got {self.max_charge_kwh_per_hour}"
            )
        if self.max_discharge_kwh_per_hour < 0.0:
            raise ValueError(
                f"max_discharge_kwh_per_hour must be non-negative, got {self.max_discharge_kwh_per_hour}"
            )
        if not (0.0 < self.charge_efficiency <= 1.0):
            raise ValueError(
                f"charge_efficiency must be in (0.0, 1.0], got {self.charge_efficiency}"
            )
        if not (0.0 < self.discharge_efficiency <= 1.0):
            raise ValueError(
                f"discharge_efficiency must be in (0.0, 1.0], got {self.discharge_efficiency}"
            )

        # Boundary relationships
        if self.initial_energy_kwh > self.capacity_kwh:
            raise ValueError(
                f"initial_energy_kwh ({self.initial_energy_kwh}) cannot exceed capacity_kwh ({self.capacity_kwh})"
            )
        if self.minimum_energy_kwh > self.capacity_kwh:
            raise ValueError(
                f"minimum_energy_kwh ({self.minimum_energy_kwh}) cannot exceed capacity_kwh ({self.capacity_kwh})"
            )
        if self.initial_energy_kwh < self.minimum_energy_kwh:
            raise ValueError(
                f"initial_energy_kwh ({self.initial_energy_kwh}) cannot be below minimum_energy_kwh ({self.minimum_energy_kwh})"
            )

    @property
    def efficiency(self) -> float:
        """Round-trip battery efficiency."""
        return self.charge_efficiency * self.discharge_efficiency


# ─────────────────────────────────────────────────────────────────────────────
# 3. Normalized Directives
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class NormalizedDirective:
    """A validated, normalized operational directive parsed from operator instructions."""

    note_index: int
    directive_type: DirectiveType
    hours: list[int] = field(default_factory=list)
    factor: float | None = None  # for solar_reduction: remaining usable fraction in [0, 1]
    minimum_energy_kwh: float | None = None  # for minimum_battery_reserve
    max_grid_kwh: float | None = None  # for max_grid_window
    applies: bool = True

    def __post_init__(self) -> None:
        if self.directive_type not in SUPPORTED_DIRECTIVE_TYPES:
            raise ValueError(
                f"Unsupported directive_type '{self.directive_type}'. Must be one of {sorted(SUPPORTED_DIRECTIVE_TYPES)}"
            )

        if self.directive_type == "no_op":
            if self.applies:
                object.__setattr__(self, "applies", False)
            if self.hours:
                object.__setattr__(self, "hours", [])
            return

        if self.applies:
            if not self.hours:
                raise ValueError("Active directive must specify at least one target hour")
            if any(type(h) is not int for h in self.hours):
                raise ValueError(f"All directive hours must be integers, got {self.hours}")
            for h in self.hours:
                if not (0 <= h < HOURS_IN_DAY):
                    raise ValueError(f"Directive hour {h} out of bounds [0, {HOURS_IN_DAY - 1}]")
            if len(self.hours) != len(set(self.hours)):
                raise ValueError(
                    f"Directive hours must be unique, got duplicate hours in {self.hours}"
                )
            if self.hours != sorted(self.hours):
                raise ValueError(
                    f"Directive hours must be sorted in ascending order, got {self.hours}"
                )

            if self.directive_type == "solar_reduction" and (
                self.factor is None or not (0.0 <= self.factor <= 1.0)
            ):
                raise ValueError(
                    f"solar_reduction requires factor in [0.0, 1.0], got {self.factor}"
                )
            elif self.directive_type == "minimum_battery_reserve" and (
                self.minimum_energy_kwh is None or self.minimum_energy_kwh < 0.0
            ):
                raise ValueError(
                    f"minimum_battery_reserve requires non-negative minimum_energy_kwh, got {self.minimum_energy_kwh}"
                )
            elif self.directive_type == "max_grid_window" and (
                self.max_grid_kwh is None or self.max_grid_kwh < 0.0
            ):
                raise ValueError(
                    f"max_grid_window requires non-negative max_grid_kwh, got {self.max_grid_kwh}"
                )


@dataclass(frozen=True)
class CompiledDirectives:
    """Compiled 24-hour deterministic constraint vectors derived from normalized directives."""

    solar_factor: list[float]
    effective_solar: list[float]
    min_reserve: list[float]
    no_charge: list[bool]
    no_discharge: list[bool]
    max_grid: list[float | None]
    conflicts: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for name, arr in [
            ("solar_factor", self.solar_factor),
            ("effective_solar", self.effective_solar),
            ("min_reserve", self.min_reserve),
            ("no_charge", self.no_charge),
            ("no_discharge", self.no_discharge),
            ("max_grid", self.max_grid),
        ]:
            if len(arr) != HOURS_IN_DAY:
                raise ValueError(f"{name} must have length {HOURS_IN_DAY}, got {len(arr)}")

    def is_charge_allowed(self, hour: int) -> bool:
        """Return whether charging is permitted in the given hour."""
        return not self.no_charge[hour]

    def is_discharge_allowed(self, hour: int) -> bool:
        """Return whether discharging is permitted in the given hour."""
        return not self.no_discharge[hour]

    def has_battery_lock(self, hour: int) -> bool:
        """Return whether both charging and discharging are prohibited in the given hour."""
        return self.no_charge[hour] and self.no_discharge[hour]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "solar_factor": self.solar_factor,
            "effective_solar": self.effective_solar,
            "min_reserve": self.min_reserve,
            "no_charge": self.no_charge,
            "no_discharge": self.no_discharge,
            "max_grid": self.max_grid,
            "conflicts": self.conflicts,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 4. Optimization Input
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class OptimizationInput:
    """Input payload provided to the optimization solver.

    The optimizer receives ONLY clean, validated numerical parameters and compiled/normalized
    directives. It does not accept raw text notes and does not invoke LLMs.
    """

    energy_profile: HourlyEnergyProfile
    battery: BatteryConfig
    compiled_directives: CompiledDirectives

    @classmethod
    def from_arrays(
        cls,
        demand_kwh: list[float],
        base_solar_kwh: list[float],
        tariff_bdt_per_kwh: list[float],
        battery: BatteryConfig,
        compiled_directives: CompiledDirectives,
    ) -> OptimizationInput:
        """Factory constructor accepting flat lists directly."""
        profile = HourlyEnergyProfile(
            demand_kwh=demand_kwh,
            base_solar_kwh=base_solar_kwh,
            tariff_bdt_per_kwh=tariff_bdt_per_kwh,
        )
        return cls(
            energy_profile=profile,
            battery=battery,
            compiled_directives=compiled_directives,
        )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Schedule Output
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class HourlyScheduleOutput:
    """Individual hour dispatch result representing power flows and battery state."""

    hour: int
    grid_kwh: float
    solar_used_kwh: float
    battery_charge_kwh: float
    battery_discharge_kwh: float
    battery_energy_after_kwh: float

    # Optional context fields computed during dispatch
    demand_kwh: float | None = None
    effective_solar_kwh: float | None = None
    tariff_bdt_per_kwh: float | None = None
    grid_cost_bdt: float | None = None

    # Convenient accessors matching challenge specification aliases
    @property
    def grid(self) -> float:
        return self.grid_kwh

    @property
    def solar_used(self) -> float:
        return self.solar_used_kwh

    @property
    def battery_charge(self) -> float:
        return self.battery_charge_kwh

    @property
    def battery_discharge(self) -> float:
        return self.battery_discharge_kwh

    @property
    def battery_energy_after(self) -> float:
        return self.battery_energy_after_kwh


# ─────────────────────────────────────────────────────────────────────────────
# 6. Optimization Result
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class OptimizationResult:
    """Complete outcome of the 24-hour dispatch optimization.

    Provides all data required by the integration, repository, and presentation layers.
    """

    schedule: list[HourlyScheduleOutput]
    total_grid_kwh: float
    total_grid_cost_bdt: float
    objective_value: float
    solver_status: SolverStatus
    message: str = ""
    execution_time_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.solver_status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE):
            if len(self.schedule) != HOURS_IN_DAY:
                raise ValueError(
                    f"schedule must contain exactly {HOURS_IN_DAY} entries, got {len(self.schedule)}"
                )
        elif len(self.schedule) not in (0, HOURS_IN_DAY):
            raise ValueError(
                f"Failed schedule must be empty or contain {HOURS_IN_DAY} entries, got {len(self.schedule)}"
            )

    @property
    def is_optimal(self) -> bool:
        """Return True if solver found an optimal solution."""
        return self.solver_status == SolverStatus.OPTIMAL

    @property
    def is_feasible(self) -> bool:
        """Return True if solver found an optimal or feasible solution."""
        return self.solver_status in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE)

    @property
    def total_cost(self) -> float:
        """Alias for total_grid_cost_bdt."""
        return self.total_grid_cost_bdt

    @property
    def status(self) -> SolverStatus:
        """Alias for solver_status."""
        return self.solver_status


# ─────────────────────────────────────────────────────────────────────────────
# 7. Validation Result
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ReplayValidationResult:
    """Audit result from the independent deterministic replay physics simulator."""

    verified: bool
    max_constraint_error: float
    total_grid_cost_bdt: float
    violations: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        """Alias for verified."""
        return self.verified

    @property
    def errors(self) -> list[str]:
        """Alias for violations."""
        return self.violations

    @property
    def recalculated_total_cost(self) -> float:
        """Alias for total_grid_cost_bdt."""
        return self.total_grid_cost_bdt

    @property
    def max_violation_magnitude(self) -> float:
        """Alias for max_constraint_error."""
        return self.max_constraint_error
