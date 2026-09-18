from __future__ import annotations

from app.core.logging import logger
from app.schemas.optimization import (
    DirectiveInterpretation,
    EnergyScenario,
    HourSchedule,
    VerificationResult,
)
from app.services.validation.compiler import compile_directives
from app.services.validation.guardrails import validate_directives
from app.services.validation.models import CompiledDirectives
from app.services.validation.replay import replay_validate


class ValidationService:
    """Production service facade providing deterministic guardrails and replay validation.

    Delegates to specialized modular engines:
      - validate_directives: sanitizes untrusted LLM directives against physical boundaries
      - replay_validate_schedule: verifies 24-hour dispatch schedule against hourly physical equations
    """

    def validate_directives(
        self, scenario: EnergyScenario, directives: list[DirectiveInterpretation]
    ) -> list[DirectiveInterpretation]:
        """Validate LLM directives against physical boundaries before solver execution."""
        logger.info(
            "ValidationService.validate_directives invoked with %d directives", len(directives)
        )
        return validate_directives(scenario, directives)

    def replay_validate_schedule(
        self,
        scenario: EnergyScenario,
        schedule: list[HourSchedule],
        directives: list[DirectiveInterpretation] | None = None,
        compiled_directives: CompiledDirectives | None = None,
    ) -> VerificationResult:
        """Replay-simulate the schedule hour-by-hour to guarantee zero physical constraint violations."""
        logger.info("ValidationService.replay_validate_schedule invoked for 24-hour schedule")

        if compiled_directives is None:
            if directives is not None:
                compiled_directives = compile_directives(scenario, directives)
            else:
                # Default baseline (no applied directives)
                compiled_directives = compile_directives(scenario, [])

        total_cost = sum(entry.grid_cost_bdt for entry in schedule)
        return replay_validate(
            scenario=scenario,
            directives=compiled_directives,
            schedule=schedule,
            reported_total_cost=total_cost,
        )
