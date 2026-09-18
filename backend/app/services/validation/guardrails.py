"""Deterministic guardrails converting untrusted LLM directives into safe constraints.

The LLM is untrusted input. Structurally valid JSON does not imply a semantically
valid directive, so every field is re-checked here against the physical scenario
before anything reaches the optimizer.

Failure policy: a directive that violates any rule is *rejected and recorded*,
never coerced into something else and never silently reinterpreted as a different
directive type. One malformed directive therefore cannot fail an entire request,
and it also cannot leak an unchecked constraint into the LP.

Expected ``structured_adjustment`` payload per directive type::

    solar_reduction          {"hours": [int, ...], "factor": float}
    minimum_battery_reserve  {"hours": [int, ...], "minimum_energy_kwh": float}
    no_charge_window         {"hours": [int, ...]}
    no_discharge_window      {"hours": [int, ...]}
    max_grid_window          {"hours": [int, ...], "max_grid_kwh": float}
    no_op                    null
"""

from __future__ import annotations

import math
from typing import Any

from app.core.logging import logger
from app.schemas.optimization import (
    HOURS,
    BatteryParameters,
    DirectiveInterpretation,
    EnergyScenario,
)

from .models import DirectiveRejection, GuardrailReport, NormalizedDirectives

#: Directive types the optimizer understands. Anything else must not reach it.
SUPPORTED_DIRECTIVE_TYPES: frozenset[str] = frozenset(
    {
        "solar_reduction",
        "minimum_battery_reserve",
        "no_charge_window",
        "no_discharge_window",
        "max_grid_window",
        "no_op",
    }
)


