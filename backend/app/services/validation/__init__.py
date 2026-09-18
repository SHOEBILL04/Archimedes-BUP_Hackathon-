"""Independent Replay Validation Service Package.

Exposes deterministic simulation and verification routines to audit candidate
dispatch schedules against all physical equations and operational directives.
"""

from __future__ import annotations

from app.services.optimizer.models import (
    SUPPORTED_DIRECTIVE_TYPES,
    DirectiveType,
    NormalizedDirective,
    ReplayValidationResult,
)
from app.services.validation.compiler import compile_directives
from app.services.validation.directive_guardrail import (
    BatchDirectiveValidationResult,
    DeterministicDirectiveGuardrail,
    DirectiveValidationErrorItem,
    DirectiveValidationResult,
    validate_directive,
    validate_directive_batch,
    validate_directive_batch_strict,
    validate_directive_strict,
)
from app.services.validation.exceptions import GuardrailValidationError
from app.services.validation.guardrails import noop, validate_directives, validate_interpretation
from app.services.validation.interface import (
    IDirectiveCompiler,
    IDirectiveGuardrail,
    IReplayValidator,
)
from app.services.validation.models import CompiledDirectives
from app.services.validation.replay import replay_validate as replay_validate_schedule
from app.services.validation.replay_validator import (
    ReplayValidationError,
    ReplayValidationInput,
    ValidationResult,
    replay_validate,
    validate_and_raise,
)

__all__ = [
    # Domain Models & Types
    "BatchDirectiveValidationResult",
    "CompiledDirectives",
    "DirectiveType",
    "DirectiveValidationErrorItem",
    "DirectiveValidationResult",
    "NormalizedDirective",
    "ReplayValidationInput",
    "ReplayValidationResult",
    "SUPPORTED_DIRECTIVE_TYPES",
    "ValidationResult",
    # Guardrails
    "DeterministicDirectiveGuardrail",
    # Exceptions
    "GuardrailValidationError",
    "ReplayValidationError",
    # Interfaces
    "IDirectiveCompiler",
    "IDirectiveGuardrail",
    "IReplayValidator",
    # Functions
    "compile_directives",
    "noop",
    "replay_validate",
    "replay_validate_schedule",
    "validate_and_raise",
    "validate_directive",
    "validate_directive_batch",
    "validate_directive_batch_strict",
    "validate_directive_strict",
    "validate_directives",
    "validate_interpretation",
]
