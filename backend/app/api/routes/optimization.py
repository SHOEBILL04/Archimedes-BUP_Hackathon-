from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.optimization import EnergyScenario, OptimizationResponse
from app.services.optimization_service import OptimizationService

router = APIRouter(prefix="/optimize-energy", tags=["Optimization"])


def get_optimization_service() -> OptimizationService:
    return OptimizationService()


@router.post(
    "",
    response_model=OptimizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Optimize 24-hour campus energy dispatch",
    description=(
        "Accepts a 24-hour campus scenario (demand, solar, tariff, battery parameters, and operator notes). "
        "Returns a validated 24-hour schedule and directives interpretation. "
        "NOTE: Currently returns a verified scaffold placeholder response."
    ),
)
async def optimize_energy(
    scenario: EnergyScenario,
    service: OptimizationService = Depends(get_optimization_service),
    db: Session = Depends(get_db),
) -> OptimizationResponse:
    """Execute energy optimization pipeline."""
    return await service.optimize(scenario, db=db, persist=True)
