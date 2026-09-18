"""Deterministic 24-hour LP dispatch optimizer (PuLP / CBC)."""

from __future__ import annotations

from .lp import SolverNumericalError, solve_dispatch, total_cost
from .models import (
    DEFAULT_CHARGE_EFFICIENCY,
    DEFAULT_DISCHARGE_EFFICIENCY,
    SOLVER_NEGATIVE_TOLERANCE,
    OptimizationOutcome,
    SolverStatus,
)

__all__ = [
    "DEFAULT_CHARGE_EFFICIENCY",
    "DEFAULT_DISCHARGE_EFFICIENCY",
    "SOLVER_NEGATIVE_TOLERANCE",
    "OptimizationOutcome",
    "SolverNumericalError",
    "SolverStatus",
    "solve_dispatch",
    "total_cost",
]
