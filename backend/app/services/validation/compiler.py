from __future__ import annotations

from app.schemas.optimization import DirectiveInterpretation, EnergyScenario
from app.services.validation.models import CompiledDirectives


def compile_directives(
    scenario: EnergyScenario,
    interpretations: list[DirectiveInterpretation],
) -> CompiledDirectives:
    """Converts validated directives into deterministic per-hour constraints.

    Resolution of overlapping directives:
      - solar reductions multiply their remaining-usable factors.
      - minimum reserves take the maximum value required.
      - no-charge/no-discharge windows take the boolean union.
      - grid ceilings take the minimum allowable power.
    """
    solar_factor = [1.0] * 24
    min_reserve = [float(scenario.battery.minimum_energy_kwh)] * 24
    no_charge = [False] * 24
    no_discharge = [False] * 24
    max_grid: list[float | None] = [None] * 24

    for item in interpretations:
        if not item.applies or not item.structured_adjustment:
            continue

        adj = item.structured_adjustment
        hours = adj.get("hours", [])

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
                current_max = max_grid[h]
                max_grid[h] = maximum if current_max is None else min(current_max, maximum)

    effective_solar = [float(scenario.base_solar_kwh[h]) * solar_factor[h] for h in range(24)]

    return CompiledDirectives(
        solar_factor=solar_factor,
        effective_solar=effective_solar,
        min_reserve=min_reserve,
        no_charge=no_charge,
        no_discharge=no_discharge,
        max_grid=max_grid,
    )
