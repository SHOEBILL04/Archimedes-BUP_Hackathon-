from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import logger
from app.repositories.optimization_repository import OptimizationRepository
from app.schemas.optimization import (
    EnergyScenario,
    HourSchedule,
    OptimizationResponse,
)
from app.services.llm_service import LLMService
from app.services.validation_service import ValidationService


class OptimizationService:
    """Orchestrates the energy optimization pipeline:
    LLM Interpretation -> Guardrails -> LP Solver (placeholder) -> Replay Validator -> DB Persistence.
    """

    def __init__(
        self,
        llm_service: LLMService | None = None,
        validation_service: ValidationService | None = None,
    ) -> None:
        self.llm_service = llm_service or LLMService()
        self.validation_service = validation_service or ValidationService()

    async def optimize(
        self, scenario: EnergyScenario, db: Session | None = None, persist: bool = True
    ) -> OptimizationResponse:
        """Run the end-to-end optimization pipeline.

        Returns a clearly marked scaffold placeholder response.
        The actual PuLP/CBC linear program will be plugged in here in the next phase.
        """
        logger.info("OptimizationService.optimize called (SCAFFOLD PLACEHOLDER)")

        # 1. LLM Directive Interpretation (Placeholder)
        directives = await self.llm_service.interpret_notes(scenario)

        # 2. Deterministic Guardrails (Placeholder)
        validated_directives = self.validation_service.validate_directives(scenario, directives)

        # 3. Solver dispatch (Scaffold placeholder 24-hr schedule)
        # Baseline deterministic logic: solar meets demand first, rest from grid, battery idle
        schedules: list[HourSchedule] = []
        total_grid_kwh = 0.0
        total_grid_cost = 0.0

        for h in range(24):
            demand = scenario.demand_kwh[h]
            solar = scenario.base_solar_kwh[h]
            tariff = scenario.tariff_bdt_per_kwh[h]

            solar_used = min(demand, solar)
            grid_needed = max(0.0, demand - solar_used)
            grid_cost = round(grid_needed * tariff, 2)

            total_grid_kwh += grid_needed
            total_grid_cost += grid_cost

            schedules.append(
                HourSchedule(
                    hour=h,
                    demand_kwh=round(demand, 2),
                    effective_solar_kwh=round(solar, 2),
                    solar_used_kwh=round(solar_used, 2),
                    battery_charge_kwh=0.0,
                    battery_discharge_kwh=0.0,
                    battery_energy_after_kwh=round(scenario.battery.initial_energy_kwh, 2),
                    grid_kwh=round(grid_needed, 2),
                    tariff_bdt_per_kwh=round(tariff, 2),
                    grid_cost_bdt=grid_cost,
                )
            )

        # 4. Replay Validation (Placeholder)
        verification = self.validation_service.replay_validate_schedule(scenario, schedules)

        response = OptimizationResponse(
            directive_interpretation=validated_directives,
            schedule=schedules,
            total_grid_cost_bdt=round(total_grid_cost, 2),
            total_grid_kwh=round(total_grid_kwh, 2),
            verification=verification,
            status_message="[SCAFFOLD_PLACEHOLDER] Optimization pipeline scaffold response. Business logic will be implemented in next phase.",
        )

        # 5. Repository persistence into SQLite if DB session is supplied
        if db is not None and persist:
            try:
                repo = OptimizationRepository(db)
                repo.save_optimization_run(scenario, response)
                logger.info("Saved scaffold optimization result into SQLite database")
            except Exception as e:
                logger.warning("Could not persist optimization to database: %s", e)

        return response
