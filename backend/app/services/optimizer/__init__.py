"""Public API for the Energy Dispatch Optimizer Service.

Higher-level orchestration layers (e.g. OptimizationService) should import
from this package only. Direct access to PuLP or internal solver routines is prohibited.
"""

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

__all__ = [
    "BatteryInput",
    "CompiledDirectives",
    "HourResult",
    "InfeasibleError",
    "OptimizationError",
    "OptimizationResult",
    "SolverError",
    "run_optimization",
]
