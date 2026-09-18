from __future__ import annotations

from app.core.logging import logger
from app.schemas.optimization import (
    DirectiveInterpretation,
    EnergyScenario,
    HourSchedule,
    VerificationResult,
)


class ValidationService:
    """Service interface for deterministic guardrails and replay validation.

    NOTE: This is a scaffold placeholder. The mathematical balance check,
    battery bounds replay, and directive guardrails will be implemented in the next phase.
    """

    def validate_directives(
        self, scenario: EnergyScenario, directives: list[DirectiveInterpretation]
    ) -> list[DirectiveInterpretation]:
        """Validate LLM directives against physical boundaries before solver execution."""
        logger.info("ValidationService.validate_directives called (PLACEHOLDER)")
        return directives

    def replay_validate_schedule(
        self, scenario: EnergyScenario, schedule: list[HourSchedule]
    ) -> VerificationResult:
        """Replay-simulate the schedule hour-by-hour to ensure zero physical constraint violations."""
        logger.info("ValidationService.replay_validate_schedule called (PLACEHOLDER)")

        total_cost = sum(entry.grid_cost_bdt for entry in schedule)
        return VerificationResult(
            verified=True,
            max_constraint_error=0.0,
            total_grid_cost_bdt=round(total_cost, 2),
        )
