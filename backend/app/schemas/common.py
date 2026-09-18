from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ErrorResponse(BaseModel):
    detail: str
    code: str = Field(default="INTERNAL_ERROR")
    context: dict[str, Any] | None = None
