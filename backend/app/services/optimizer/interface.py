"""Abstract interface contracts for energy dispatch solvers.

Decouples higher-level orchestration services from concrete linear programming
implementations (such as PuLP, CBC, or HiGHS).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.services.optimizer.models import OptimizationInput, OptimizationResult


@runtime_checkable
class IOptimizer(Protocol):
    """Abstract interface contract for energy dispatch optimization engines.

    Higher-level services must interact with the solver exclusively via this protocol.
    Direct imports of PuLP or external solver packages in orchestration, API, or repository
    layers are prohibited.
    """

    def solve(
        self,
        opt_input: OptimizationInput,
        timeout_seconds: float = 5.0,
    ) -> OptimizationResult:
        """Formulate and solve the 24-hour cost minimization problem.

        Args:
            opt_input: Validated numerical input parameters and compiled directives.
            timeout_seconds: Maximum wall-clock time in seconds before aborting.

        Returns:
            OptimizationResult containing 24-hour schedule, costs, energy, and solver status.

        Raises:
            OptimizationInfeasibleError: If constraints are mathematically contradictory.
            OptimizationTimeoutError: If execution exceeds the allotted timeout.
            SolverExecutionError: If the external solver binary crashes or fails.
        """
        ...
