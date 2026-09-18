"""Internal result types for the LP optimizer.

Deliberately separate from the API response schema in ``app.schemas.optimization``:
the optimizer is a pure computational component and must not grow HTTP concerns.
The hourly rows reuse ``HourSchedule`` rather than defining a parallel shape.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.optimization import HOURS, HourSchedule

# Re-exported so callers can reach them from the optimizer package, but defined
# once in app.services.validation.physics -- the optimizer and the replay
# validator must never hold separate copies of a physical constant.
from app.services.validation.physics import (  # noqa: F401
    DEFAULT_CHARGE_EFFICIENCY,
    DEFAULT_DISCHARGE_EFFICIENCY,
)

#: Magnitude below which a negative solver output is treated as floating-point
#: noise and clamped to zero. CBC routinely returns values like -1e-14 for
#: variables it drove to their lower bound of 0. Anything more negative than this
#: is a genuine modelling error and is surfaced as a solver failure rather than
#: silently repaired. This clamps noise only; it never rounds meaningful values.
SOLVER_NEGATIVE_TOLERANCE = 1e-9


class SolverStatus(StrEnum):
    """Normalized solver outcome, decoupled from PuLP's integer status codes."""

    OPTIMAL = "optimal"
    INFEASIBLE = "infeasible"
    UNBOUNDED = "unbounded"
    UNDEFINED = "undefined"
    NOT_SOLVED = "not_solved"
    ERROR = "error"


class OptimizationOutcome(BaseModel):
    """Everything the validator and the API layer need from one solver run.

    A non-optimal run always carries an empty schedule and zeroed totals, so an
    invalid schedule can never be mistaken for a successful optimization.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: SolverStatus
    schedule: tuple[HourSchedule, ...] = Field(default=())
    #: Usable solar per hour after directives, retained so callers can inspect
    #: what the LP was actually offered. The validator recomputes this
    #: independently rather than trusting it.
    effective_solar_kwh: tuple[float, ...] = Field(default=())
    total_grid_kwh: float = Field(default=0.0, ge=0)
    total_grid_cost_bdt: float = Field(default=0.0, ge=0)
    #: CBC's reported objective. Equals total_grid_cost_bdt for a correct model;
    #: kept separate so the validator can cross-check the two.
    objective_value: float = Field(default=0.0)
    message: str = ""

    @property
    def succeeded(self) -> bool:
        return self.status is SolverStatus.OPTIMAL and len(self.schedule) == HOURS
