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
from app.services.optimizer.interface import IOptimizer
from app.services.optimizer.lp_optimizer import (
    BatteryInput,
    HourResult,
    InfeasibleError,
    OptimizationError,
    SolverError,
)
from app.services.optimizer.models import (
    SUPPORTED_DIRECTIVE_TYPES,
    BatteryConfig,
    CompiledDirectives,
    DirectiveType,
    HourlyEnergyData,
    HourlyEnergyProfile,
    HourlyScheduleOutput,
    NormalizedDirective,
    OptimizationInput,
    OptimizationResult,
    SolverStatus,
)
from app.services.optimizer.optimizer_service import run_optimization
from app.services.optimizer.solver import EnergyOptimizer

__all__ = [
    # Domain Models & Types
    "BatteryConfig",
    "BatteryInput",
    "CompiledDirectives",
    "DirectiveType",
    "EnergyOptimizer",
    "HourResult",
    "HourlyEnergyData",
    "HourlyEnergyProfile",
    "HourlyScheduleOutput",
    "InfeasibleError",
    "NormalizedDirective",
    "OptimizationError",
    "OptimizationInfeasibleError",
    "OptimizationInput",
    "OptimizationResult",
    "OptimizationTimeoutError",
    "SUPPORTED_DIRECTIVE_TYPES",
    "SolverError",
    "SolverExecutionError",
    "SolverStatus",
    # Interfaces
    "IOptimizer",
    # Legacy Run Entrypoint
    "run_optimization",
]
