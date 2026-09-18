from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import health, optimization

api_v1_router = APIRouter()

# Register health under /api/v1/health
api_v1_router.include_router(health.router)

# Register optimization under /api/v1/optimize-energy
api_v1_router.include_router(optimization.router)
