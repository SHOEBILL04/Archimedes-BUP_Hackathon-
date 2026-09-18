"""Public API for the Energy Dispatch Optimizer Service.

Higher-level orchestration layers (e.g. OptimizationService) should import
from this package only. Direct access to PuLP or internal solver routines is prohibited.
"""

from __future__ import annotations

from app.services.optimizer.exceptions import (
    OptimizationInfeasibleError,
    OptimizationTimeoutError,
    SolverExecutionError,
)
from app.services.optimizer.guardrails import CompiledDirectives
from app.services.optimizer.lp_optimizer import (
    BatteryInput,
    HourResult,
    InfeasibleError,
    OptimizationError,
    OptimizationResult,
    SolverError,
)
from app.services.optimizer.optimizer_service import run_optimization
from app.services.optimizer.solver import EnergyOptimizer

__all__ = [
    "BatteryInput",
    "CompiledDirectives",
    "EnergyOptimizer",
    "HourResult",
    "InfeasibleError",
    "OptimizationError",
    "OptimizationInfeasibleError",
    "OptimizationResult",
    "OptimizationTimeoutError",
    "SolverError",
    "SolverExecutionError",
    "run_optimization",
]
