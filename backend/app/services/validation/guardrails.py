from __future__ import annotations

import math
from typing import Any

from app.schemas.optimization import DirectiveInterpretation, EnergyScenario

SUPPORTED_DIRECTIVE_TYPES: set[str] = {
    "solar_reduction",
    "minimum_battery_reserve",
    "no_charge_window",
    "no_discharge_window",
    "max_grid_window",
    "no_op",
}


def _valid_hours(value: Any) -> bool:
    """Validate that value is a non-empty, strictly ascending list of unique integers in [0, 23]."""
    if not isinstance(value, list) or not value:
        return False
    if any(type(x) is not int for x in value):
        return False
    if any(x < 0 or x > 23 for x in value):
        return False
    return value == sorted(set(value)) and len(value) == len(set(value))


def _finite_number(value: Any) -> bool:
    """Validate that value is a finite number and not a boolean."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def noop(note_index: int) -> DirectiveInterpretation:
    """Construct a clean, non-applying no-op directive interpretation."""
    return DirectiveInterpretation(
        note_index=note_index,
        directive_type="no_op",
        structured_adjustment=None,
        applies=False,
    )


def validate_directives(
    scenario: EnergyScenario,
    raw_items: list[DirectiveInterpretation],
) -> list[DirectiveInterpretation]:
    """Deterministic trust boundary around untrusted LLM outputs.

    Ensures directive schemas, parameters, and physical boundary conditions
    are valid. Any malformed directive safely degrades to a no_op without
    aborting the optimization pipeline. If the index ordering or item count
    is broken, the entire set degrades to no_op.
    """
    n = len(scenario.operator_notes)

    if len(raw_items) != n:
        return [noop(i) for i in range(n)]

    indexes = [item.note_index for item in raw_items]
    if indexes != list(range(n)):
        return [noop(i) for i in range(n)]

    result: list[DirectiveInterpretation] = []

    for item in raw_items:
        if item.directive_type not in SUPPORTED_DIRECTIVE_TYPES or item.directive_type == "no_op":
            result.append(noop(item.note_index))
            continue

        adj = item.structured_adjustment
        if not isinstance(adj, dict):
            result.append(noop(item.note_index))
            continue

        hours = adj.get("hours")
        if not _valid_hours(hours):
            result.append(noop(item.note_index))
            continue

        # Enforce exact expected keys per directive type.
        # This prevents hidden or unexpected semantics from entering the optimization solver.
        expected_keys_map: dict[str, set[str]] = {
            "solar_reduction": {"hours", "factor"},
            "minimum_battery_reserve": {"hours", "minimum_energy_kwh"},
            "no_charge_window": {"hours"},
            "no_discharge_window": {"hours"},
            "max_grid_window": {"hours", "max_grid_kwh"},
        }

        expected = expected_keys_map.get(item.directive_type)
        if expected is None or set(adj.keys()) != expected:
            result.append(noop(item.note_index))
            continue

        if item.directive_type == "solar_reduction":
            factor = adj.get("factor")
            if not _finite_number(factor) or not (0.0 <= float(factor) <= 1.0):
                result.append(noop(item.note_index))
                continue
            normalized = {
                "hours": hours,
                "factor": float(factor),
            }

        elif item.directive_type == "minimum_battery_reserve":
            minimum = adj.get("minimum_energy_kwh")
            cap = scenario.battery.capacity_kwh
            if not _finite_number(minimum) or not (0.0 <= float(minimum) <= cap):
                result.append(noop(item.note_index))
                continue
            normalized = {
                "hours": hours,
                "minimum_energy_kwh": float(minimum),
            }

        elif item.directive_type == "max_grid_window":
            maximum = adj.get("max_grid_kwh")
            if not _finite_number(maximum) or float(maximum) < 0:
                result.append(noop(item.note_index))
                continue
            normalized = {
                "hours": hours,
                "max_grid_kwh": float(maximum),
            }

        else:
            # no_charge_window and no_discharge_window
            normalized = {"hours": hours}

        result.append(
            DirectiveInterpretation(
                note_index=item.note_index,
                directive_type=item.directive_type,
                structured_adjustment=normalized,
                applies=True,
            )
        )

    return result


# Backwards compatibility alias matching prototype archive
def validate_interpretation(
    raw_items: list[DirectiveInterpretation],
    scenario: EnergyScenario,
) -> list[DirectiveInterpretation]:
    """Backwards compatibility alias for validate_directives."""
    return validate_directives(scenario, raw_items)
