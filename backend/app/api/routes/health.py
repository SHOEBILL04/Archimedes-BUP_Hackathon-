from __future__ import annotations

from fastapi import APIRouter

from app.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Return health status of the API service."""
    return HealthResponse(status="ok")
