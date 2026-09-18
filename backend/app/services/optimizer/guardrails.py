"""Deterministic Guardrails for Operator Directive Interpretation.

This module acts as an untrusted boundary protecting the LP optimization engine
from hallucinated, malformed, or out-of-range directives produced by upstream LLMs.

Design Principles:
1. Pure Determinism: Zero external network or model calls.
2. Strict Schema & Range Checking: Unknown keys, negative/non-finite values,
   out-of-bounds hours, or impossible limits are caught immediately.
3. Safe Degradation: Invalid directives are gracefully downgraded to `no_op`
   with an audit warning rather than crashing the pipeline.
4. Deterministic Conflict Resolution: When multiple directives overlap in time,
   they are composed using well-defined mathematical rules.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

HOURS_IN_DAY: int = 24

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


@dataclass
class CompiledDirectives:
    """Deterministic hourly constraints compiled from validated directives."""

    solar_factor: list[float] = field(default_factory=lambda: [1.0] * HOURS_IN_DAY)
    effective_solar: list[float] = field(default_factory=lambda: [0.0] * HOURS_IN_DAY)
    min_reserve: list[float] = field(default_factory=lambda: [0.0] * HOURS_IN_DAY)
    no_charge: list[bool] = field(default_factory=lambda: [False] * HOURS_IN_DAY)
    no_discharge: list[bool] = field(default_factory=lambda: [False] * HOURS_IN_DAY)
    max_grid: list[float | None] = field(default_factory=lambda: [None] * HOURS_IN_DAY)


def _is_finite_number(value: Any) -> bool:
    """Verify that value is a finite number and strictly not a boolean."""
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


def _is_valid_hours(value: Any) -> bool:
    """Verify that value is a non-empty, unique, ascending list of integers between 0 and 23."""
    if not isinstance(value, list) or not value:
        return False
    if any(type(x) is not int for x in value):
        return False
    if any(x < 0 or x >= HOURS_IN_DAY for x in value):
        return False
    # Must be sorted ascending without duplicates
    return value == sorted(set(value))


def noop(note_index: int, explanation: str | None = None) -> dict[str, Any]:
    """Create a safe fallback no_op directive interpretation."""
    return {
        "note_index": note_index,
        "directive_type": "no_op",
        "structured_adjustment": None,
        "applies": False,
        "explanation": explanation
        or "This note does not affect the current 24-hour energy schedule.",
    }


def validate_interpretations(
    raw_items: list[dict[str, Any]],
    note_count: int,
    battery_capacity: float,
) -> list[dict[str, Any]]:
    """Validate LLM-generated directive interpretations against strict physical and schema boundaries.

    Any structurally or semantically invalid directive is safely downgraded to `no_op`.
    If the collection itself is inconsistent (wrong count, missing/duplicate indexes),
    all items are degraded to `no_op`.

    Args:
        raw_items: Raw list of directive dicts returned by the LLM.
        note_count: Expected number of operator notes (1-3).
        battery_capacity: Maximum energy storage capacity of the battery in kWh.

    Returns:
        A list of validated directive dicts in sequential note_index order (0..note_count-1).
    """
    if len(raw_items) != note_count:
        logger.warning(
            "Guardrail rejection: raw interpretations count (%d) does not match expected note count (%d).",
            len(raw_items),
            note_count,
        )
        return [noop(i) for i in range(note_count)]

    # Attempt to sort by note_index to handle possible out-of-order returns
    try:
        sorted_items = sorted(raw_items, key=lambda item: int(item.get("note_index", -1)))
    except (TypeError, ValueError):
        logger.warning("Guardrail rejection: non-integer note_index encountered in raw items.")
        return [noop(i) for i in range(note_count)]

    indexes = [item.get("note_index") for item in sorted_items]
    if indexes != list(range(note_count)):
        logger.warning(
            "Guardrail rejection: note_index sequence %s is invalid or incomplete (expected %s).",
            indexes,
            list(range(note_count)),
        )
        return [noop(i) for i in range(note_count)]

    validated_results: list[dict[str, Any]] = []

    for item in sorted_items:
        note_idx = int(item["note_index"])
        explanation = item.get("explanation")
        directive_type = item.get("directive_type")

        if directive_type not in SUPPORTED_DIRECTIVE_TYPES:
            logger.warning(
                "Guardrail rejection [note %d]: unsupported directive_type '%s'.",
                note_idx,
                directive_type,
            )
            validated_results.append(noop(note_idx))
            continue

        if directive_type == "no_op":
            validated_results.append(noop(note_idx, explanation=explanation))
            continue

        adj = item.get("structured_adjustment")
        if not isinstance(adj, dict):
            logger.warning(
                "Guardrail rejection [note %d]: structured_adjustment is not a dict for '%s'.",
                note_idx,
                directive_type,
            )
            validated_results.append(noop(note_idx))
            continue

        hours = adj.get("hours")
        if not _is_valid_hours(hours):
            logger.warning(
                "Guardrail rejection [note %d]: invalid hours %s for '%s'.",
                note_idx,
                hours,
                directive_type,
            )
            validated_results.append(noop(note_idx))
            continue

        # Reject unknown keys to eliminate hallucinated semantic side-effects
        expected_keys_map = {
            "solar_reduction": {"hours", "factor"},
            "minimum_battery_reserve": {"hours", "minimum_energy_kwh"},
            "no_charge_window": {"hours"},
            "no_discharge_window": {"hours"},
            "max_grid_window": {"hours", "max_grid_kwh"},
        }
        expected_keys = expected_keys_map[directive_type]
        actual_keys = set(adj.keys())

        if actual_keys != expected_keys:
            logger.warning(
                "Guardrail rejection [note %d]: keys %s do not match expected keys %s for '%s'.",
                note_idx,
                actual_keys,
                expected_keys,
                directive_type,
            )
            validated_results.append(noop(note_idx))
            continue

        # Specific numerical boundary checks
        if directive_type == "solar_reduction":
            factor = adj.get("factor")
            if not _is_finite_number(factor) or not (0.0 <= float(factor) <= 1.0):
                logger.warning(
                    "Guardrail rejection [note %d]: solar_reduction factor %s out of [0.0, 1.0].",
                    note_idx,
                    factor,
                )
                validated_results.append(noop(note_idx))
                continue
            normalized_adj: dict[str, Any] = {
                "hours": hours,
                "factor": float(factor),
            }

        elif directive_type == "minimum_battery_reserve":
            minimum_energy = adj.get("minimum_energy_kwh")
            if not _is_finite_number(minimum_energy) or not (
                0.0 <= float(minimum_energy) <= battery_capacity
            ):
                logger.warning(
                    "Guardrail rejection [note %d]: minimum_battery_reserve %s out of [0.0, capacity=%.2f].",
                    note_idx,
                    minimum_energy,
                    battery_capacity,
                )
                validated_results.append(noop(note_idx))
                continue
            normalized_adj = {
                "hours": hours,
                "minimum_energy_kwh": float(minimum_energy),
            }

        elif directive_type == "max_grid_window":
            max_grid = adj.get("max_grid_kwh")
            if not _is_finite_number(max_grid) or float(max_grid) < 0.0:
                logger.warning(
                    "Guardrail rejection [note %d]: max_grid_kwh %s is negative or non-finite.",
                    note_idx,
                    max_grid,
                )
                validated_results.append(noop(note_idx))
                continue
            normalized_adj = {
                "hours": hours,
                "max_grid_kwh": float(max_grid),
            }

        else:
            # no_charge_window or no_discharge_window
            normalized_adj = {"hours": hours}

        validated_results.append(
            {
                "note_index": note_idx,
                "directive_type": directive_type,
                "structured_adjustment": normalized_adj,
                "applies": True,
                "explanation": explanation or f"Applied {directive_type} directive.",
            }
        )

    return validated_results


def compile_directives(
    interpretations: list[dict[str, Any]],
    base_solar: list[float],
    battery_capacity: float,
    battery_min_energy: float,
) -> CompiledDirectives:
    """Compile validated directives into deterministic per-hour optimization constraints.

    Deterministic Conflict Resolution Rules:
    - solar_reduction: Multiply remaining usable factors across overlapping windows.
    - minimum_battery_reserve: Maximum reserve wins across overlapping windows.
    - no_charge_window: Union of hours (any active no-charge window disables charging).
    - no_discharge_window: Union of hours (any active no-discharge window disables discharging).
    - max_grid_window: Minimum grid ceiling wins across overlapping windows.

    Args:
        interpretations: Validated directive dicts.
        base_solar: 24 hourly base solar forecast values in kWh.
        battery_capacity: Total battery capacity in kWh.
        battery_min_energy: Baseline minimum battery reserve in kWh.

    Returns:
        CompiledDirectives dataclass with 24-hour resolved constraint arrays.
    """
    solar_factor = [1.0] * HOURS_IN_DAY
    min_reserve = [float(battery_min_energy)] * HOURS_IN_DAY
    no_charge = [False] * HOURS_IN_DAY
    no_discharge = [False] * HOURS_IN_DAY
    max_grid: list[float | None] = [None] * HOURS_IN_DAY

    for item in interpretations:
        if not item.get("applies", False):
            continue

        adj = item.get("structured_adjustment")
        if not isinstance(adj, dict):
            continue

        hours: list[int] = adj.get("hours", [])
        dtype = item.get("directive_type")

        if dtype == "solar_reduction":
            factor = float(adj["factor"])
            for h in hours:
                solar_factor[h] *= factor

        elif dtype == "minimum_battery_reserve":
            reserve = float(adj["minimum_energy_kwh"])
            for h in hours:
                min_reserve[h] = max(min_reserve[h], reserve)

        elif dtype == "no_charge_window":
            for h in hours:
                no_charge[h] = True

        elif dtype == "no_discharge_window":
            for h in hours:
                no_discharge[h] = True

        elif dtype == "max_grid_window":
            grid_cap = float(adj["max_grid_kwh"])
            for h in hours:
                max_grid[h] = grid_cap if max_grid[h] is None else min(max_grid[h], grid_cap)

    effective_solar = [base_solar[h] * solar_factor[h] for h in range(HOURS_IN_DAY)]

    return CompiledDirectives(
        solar_factor=solar_factor,
        effective_solar=effective_solar,
        min_reserve=min_reserve,
        no_charge=no_charge,
        no_discharge=no_discharge,
        max_grid=max_grid,
    )
