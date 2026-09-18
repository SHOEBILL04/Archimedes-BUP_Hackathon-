from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CompiledDirectives:
    """Compiled 24-hour hourly constraint arrays derived from sanitized directives.

    Each array is guaranteed to have exactly 24 elements corresponding to hours 0 through 23.
    """

    solar_factor: list[float]
    effective_solar: list[float]
    min_reserve: list[float]
    no_charge: list[bool]
    no_discharge: list[bool]
    max_grid: list[float | None]

    def to_dict(self) -> dict[str, Any]:
        """Convert compiled constraints to dictionary format for backwards compatibility."""
        return {
            "solar_factor": self.solar_factor,
            "effective_solar": self.effective_solar,
            "min_reserve": self.min_reserve,
            "no_charge": self.no_charge,
            "no_discharge": self.no_discharge,
            "max_grid": self.max_grid,
        }
