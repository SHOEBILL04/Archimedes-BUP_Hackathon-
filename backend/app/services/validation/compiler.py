"""Deterministic directive preprocessing and constraint compiler.

Converts validated directives into deterministic 24-hour mathematical constraint
arrays consumable directly by the LP optimization solver.

Resolution Rules:
1. Effective Solar:
   effective_solar[h] = base_solar[h] * factor1 * factor2 * ...
   Multiplicative chaining across overlapping windows (never additive).
2. No-Charge Windows:
   battery_charge[h] = 0 (boolean union across all active windows).
3. No-Discharge Windows:
   battery_discharge[h] = 0 (boolean union across all active windows).
4. Minimum Reserve:
   battery_energy_after[h] >= required_reserve (highest reserve wins).
5. Max Grid:
   grid[h] <= max_grid_kwh (smallest maximum ceiling wins).
6. Conflicts:
   Physically impossible combinations are NEVER silently resolved or dropped.
   All mathematical constraints are preserved in full so the optimizer can
   formulate the exact problem and determine feasibility.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.services.optimizer.models import (
    HOURS_IN_DAY,
    BatteryConfig,
    CompiledDirectives,
    NormalizedDirective,
)
from app.services.validation.interface import IDirectiveCompiler


def _extract_directive_data(
    item: Any,
) -> tuple[str | None, list[int], float | None, float | None, float | None, bool]:
    """Extract (directive_type, hours, factor, reserve, max_grid, applies) from any supported representation."""
    if isinstance(item, NormalizedDirective):
        return (
            item.directive_type,
            item.hours,
            item.factor,
            item.minimum_energy_kwh,
            item.max_grid_kwh,
            item.applies,
        )

    if isinstance(item, dict):
        applies = item.get("applies", True)
        dtype = item.get("directive_type")
        adj = item.get("structured_adjustment")
        if isinstance(adj, dict):
            hours = adj.get("hours", item.get("hours", []))
            factor = adj.get("factor", item.get("factor"))
            reserve = adj.get(
                "minimum_energy_kwh", item.get("minimum_energy_kwh", item.get("reserve"))
            )
            max_grid = adj.get("max_grid_kwh", item.get("max_grid_kwh", item.get("max_grid")))
        else:
            hours = item.get("hours", [])
            factor = item.get("factor")
            reserve = item.get("minimum_energy_kwh", item.get("reserve"))
            max_grid = item.get("max_grid_kwh", item.get("max_grid"))
        return dtype, hours, factor, reserve, max_grid, applies

    # Object with attributes (e.g. DirectiveInterpretation)
    applies = getattr(item, "applies", True)
    dtype = getattr(item, "directive_type", None)
    adj = getattr(item, "structured_adjustment", None)
    if isinstance(adj, dict):
        hours = adj.get("hours", getattr(item, "hours", []))
        factor = adj.get("factor", getattr(item, "factor", None))
        reserve = adj.get(
            "minimum_energy_kwh",
            getattr(item, "minimum_energy_kwh", getattr(item, "reserve", None)),
        )
        max_grid = adj.get(
            "max_grid_kwh",
            getattr(item, "max_grid_kwh", getattr(item, "max_grid", None)),
        )
    else:
        hours = getattr(item, "hours", [])
        factor = getattr(item, "factor", None)
        reserve = getattr(item, "minimum_energy_kwh", getattr(item, "reserve", None))
        max_grid = getattr(item, "max_grid_kwh", getattr(item, "max_grid", None))

    return dtype, hours, factor, reserve, max_grid, applies


def preprocess_directives(
    directives: Sequence[Any],
    base_solar: Sequence[float],
    battery_min_energy: float = 0.0,
    battery_capacity: float | None = None,
) -> CompiledDirectives:
    """Preprocess validated directives into deterministic 24-hour constraint vectors.

    Args:
        directives: Sequence of NormalizedDirective, DirectiveInterpretation, or raw dicts.
        base_solar: 24-element sequence of base solar generation values in kWh.
        battery_min_energy: Baseline minimum battery reserve in kWh (default 0.0).
        battery_capacity: Optional battery capacity in kWh for boundary context.

    Returns:
        CompiledDirectives containing 24-hour deterministic constraint vectors and conflict diagnostics.
    """
    if len(base_solar) != HOURS_IN_DAY:
        raise ValueError(f"base_solar must have length {HOURS_IN_DAY}, got {len(base_solar)}")

    solar_factor = [1.0] * HOURS_IN_DAY
    min_reserve = [float(battery_min_energy)] * HOURS_IN_DAY
    no_charge = [False] * HOURS_IN_DAY
    no_discharge = [False] * HOURS_IN_DAY
    max_grid: list[float | None] = [None] * HOURS_IN_DAY

    for item in directives:
        dtype, hours, factor, reserve, max_grid_cap, applies = _extract_directive_data(item)

        if not applies or dtype == "no_op" or not dtype:
            continue

        if dtype == "solar_reduction" and factor is not None:
            f_val = float(factor)
            for h in hours:
                if 0 <= h < HOURS_IN_DAY:
                    solar_factor[h] *= f_val

        elif dtype == "minimum_battery_reserve" and reserve is not None:
            r_val = float(reserve)
            for h in hours:
                if 0 <= h < HOURS_IN_DAY:
                    min_reserve[h] = max(min_reserve[h], r_val)

        elif dtype == "no_charge_window":
            for h in hours:
                if 0 <= h < HOURS_IN_DAY:
                    no_charge[h] = True

        elif dtype == "no_discharge_window":
            for h in hours:
                if 0 <= h < HOURS_IN_DAY:
                    no_discharge[h] = True

        elif dtype == "max_grid_window" and max_grid_cap is not None:
            g_val = float(max_grid_cap)
            for h in hours:
                if 0 <= h < HOURS_IN_DAY:
                    current = max_grid[h]
                    max_grid[h] = g_val if current is None else min(current, g_val)

    effective_solar = [float(base_solar[h]) * solar_factor[h] for h in range(HOURS_IN_DAY)]

    # Preserve conflict diagnostics without modifying or relaxing mathematical constraints
    conflicts: list[str] = []
    for h in range(HOURS_IN_DAY):
        if no_charge[h] and no_discharge[h]:
            conflicts.append(
                f"Hour {h}: Both no_charge and no_discharge active (battery locked to 0 kW)."
            )
        if (
            max_grid[h] is not None
            and max_grid[h] == 0.0
            and effective_solar[h] == 0.0
            and no_discharge[h]
        ):
            conflicts.append(
                f"Hour {h}: Severe supply constraint: grid import capped at 0.0 kWh, "
                f"effective solar is 0.0 kWh, and battery discharge is prohibited."
            )
        if min_reserve[h] > battery_min_energy and no_charge[h]:
            conflicts.append(
                f"Hour {h}: Elevated reserve ({min_reserve[h]:.2f} kWh) required while "
                f"battery charging is prohibited (no_charge=True)."
            )

    return CompiledDirectives(
        solar_factor=solar_factor,
        effective_solar=effective_solar,
        min_reserve=min_reserve,
        no_charge=no_charge,
        no_discharge=no_discharge,
        max_grid=max_grid,
        conflicts=conflicts,
    )


def compile_directives(*args: Any, **kwargs: Any) -> CompiledDirectives:
    """Universal entrypoint compiling directives into deterministic per-hour constraints.

    Supported calling signatures:
    1. compile_directives(scenario: EnergyScenario, interpretations: list[DirectiveInterpretation])
    2. compile_directives(directives: list[NormalizedDirective], base_solar: list[float], battery: BatteryConfig | float)
    3. compile_directives(directives, base_solar, battery_capacity, battery_min_reserve)
    """
    if len(args) >= 1 and hasattr(args[0], "base_solar_kwh"):
        # Signature 1: scenario as first argument
        scenario = args[0]
        interpretations = args[1] if len(args) > 1 else kwargs.get("interpretations", [])
        base_solar = [float(x) for x in scenario.base_solar_kwh]
        battery_min = float(scenario.battery.minimum_energy_kwh)
        battery_cap = float(scenario.battery.capacity_kwh)
        return preprocess_directives(
            directives=interpretations,
            base_solar=base_solar,
            battery_min_energy=battery_min,
            battery_capacity=battery_cap,
        )

    # Signature 2 or 3: directives as first argument
    directives = args[0] if len(args) > 0 else kwargs.get("directives", [])
    base_solar = args[1] if len(args) > 1 else kwargs.get("base_solar", [0.0] * HOURS_IN_DAY)

    battery_min_energy = 0.0
    battery_capacity: float | None = None

    if len(args) == 4:
        # Signature 3: (directives, base_solar, battery_capacity, battery_min_energy)
        battery_capacity = float(args[2])
        battery_min_energy = float(args[3])
    elif len(args) >= 3:
        battery_arg = args[2]
        if isinstance(battery_arg, BatteryConfig):
            battery_min_energy = float(battery_arg.minimum_energy_kwh)
            battery_capacity = float(battery_arg.capacity_kwh)
        elif hasattr(battery_arg, "minimum_energy_kwh"):
            battery_min_energy = float(battery_arg.minimum_energy_kwh)
            if hasattr(battery_arg, "capacity_kwh"):
                battery_capacity = float(battery_arg.capacity_kwh)
        elif isinstance(battery_arg, (int, float)):
            battery_min_energy = float(battery_arg)
    else:
        battery_arg = kwargs.get("battery")
        if isinstance(battery_arg, BatteryConfig):
            battery_min_energy = float(battery_arg.minimum_energy_kwh)
            battery_capacity = float(battery_arg.capacity_kwh)
        elif isinstance(battery_arg, (int, float)):
            battery_min_energy = float(battery_arg)
        elif "battery_min_energy" in kwargs:
            battery_min_energy = float(kwargs["battery_min_energy"])

    return preprocess_directives(
        directives=directives,
        base_solar=base_solar,
        battery_min_energy=battery_min_energy,
        battery_capacity=battery_capacity,
    )


class DeterministicDirectiveCompiler(IDirectiveCompiler):
    """Concrete implementation of IDirectiveCompiler protocol."""

    def compile(
        self,
        directives: list[NormalizedDirective],
        base_solar: list[float],
        battery: BatteryConfig,
    ) -> CompiledDirectives:
        """Compile normalized directives into deterministic hourly constraint vectors."""
        return preprocess_directives(
            directives=directives,
            base_solar=base_solar,
            battery_min_energy=battery.minimum_energy_kwh,
            battery_capacity=battery.capacity_kwh,
        )
