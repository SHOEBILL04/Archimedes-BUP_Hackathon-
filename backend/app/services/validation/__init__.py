"""Independent Replay Validation Service Package.

Exposes deterministic simulation and verification routines to audit candidate
dispatch schedules against all physical equations and operational directives.
"""

from app.services.validation.replay_validator import (
    ReplayValidationError,
    ReplayValidationInput,
    ValidationResult,
    replay_validate,
    validate_and_raise,
)

__all__ = [
    "ReplayValidationError",
    "ReplayValidationInput",
    "ValidationResult",
    "replay_validate",
    "validate_and_raise",
]
