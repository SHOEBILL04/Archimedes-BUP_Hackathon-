"""Natural-language operator directive interpretation using Groq / OpenAI LLM APIs with LangSmith tracing."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from openai import AsyncOpenAI

try:
    from langsmith import traceable
    from langsmith.wrappers import wrap_openai

    _HAS_LANGSMITH = True
except ImportError:
    _HAS_LANGSMITH = False

    def traceable(*args: Any, **kwargs: Any):
        def decorator(f: Any) -> Any:
            return f

        return decorator

    def wrap_openai(client: Any) -> Any:
        return client

from app.core.config import Settings, get_settings
from app.schemas.optimization import DirectiveInterpretation, EnergyScenario

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a deterministic operator-note parser for a smart campus energy optimizer.

Your ONLY task is to convert each operator note into one supported directive.
Do not optimize anything. Do not change demand, solar, tariff, or battery parameters.
Do not invent directive types.

Supported directive types:
1. solar_reduction:
   structured_adjustment = {"hours": [...], "factor": number}
   factor is the usable fraction remaining. Example: "80% reduction" => factor = 0.2, "reduced to 25%" => factor = 0.25.
2. minimum_battery_reserve:
   structured_adjustment = {"hours": [...], "minimum_energy_kwh": number}
3. no_charge_window:
   structured_adjustment = {"hours": [...]}
4. no_discharge_window:
   structured_adjustment = {"hours": [...]}
5. max_grid_window:
   structured_adjustment = {"hours": [...], "max_grid_kwh": number}
6. no_op:
   structured_adjustment = null, applies = false

Time intervals are whole-hour, start-inclusive and end-exclusive:
- "1 PM to 3 PM" => [13, 14]
- "from 6 PM until 9 PM" => [18, 19, 20]
- "at 17:00" => [17]
- Hours must be unique integers from 0 through 23, sorted ascending.
- Non-energy notes (e.g. cafeteria menu, office notices) MUST be no_op with applies = false.

You must return valid JSON matching this schema:
{
  "interpretations": [
    {
      "note_index": 0,
      "directive_type": "solar_reduction",
      "structured_adjustment": {"hours": [13, 14], "factor": 0.2},
      "applies": true,
      "explanation": "Brief reason"
    }
  ]
}
"""


class LLMService:
    """Service interface for interpreting operator notes with Groq or OpenAI, traced via LangSmith."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @traceable(name="operator_notes_interpretation", run_type="chain", project_name="BUP HACKATHON")
    async def interpret_notes(self, scenario: EnergyScenario) -> list[DirectiveInterpretation]:
        """Convert natural language operator notes into structured directive candidates with LangSmith tracing."""
        n_notes = len(scenario.operator_notes)

        # Ensure LangSmith tracing environment is active if key is configured
        if self.settings.langchain_api_key:
            import os
            os.environ["LANGCHAIN_TRACING_V2"] = "true" if self.settings.langchain_tracing_v2 else "false"
            os.environ["LANGCHAIN_ENDPOINT"] = self.settings.langchain_endpoint
            os.environ["LANGCHAIN_API_KEY"] = self.settings.langchain_api_key
            os.environ["LANGCHAIN_PROJECT"] = self.settings.langchain_project or "BUP HACKATHON"

        # 1. Determine active API credentials (prefer Groq, fallback to OpenAI)
        api_key = self.settings.groq_api_key or self.settings.openai_api_key
        base_url = (
            self.settings.groq_base_url
            if self.settings.groq_api_key
            else "https://api.openai.com/v1"
        )
        model = (
            self.settings.groq_model
            if self.settings.groq_api_key
            else self.settings.openai_model
        )

        if not api_key:
            logger.info("No GROQ_API_KEY or OPENAI_API_KEY configured; returning safe no_op interpretations.")
            return [
                DirectiveInterpretation(
                    note_index=i,
                    directive_type="no_op",
                    structured_adjustment=None,
                    applies=False,
                )
                for i in range(n_notes)
            ]

        # Wrap client with LangSmith for automated tracing
        raw_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        client = wrap_openai(raw_client)

        user_content = json.dumps(
            {
                "battery_capacity_kwh": scenario.battery.capacity_kwh,
                "battery_minimum_energy_kwh": scenario.battery.minimum_energy_kwh,
                "operator_notes": [
                    {"note_index": i, "note": note}
                    for i, note in enumerate(scenario.operator_notes)
                ],
            },
            ensure_ascii=False,
        )

        async def call_llm() -> str:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content or "{}"

        try:
            raw_json = await asyncio.wait_for(call_llm(), timeout=self.settings.llm_timeout_seconds)
            data = json.loads(raw_json)
            raw_items: list[dict[str, Any]] = data.get("interpretations", [])

            interpretations: list[DirectiveInterpretation] = []
            for item in raw_items:
                interpretations.append(
                    DirectiveInterpretation(
                        note_index=int(item["note_index"]),
                        directive_type=item["directive_type"],
                        structured_adjustment=item.get("structured_adjustment"),
                        applies=bool(item.get("applies", False)),
                    )
                )
            return interpretations

        except Exception as exc:
            logger.warning("LLM directive interpretation failed safely: %s; using no_op fallback.", exc)
            return [
                DirectiveInterpretation(
                    note_index=i,
                    directive_type="no_op",
                    structured_adjustment=None,
                    applies=False,
                )
                for i in range(n_notes)
            ]
