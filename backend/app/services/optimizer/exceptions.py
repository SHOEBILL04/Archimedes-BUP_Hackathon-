from __future__ import annotations

from typing import Any

from app.core.exceptions import OptimizationException


class OptimizationInfeasibleError(OptimizationException):
    """Raised when the linear programming formulation has no feasible solution."""

    def __init__(
        self,
        message: str = "Optimization problem is mathematically infeasible",
        details: Any | None = None,
    ) -> None:
        super().__init__(message, details)


class OptimizationTimeoutError(OptimizationException):
    """Raised when the solver exceeds its maximum execution time budget."""

    def __init__(
        self, message: str = "Optimization solver timed out", details: Any | None = None
    ) -> None:
        super().__init__(message, details)


class SolverExecutionError(OptimizationException):
    """Raised when the external solver binary fails to execute or crashes."""

    def __init__(
        self, message: str = "Optimization solver failed execution", details: Any | None = None
    ) -> None:
        super().__init__(message, details)
