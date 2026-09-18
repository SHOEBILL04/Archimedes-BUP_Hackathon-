"""Deterministic guardrail and replay-validation layer."""

from __future__ import annotations

from .guardrails import SUPPORTED_DIRECTIVE_TYPES, normalize_directives
from .models import DirectiveRejection, GuardrailReport, NormalizedDirectives
from .physics import (
    DEFAULT_CHARGE_EFFICIENCY,
    DEFAULT_DISCHARGE_EFFICIENCY,
    required_reserve_kwh,
)
from .replay import TOLERANCE, ReplayValidationResult, ValidationIssue, replay_validate
from .solar import apply_solar_directives

__all__ = [
    "DEFAULT_CHARGE_EFFICIENCY",
    "DEFAULT_DISCHARGE_EFFICIENCY",
    "SUPPORTED_DIRECTIVE_TYPES",
    "TOLERANCE",
    "DirectiveRejection",
    "GuardrailReport",
    "NormalizedDirectives",
    "ReplayValidationResult",
    "ValidationIssue",
    "apply_solar_directives",
    "normalize_directives",
    "replay_validate",
    "required_reserve_kwh",
]
