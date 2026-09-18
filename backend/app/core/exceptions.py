from __future__ import annotations

from typing import Any


class AppBaseException(Exception):
    """Base exception for application-level errors."""

    def __init__(self, message: str, details: Any | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class EntityNotFoundException(AppBaseException):
    """Raised when a requested resource is not found."""


class ValidationException(AppBaseException):
    """Raised when domain guardrail validation fails."""


class OptimizationException(AppBaseException):
    """Raised when the optimization pipeline fails or is infeasible."""


class LLMServiceException(AppBaseException):
    """Raised when LLM interpretation fails or times out."""
