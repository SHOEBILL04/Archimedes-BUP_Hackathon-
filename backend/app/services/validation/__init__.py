"""Independent Replay Validation Service Package.

Exposes deterministic simulation and verification routines to audit candidate
dispatch schedules against all physical equations and operational directives.
"""

from __future__ import annotations

from app.services.validation.compiler import compile_directives
from app.services.validation.exceptions import GuardrailValidationError
from app.services.validation.guardrails import noop, validate_directives, validate_interpretation
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
    "CompiledDirectives",
    "GuardrailValidationError",
    "ReplayValidationError",
    "ReplayValidationInput",
    "ValidationResult",
    "compile_directives",
    "noop",
    "replay_validate",
    "replay_validate_schedule",
    "validate_and_raise",
    "validate_directives",
    "validate_interpretation",
]
