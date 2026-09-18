from __future__ import annotations

import math
from typing import Any

from models import DirectiveInterpretation, EnergyScenario


SUPPORTED = {
    "solar_reduction",
    "minimum_battery_reserve",
    "no_charge_window",
    "no_discharge_window",
    "max_grid_window",
    "no_op",
}


def _valid_hours(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    if any(type(x) is not int for x in value):
        return False
    if any(x < 0 or x > 23 for x in value):
        return False
    return value == sorted(set(value))


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def noop(note_index: int) -> DirectiveInterpretation:
    return DirectiveInterpretation(
        note_index=note_index,
        directive_type="no_op",
        structured_adjustment=None,
        applies=False,
    )


def validate_interpretation(
    raw_items: list[DirectiveInterpretation],
    scenario: EnergyScenario,
) -> list[DirectiveInterpretation]:
    """
    Deterministic trust boundary around the LLM.

    Any invalid item becomes no_op. If note indexes are duplicated/missing,
    the entire interpretation falls back to no_op because ordering is ambiguous.
    """
    n = len(scenario.operator_notes)

    if len(raw_items) != n:
        return [noop(i) for i in range(n)]

    indexes = [item.note_index for item in raw_items]
    if indexes != list(range(n)):
        return [noop(i) for i in range(n)]

    result: list[DirectiveInterpretation] = []

    for item in raw_items:
        if item.directive_type not in SUPPORTED:
            result.append(noop(item.note_index))
            continue

        if item.directive_type == "no_op":
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

        # Reject unknown keys. This prevents hidden semantics from crossing
        # the LLM -> deterministic optimization boundary.
        expected = {
            "solar_reduction": {"hours", "factor"},
            "minimum_battery_reserve": {"hours", "minimum_energy_kwh"},
            "no_charge_window": {"hours"},
            "no_discharge_window": {"hours"},
            "max_grid_window": {"hours", "max_grid_kwh"},
        }[item.directive_type]

        if set(adj.keys()) != expected:
            result.append(noop(item.note_index))
            continue

        if item.directive_type == "solar_reduction":
            factor = adj.get("factor")
            if not _finite_number(factor) or not 0.0 <= float(factor) <= 1.0:
                result.append(noop(item.note_index))
                continue
            normalized = {
                "hours": hours,
                "factor": float(factor),
            }

        elif item.directive_type == "minimum_battery_reserve":
            minimum = adj.get("minimum_energy_kwh")
            cap = scenario.battery.capacity_kwh
            if (
                not _finite_number(minimum)
                or not 0.0 <= float(minimum) <= cap
            ):
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


def compile_directives(
    interpretations: list[DirectiveInterpretation],
    scenario: EnergyScenario,
) -> dict[str, list | float]:
    """
    Converts validated directives into deterministic per-hour constraints.

    If multiple directives of the same type overlap:
      - solar reductions multiply their remaining-usable factors.
      - minimum reserves take the maximum.
      - no-charge/no-discharge windows take the union.
      - grid ceilings take the minimum.
    """
    solar_factor = [1.0] * 24
    min_reserve = [scenario.battery.minimum_energy_kwh] * 24
    no_charge = [False] * 24
    no_discharge = [False] * 24
    max_grid = [None] * 24

    for item in interpretations:
        if not item.applies or not item.structured_adjustment:
            continue

        adj = item.structured_adjustment
        hours = adj["hours"]

        if item.directive_type == "solar_reduction":
            factor = float(adj["factor"])
            for h in hours:
                solar_factor[h] *= factor

        elif item.directive_type == "minimum_battery_reserve":
            minimum = float(adj["minimum_energy_kwh"])
            for h in hours:
                min_reserve[h] = max(min_reserve[h], minimum)

        elif item.directive_type == "no_charge_window":
            for h in hours:
                no_charge[h] = True

        elif item.directive_type == "no_discharge_window":
            for h in hours:
                no_discharge[h] = True

        elif item.directive_type == "max_grid_window":
            maximum = float(adj["max_grid_kwh"])
            for h in hours:
                max_grid[h] = (
                    maximum if max_grid[h] is None
                    else min(max_grid[h], maximum)
                )

    effective_solar = [
        scenario.base_solar_kwh[h] * solar_factor[h]
        for h in range(24)
    ]

    return {
        "solar_factor": solar_factor,
        "effective_solar": effective_solar,
        "min_reserve": min_reserve,
        "no_charge": no_charge,
        "no_discharge": no_discharge,
        "max_grid": max_grid,
    }
