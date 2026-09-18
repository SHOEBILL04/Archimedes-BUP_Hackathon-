"""Abstract interface contracts for deterministic guardrails and replay validation."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.services.optimizer.models import (
    BatteryConfig,
    CompiledDirectives,
    HourlyScheduleOutput,
    NormalizedDirective,
    OptimizationInput,
    ReplayValidationResult,
)


@runtime_checkable
class IReplayValidator(Protocol):
    """Abstract interface contract for independent replay validation.

    Audits candidate dispatch schedules against hourly physical conservation equations,
    rate limits, battery state dynamics, and operator directives without invoking the solver.
    """

    def validate(
        self,
        opt_input: OptimizationInput,
        schedule: list[HourlyScheduleOutput],
        reported_total_cost: float,
        tolerance: float = 1e-4,
    ) -> ReplayValidationResult:
        """Perform deterministic simulation and verify zero physical constraint violations.

        Args:
            opt_input: Original optimization input parameters.
            schedule: 24-hour candidate dispatch schedule to audit.
            reported_total_cost: Total grid cost reported by the solver.
            tolerance: Maximum allowable numerical floating-point error.

        Returns:
            ReplayValidationResult indicating verification status, max error, and violations.

        Raises:
            ReplayValidationError: If strict validation mode is requested and violations occur.
        """
        ...


@runtime_checkable
class IDirectiveGuardrail(Protocol):
    """Abstract interface for validating untrusted LLM directive interpretations."""

    def sanitize(
        self,
        raw_directives: list[dict],
        note_count: int,
        battery_capacity: float,
    ) -> list[NormalizedDirective]:
        """Validate and sanitize raw directive interpretations, falling back safely to no_op."""
        ...


@runtime_checkable
class IDirectiveCompiler(Protocol):
    """Abstract interface for compiling directives into 24-hour constraint arrays."""

    def compile(
        self,
        directives: list[NormalizedDirective],
        base_solar: list[float],
        battery: BatteryConfig,
    ) -> CompiledDirectives:
        """Compile normalized directives into deterministic hourly constraint vectors."""
        ...