class _Reject(Exception):
    """Internal control-flow signal carrying a human-readable rejection reason."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _require_payload(directive: DirectiveInterpretation) -> dict[str, Any]:
    payload = directive.structured_adjustment
    if payload is None:
        raise _Reject("structured_adjustment is required but was null")
    if not isinstance(payload, dict):
        raise _Reject("structured_adjustment must be a JSON object")
    return payload


def _require_number(payload: dict[str, Any], key: str) -> float:
    if key not in payload:
        raise _Reject(f"missing required field {key!r}")
    value = payload[key]
    # bool is a subclass of int in Python; a boolean here means the LLM emitted
    # the wrong type, so reject rather than silently reading True as 1.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _Reject(f"field {key!r} must be a number, got {type(value).__name__}")
    number = float(value)
    if not math.isfinite(number):
        raise _Reject(f"field {key!r} must be finite, got {value!r}")
    return number


def _parse_hours(payload: dict[str, Any]) -> tuple[int, ...]:
    """Validate the hours list: integers in 0..23, unique and strictly ascending."""
    if "hours" not in payload:
        raise _Reject("missing required field 'hours'")

    raw = payload["hours"]
    if not isinstance(raw, (list, tuple)):
        raise _Reject("field 'hours' must be a list")
    if len(raw) == 0:
        raise _Reject("field 'hours' must not be empty")

    hours: list[int] = []
    for item in raw:
        if isinstance(item, bool):
            raise _Reject("hours must be integers, got a boolean")
        if isinstance(item, int):
            hour = item
        elif isinstance(item, float) and item.is_integer():
            # Tolerate integral floats (5.0) which some JSON encoders emit,
            # but never a fractional hour.
            hour = int(item)
        else:
            raise _Reject(f"hours must be integers, got {item!r}")
        if not 0 <= hour <= HOURS - 1:
            raise _Reject(f"hour {hour} out of range 0..{HOURS - 1}")
        hours.append(hour)

    if len(set(hours)) != len(hours):
        raise _Reject(f"hours must be unique, got {hours}")
    if any(hours[i] >= hours[i + 1] for i in range(len(hours) - 1)):
        raise _Reject(f"hours must be in ascending order, got {hours}")

    return tuple(hours)


def _apply_solar_reduction(
    payload: dict[str, Any], hours: tuple[int, ...], solar_factors: list[float]
) -> None:
    """The factor is the fraction of solar that REMAINS usable (80% reduction -> 0.2)."""
    factor = _require_number(payload, "factor")
    if not 0.0 <= factor <= 1.0:
        raise _Reject(f"factor must be within [0, 1], got {factor}")

    # Overlapping reductions compound multiplicatively: two directives of 0.5 and
    # 0.4 on the same hour leave 0.2 of baseline solar, not 0.5 or 0.4 alone.
    for hour in hours:
        solar_factors[hour] *= factor


def _apply_minimum_reserve(
    payload: dict[str, Any],
    hours: tuple[int, ...],
    battery: BatteryParameters,
    minimum_reserve: list[float],
) -> None:
    reserve = _require_number(payload, "minimum_energy_kwh")
    if reserve < 0:
        raise _Reject(f"minimum_energy_kwh must be >= 0, got {reserve}")
    if reserve > battery.capacity_kwh:
        raise _Reject(
            f"minimum_energy_kwh {reserve} exceeds battery capacity {battery.capacity_kwh}"
        )

    # The strictest reserve wins when directives overlap.
    for hour in hours:
        minimum_reserve[hour] = max(minimum_reserve[hour], reserve)


def _apply_max_grid(
    payload: dict[str, Any], hours: tuple[int, ...], max_grid: list[float | None]
) -> None:
    limit = _require_number(payload, "max_grid_kwh")
    if limit < 0:
        raise _Reject(f"max_grid_kwh must be >= 0, got {limit}")

    # The tightest cap wins when directives overlap.
    for hour in hours:
        current = max_grid[hour]
        max_grid[hour] = limit if current is None else min(current, limit)


def normalize_directives(
    scenario: EnergyScenario,
    directives: list[DirectiveInterpretation],
) -> GuardrailReport:
    """Normalize interpreted directives into per-hour constraint arrays.

    Deterministic: the same inputs always yield an identical report. Directives
    are applied in note_index order, and every combination rule (product for
    solar, max for reserve, min for grid, union for windows) is order-independent
    anyway.

    The scenario's physical inputs -- demand, tariff, base solar, battery
    capacity and initial energy -- are only ever read, never modified.
    """
    solar_factors = [1.0] * HOURS
    minimum_reserve = [0.0] * HOURS
    no_charge = [False] * HOURS
    no_discharge = [False] * HOURS
    max_grid: list[float | None] = [None] * HOURS

    accepted: list[int] = []
    rejections: list[DirectiveRejection] = []

    for directive in sorted(directives, key=lambda d: d.note_index):
        directive_type = directive.directive_type

        try:
            if directive_type not in SUPPORTED_DIRECTIVE_TYPES:
                raise _Reject(f"unsupported directive type {directive_type!r}")

            # no_op carries no constraint by definition, and neither does any
            # directive the interpreter explicitly marked as not applying.
            if directive_type == "no_op" or not directive.applies:
                accepted.append(directive.note_index)
                continue

            payload = _require_payload(directive)
            hours = _parse_hours(payload)

            if directive_type == "solar_reduction":
                _apply_solar_reduction(payload, hours, solar_factors)
            elif directive_type == "minimum_battery_reserve":
                _apply_minimum_reserve(payload, hours, scenario.battery, minimum_reserve)
            elif directive_type == "max_grid_window":
                _apply_max_grid(payload, hours, max_grid)
            elif directive_type == "no_charge_window":
                # Overlapping windows union together.
                for hour in hours:
                    no_charge[hour] = True
            elif directive_type == "no_discharge_window":
                for hour in hours:
                    no_discharge[hour] = True

            accepted.append(directive.note_index)

        except _Reject as rejection:
            logger.warning(
                "Rejected directive %d (%s): %s",
                directive.note_index,
                directive_type,
                rejection.reason,
            )
            rejections.append(
                DirectiveRejection(
                    note_index=directive.note_index,
                    directive_type=str(directive_type),
                    reason=rejection.reason,
                )
            )

    return GuardrailReport(
        normalized=NormalizedDirectives(
            solar_factors=tuple(solar_factors),
            minimum_reserve=tuple(minimum_reserve),
            no_charge=tuple(no_charge),
            no_discharge=tuple(no_discharge),
            max_grid=tuple(max_grid),
        ),
        accepted=tuple(accepted),
        rejections=tuple(rejections),
    )
