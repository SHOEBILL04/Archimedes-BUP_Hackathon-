"""Independent replay validator for optimizer output.

The validator exists to catch bugs in the optimizer, so it never asks the solver
whether it succeeded and never re-solves the LP. It recomputes every derived
quantity directly from the *original* scenario inputs and the normalized
directives, then compares those independent results against what the schedule
claims.

Trust boundary
--------------
Authoritative (from the original request):  demand, tariff, base solar, battery
parameters, normalized directives.

Untrusted (from the optimizer, re-derived here): effective solar, solar used,
charge, discharge, state of charge, grid, per-hour cost, reported totals.

Taking tariff or demand from the schedule instead of the request would let a
buggy optimizer define its own objective and validate against itself.
"""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.optimization import HOURS, EnergyScenario, HourSchedule

from .models import NormalizedDirectives
from .physics import (
    DEFAULT_CHARGE_EFFICIENCY,
    DEFAULT_DISCHARGE_EFFICIENCY,
    required_reserve_kwh,
)
from .solar import apply_solar_directives

#: Single documented numerical tolerance for every floating-point comparison.
#: CBC solutions routinely carry error around 1e-10..1e-12; 1e-6 kWh (one
#: milliwatt-hour) is far below any physically meaningful quantity here while
#: sitting comfortably above solver noise.
TOLERANCE = 1e-6

#: Units a check can be expressed in. Only ``kWh`` quantities are physical
#: constraint violations; monetary discrepancies are reported separately so the
#: two are never compared against each other or summarised into one number.
UNIT_ENERGY = "kWh"
UNIT_MONEY = "BDT"
UNIT_TARIFF = "BDT/kWh"


class ValidationIssue(BaseModel):
    """A single failed (or suspicious) check, addressed to a developer."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rule: str
    message: str
    hour: int | None = None
    actual: float | None = None
    expected: float | None = None
    unit: str = UNIT_ENERGY

    def __str__(self) -> str:  # pragma: no cover - convenience for logs
        where = f"hour {self.hour}" if self.hour is not None else "schedule"
        return f"[{self.rule}] {where}: {self.message}"


class ReplayValidationResult(BaseModel):
    """Outcome of replaying a schedule against the original inputs."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    valid: bool
    errors: tuple[ValidationIssue, ...] = Field(default=())
    warnings: tuple[ValidationIssue, ...] = Field(default=())
    #: Largest absolute PHYSICAL violation observed, in kWh, for the API layer's
    #: ``VerificationResult.max_constraint_error``. Monetary discrepancies are
    #: deliberately excluded: mixing kWh and BDT into one scalar would make the
    #: figure meaningless, since a cost error is an energy error times a tariff.
    max_constraint_error: float = Field(default=0.0, ge=0.0)
    #: Largest absolute monetary discrepancy observed, in BDT.
    max_cost_error_bdt: float = Field(default=0.0, ge=0.0)
    #: Independently recomputed totals; callers should prefer these.
    total_grid_kwh: float = Field(default=0.0)
    total_grid_cost_bdt: float = Field(default=0.0)


class _Collector:
    """Accumulates issues and tracks the largest violation per unit."""

    def __init__(self, tolerance: float) -> None:
        self.tolerance = tolerance
        self.errors: list[ValidationIssue] = []
        self.warnings: list[ValidationIssue] = []
        self.max_energy_error = 0.0
        self.max_cost_error = 0.0

    def _tolerance_for(self, unit: str, expected: float) -> float:
        """Absolute tolerance for energy; scaled tolerance for money.

        A cost is energy times a tariff, so its floating-point error scales with
        magnitude. Holding BDT to the same absolute 1e-6 as kWh would flag a
        perfectly sound schedule whenever the tariff is large, so monetary checks
        use ``tolerance * (1 + |expected|)`` -- the usual relative-plus-absolute
        form. Physical quantities keep the strict absolute bound.
        """
        if unit == UNIT_MONEY:
            return self.tolerance * (1.0 + abs(expected))
        return self.tolerance

    def error(
        self,
        rule: str,
        message: str,
        *,
        hour: int | None = None,
        actual: float | None = None,
        expected: float | None = None,
        magnitude: float | None = None,
        unit: str = UNIT_ENERGY,
    ) -> None:
        self.errors.append(
            ValidationIssue(
                rule=rule,
                message=message,
                hour=hour,
                actual=actual,
                expected=expected,
                unit=unit,
            )
        )
        if magnitude is None and actual is not None and expected is not None:
            magnitude = abs(actual - expected)
        if magnitude is None:
            return
        if unit == UNIT_ENERGY:
            self.max_energy_error = max(self.max_energy_error, abs(magnitude))
        elif unit == UNIT_MONEY:
            self.max_cost_error = max(self.max_cost_error, abs(magnitude))

    def warn(self, rule: str, message: str, *, hour: int | None = None) -> None:
        self.warnings.append(ValidationIssue(rule=rule, message=message, hour=hour))

    def check_close(
        self,
        rule: str,
        actual: float,
        expected: float,
        hour: int | None,
        message: str,
        *,
        unit: str = UNIT_ENERGY,
    ) -> None:
        if abs(actual - expected) > self._tolerance_for(unit, expected):
            self.error(rule, message, hour=hour, actual=actual, expected=expected, unit=unit)

    def check_max(
        self, rule: str, actual: float, bound: float, hour: int | None, message: str
    ) -> None:
        if actual > bound + self.tolerance:
            self.error(rule, message, hour=hour, actual=actual, expected=bound,
                       magnitude=actual - bound)

    def check_min(
        self, rule: str, actual: float, bound: float, hour: int | None, message: str
    ) -> None:
        if actual < bound - self.tolerance:
            self.error(rule, message, hour=hour, actual=actual, expected=bound,
                       magnitude=bound - actual)


