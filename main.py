from __future__ import annotations

import asyncio
import logging
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from config import get_settings
from llm_interpreter import interpret_notes
from models import EnergyScenario, OptimizationResponse
from optimizer import OptimizationError, optimize_energy
from validator import ReplayValidationError, replay_validate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smart-campus-energy")

app = FastAPI(
    title="Smart Campus Energy Optimization API",
    version="1.0.0",
    description=(
        "LLM-assisted directive interpretation followed by deterministic "
        "guardrails, linear-programming dispatch, and replay verification."
    ),
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/optimize-energy", response_model=OptimizationResponse)
async def optimize_energy_endpoint(
    scenario: EnergyScenario,
    request: Request,
) -> OptimizationResponse | JSONResponse:
    settings = get_settings()
    started = time.perf_counter()

    async def pipeline() -> OptimizationResponse:
        interpretations = await interpret_notes(scenario, settings)

        # PuLP/CBC is synchronous; keep it off the event-loop thread.
        result = await asyncio.to_thread(
            optimize_energy,
            scenario,
            interpretations,
            settings.solver_timeout_seconds,
        )

        verification = replay_validate(
            scenario=scenario,
            interpretations=interpretations,
            schedule=result.schedule,
            reported_total_cost=result.total_grid_cost_bdt,
        )

        response = OptimizationResponse(
            directive_interpretation=interpretations,
            schedule=result.schedule,
            total_grid_cost_bdt=result.total_grid_cost_bdt,
            total_grid_kwh=result.total_grid_kwh,
            verification=verification,
        )

        # One final Pydantic validation before serialization.
        return OptimizationResponse.model_validate(response.model_dump())

    try:
        response = await asyncio.wait_for(
            pipeline(),
            timeout=settings.api_timeout_seconds,
        )
        elapsed = time.perf_counter() - started
        logger.info(
            "optimization completed in %.3fs from %s",
            elapsed,
            request.client.host if request.client else "unknown",
        )
        return response

    except asyncio.TimeoutError:
        logger.error("request exceeded %.2fs", settings.api_timeout_seconds)
        raise HTTPException(
            status_code=504,
            detail="optimization request exceeded the service time budget",
        )

    except OptimizationError as exc:
        logger.warning("optimization error: %s", exc)
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )

    except ReplayValidationError as exc:
        logger.error("replay validation failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="internal replay validation failure",
        )

    except Exception:
        logger.exception("unexpected optimization failure")
        raise HTTPException(
            status_code=500,
            detail="internal server error",
        )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled request error")
    return JSONResponse(
        status_code=500,
        content={"detail": "internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
    )
