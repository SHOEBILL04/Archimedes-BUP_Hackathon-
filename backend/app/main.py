from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_v1_router
from app.api.routes.health import router as root_health_router
from app.api.routes.optimization import router as root_optimization_router
from app.core.config import get_settings
from app.core.exceptions import AppBaseException
from app.core.logging import logger

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Startup and shutdown events."""
    logger.info("Starting %s in %s mode", settings.app_name, settings.app_env)
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Production-grade FastAPI service for Smart Campus Energy Optimization Challenge. "
        "Integrates 24-hour demand/solar/tariff dispatch with battery scheduling, "
        "deterministic guardrails, and future LLM operator note interpretation."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handling
@app.exception_handler(AppBaseException)
async def app_base_exception_handler(request: Request, exc: AppBaseException) -> JSONResponse:
    logger.error("Handled Application Exception: %s", exc.message)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message, "details": exc.details},
    )


# Expose root GET /health and POST /optimize-energy for hackathon judge
app.include_router(root_health_router)
app.include_router(root_optimization_router)

# Expose API v1 routes (/api/v1/health, /api/v1/optimize-energy)
app.include_router(api_v1_router, prefix="/api/v1")