def _validate_shape(schedule: Sequence[HourSchedule], collector: _Collector) -> bool:
    """Verify exactly 24 entries covering hours 0..23 once each, in order."""
    if len(schedule) != HOURS:
        collector.error(
            "schedule_length",
            f"schedule must contain exactly {HOURS} hourly entries, got {len(schedule)}",
            actual=float(len(schedule)),
            expected=float(HOURS),
        )
        return False

    hours = [row.hour for row in schedule]
    if len(set(hours)) != len(hours):
        collector.error("schedule_hours", f"schedule contains duplicate hours: {hours}")
        return False

    if hours != list(range(HOURS)):
        collector.error(
            "schedule_hours",
            f"hours must be 0..{HOURS - 1} in ascending order, got {hours}",
        )
        return False

    return True


def replay_validate(
    scenario: EnergyScenario,
    normalized: NormalizedDirectives,
    schedule: Sequence[HourSchedule],
    *,
    reported_total_cost_bdt: float | None = None,
    reported_total_grid_kwh: float | None = None,
    charge_efficiency: float = DEFAULT_CHARGE_EFFICIENCY,
    discharge_efficiency: float = DEFAULT_DISCHARGE_EFFICIENCY,
    tolerance: float = TOLERANCE,
) -> ReplayValidationResult:
    """Independently verify that a schedule is physically and financially valid.

    Performs only direct deterministic arithmetic: no solver, no database, no
    network.
    """
    collector = _Collector(tolerance)

    if not _validate_shape(schedule, collector):
        return ReplayValidationResult(
            valid=False,
            errors=tuple(collector.errors),
            warnings=tuple(collector.warnings),
            max_constraint_error=collector.max_energy_error,
            max_cost_error_bdt=collector.max_cost_error,
        )

    battery = scenario.battery
    # Independently derived from the ORIGINAL baseline, never read from the schedule.
    expected_effective_solar = apply_solar_directives(scenario.base_solar_kwh, normalized)

    replayed_energy = battery.initial_energy_kwh
    total_grid_kwh = 0.0
    total_grid_cost = 0.0

    for hour, row in enumerate(schedule):
        demand = scenario.demand_kwh[hour]
        tariff = scenario.tariff_bdt_per_kwh[hour]

        # ---- Input integrity ---------------------------------------------- #
        # The optimizer must not be able to restate the problem it was given.
        collector.check_close(
            "demand_integrity", row.demand_kwh, demand, hour,
            "schedule demand does not match the original request",
        )
        collector.check_close(
            "tariff_integrity", row.tariff_bdt_per_kwh, tariff, hour,
            "schedule tariff does not match the original request",
            unit=UNIT_TARIFF,
        )

        # ---- Non-negativity ------------------------------------------------ #
        for rule, value in (
            ("grid_non_negative", row.grid_kwh),
            ("solar_used_non_negative", row.solar_used_kwh),
            ("charge_non_negative", row.battery_charge_kwh),
            ("discharge_non_negative", row.battery_discharge_kwh),
        ):
            collector.check_min(rule, value, 0.0, hour, f"{rule} violated")

        # ---- Effective solar, recomputed ----------------------------------- #
        expected_solar = expected_effective_solar[hour]
        collector.check_close(
            "effective_solar", row.effective_solar_kwh, expected_solar, hour,
            "reported effective solar does not match base solar times directive factors",
        )
        # Bound solar usage by the INDEPENDENT figure, not the reported one.
        collector.check_max(
            "solar_availability", row.solar_used_kwh, expected_solar, hour,
            "solar used exceeds the solar actually available",
        )

        # ---- Energy balance, recomputed ------------------------------------ #
        supply = row.grid_kwh + row.solar_used_kwh + row.battery_discharge_kwh
        consumption = demand + row.battery_charge_kwh
        collector.check_close(
            "energy_balance", supply, consumption, hour,
            "grid + solar + discharge does not equal demand + charge",
        )

        # ---- Battery replayed from the initial state ----------------------- #
        replayed_energy = (
            replayed_energy
            + row.battery_charge_kwh * charge_efficiency
            - row.battery_discharge_kwh / discharge_efficiency
        )
        collector.check_close(
            "battery_state_replay", row.battery_energy_after_kwh, replayed_energy, hour,
            "reported state of charge does not match the replayed battery state",
        )

        collector.check_min(
            "battery_capacity", row.battery_energy_after_kwh, 0.0, hour,
            "battery energy is negative",
        )
        collector.check_max(
            "battery_capacity", row.battery_energy_after_kwh, battery.capacity_kwh, hour,
            "battery energy exceeds capacity",
        )
        collector.check_max(
            "charge_rate", row.battery_charge_kwh, battery.max_charge_kwh_per_hour, hour,
            "charge exceeds the maximum hourly charge rate",
        )
        collector.check_max(
            "discharge_rate", row.battery_discharge_kwh,
            battery.max_discharge_kwh_per_hour, hour,
            "discharge exceeds the maximum hourly discharge rate",
        )

        # ---- Directive constraints ----------------------------------------- #
        required_reserve = required_reserve_kwh(hour, battery, normalized)
        if required_reserve > 0.0:
            collector.check_min(
                "minimum_reserve", row.battery_energy_after_kwh, required_reserve, hour,
                "battery energy is below the required reserve",
            )

        if normalized.no_charge[hour]:
            collector.check_max(
                "no_charge", row.battery_charge_kwh, 0.0, hour,
                "charging occurred during a no-charge window",
            )

        if normalized.no_discharge[hour]:
            collector.check_max(
                "no_discharge", row.battery_discharge_kwh, 0.0, hour,
                "discharging occurred during a no-discharge window",
            )

        max_grid = normalized.max_grid[hour]
        if max_grid is not None:
            collector.check_max(
                "max_grid", row.grid_kwh, max_grid, hour,
                "grid import exceeds the directive maximum",
            )

        # ---- Per-hour cost, recomputed from the ORIGINAL tariff ------------- #
        expected_cost = row.grid_kwh * tariff
        collector.check_close(
            "hourly_cost", row.grid_cost_bdt, expected_cost, hour,
            "reported hourly cost does not equal grid times the original tariff",
            unit=UNIT_MONEY,
        )

        # Physically a battery cannot charge and discharge at once. At unit
        # efficiency it is energy- and cost-neutral rather than an exploit, so it
        # is reported as a warning rather than failing an otherwise sound schedule.
        if row.battery_charge_kwh > tolerance and row.battery_discharge_kwh > tolerance:
            collector.warn(
                "simultaneous_charge_discharge",
                "battery charges and discharges in the same hour",
                hour=hour,
            )

        total_grid_kwh += row.grid_kwh
        total_grid_cost += expected_cost

    # ---- End-of-day neutrality ------------------------------------------- #
    collector.check_close(
        "end_of_day_neutrality",
        schedule[HOURS - 1].battery_energy_after_kwh,
        battery.initial_energy_kwh,
        HOURS - 1,
        "battery does not finish the day at its initial energy",
    )

    # ---- Reported totals -------------------------------------------------- #
    if reported_total_cost_bdt is not None:
        collector.check_close(
            "total_cost", reported_total_cost_bdt, total_grid_cost, None,
            "reported total cost does not match the independently recomputed cost",
            unit=UNIT_MONEY,
        )
    if reported_total_grid_kwh is not None:
        collector.check_close(
            "total_grid_energy", reported_total_grid_kwh, total_grid_kwh, None,
            "reported total grid energy does not match the recomputed total",
        )

    return ReplayValidationResult(
        valid=not collector.errors,
        errors=tuple(collector.errors),
        warnings=tuple(collector.warnings),
        max_constraint_error=collector.max_energy_error,
        max_cost_error_bdt=collector.max_cost_error,
        total_grid_kwh=total_grid_kwh,
        total_grid_cost_bdt=total_grid_cost,
    )
