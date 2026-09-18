from __future__ import annotations

from typing import Any

from app.core.exceptions import ValidationException


class GuardrailValidationError(ValidationException):
    """Raised when deterministic guardrail validation detects an unrecoverable directive violation."""

    def __init__(self, message: str, details: Any | None = None) -> None:
        super().__init__(message, details)


class ReplayValidationError(ValidationException):
    """Raised when physical schedule replay simulation detects constraint violations exceeding tolerance."""

    def __init__(
        self,
        message: str,
        constraint_name: str | None = None,
        hour: int | None = None,
        violation_error: float | None = None,
        details: Any | None = None,
    ) -> None:
        self.constraint_name = constraint_name
        self.hour = hour
        self.violation_error = violation_error
        full_details = details or {}
        if isinstance(full_details, dict):
            if constraint_name:
                full_details["constraint_name"] = constraint_name
            if hour is not None:
                full_details["hour"] = hour
            if violation_error is not None:
                full_details["violation_error"] = violation_error
        super().__init__(message, full_details)
