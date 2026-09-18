from __future__ import annotations

from app.core.config import Settings, get_settings
from app.core.logging import logger
from app.schemas.optimization import DirectiveInterpretation, EnergyScenario


class LLMService:
    """Service interface for interpreting natural-language operator notes into structured directives.

    NOTE: This is a production scaffold placeholder. The OpenAI integration will be
    implemented in the next phase using the configured model and timeouts.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def interpret_notes(self, scenario: EnergyScenario) -> list[DirectiveInterpretation]:
        """Placeholder interpreter returning structured mock directives for scaffold verification."""
        logger.info(
            "LLMService.interpret_notes called (PLACEHOLDER) with %d notes",
            len(scenario.operator_notes),
        )

        interpretations: list[DirectiveInterpretation] = []
        for idx, note in enumerate(scenario.operator_notes):
            # Scaffold default: marked as placeholder no_op or rule placeholder
            interpretations.append(
                DirectiveInterpretation(
                    note_index=idx,
                    directive_type="no_op",
                    structured_adjustment={"raw_note": note, "status": "scaffold_placeholder"},
                    applies=True,
                )
            )
        return interpretations
