from __future__ import annotations

import asyncio
import json
import logging

from openai import AsyncOpenAI
from pydantic import ValidationError

from config import Settings
from guardrails import validate_interpretation, noop
from models import (
    DirectiveInterpretation,
    DirectiveInterpretationResponse,
    EnergyScenario,
)

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
You are a deterministic operator-note parser for a campus energy optimizer.

Your ONLY task is to convert each operator note into one supported directive.
Do not optimize anything. Do not change demand, solar, tariff, battery capacity,
or any scenario value. Do not invent directive types.

Supported directive types:
1. solar_reduction
   structured_adjustment = {"hours":[...], "factor": number}
   factor is the usable fraction remaining. Example: "80% reduction" => 0.2.
2. minimum_battery_reserve
   structured_adjustment = {"hours":[...], "minimum_energy_kwh": number}
3. no_charge_window
   structured_adjustment = {"hours":[...]}
4. no_discharge_window
   structured_adjustment = {"hours":[...]}
5. max_grid_window
   structured_adjustment = {"hours":[...], "max_grid_kwh": number}
6. no_op
   structured_adjustment = null, applies = false

Interpret time intervals as start-inclusive and end-exclusive.
Examples:
- "1 PM to 3 PM" => [13, 14]
- "9am through 11am" => [9, 10]
- "at 17:00" => [17]

Hours MUST be unique integers from 0 through 23 and sorted ascending.
If the note is ambiguous, irrelevant, unsupported, or cannot be safely parsed,
return no_op for that note.

Return exactly one interpretation for every note, in note_index order.
Never output prose outside the JSON object.
"""


def _build_user_prompt(scenario: EnergyScenario) -> str:
    return json.dumps(
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


def _json_schema() -> dict:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "interpretations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "note_index": {"type": "integer", "minimum": 0, "maximum": 2},
                        "directive_type": {
                            "type": "string",
                            "enum": [
                                "solar_reduction",
                                "minimum_battery_reserve",
                                "no_charge_window",
                                "no_discharge_window",
                                "max_grid_window",
                                "no_op",
                            ],
                        },
                        "structured_adjustment": {
                            "anyOf": [
                                {"type": "object"},
                                {"type": "null"},
                            ]
                        },
                        "applies": {"type": "boolean"},
                    },
                    "required": [
                        "note_index",
                        "directive_type",
                        "structured_adjustment",
                        "applies",
                    ],
                },
            }
        },
        "required": ["interpretations"],
    }


async def interpret_notes(
    scenario: EnergyScenario,
    settings: Settings,
) -> list[DirectiveInterpretation]:
    """
    LLM is treated as an untrusted parser.

    Missing/invalid API configuration, timeout, refusal, malformed JSON, or
    Pydantic validation errors all degrade safely to no_op for every note.
    """
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY is not configured; using no_op fallback.")
        return [noop(i) for i in range(len(scenario.operator_notes))]

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def call():
        response = await client.responses.create(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(scenario)},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "directive_interpretation",
                    "strict": True,
                    "schema": _json_schema(),
                }
            },
            temperature=0,
            max_output_tokens=800,
        )
        return response.output_text

    try:
        raw_json = await asyncio.wait_for(call(), timeout=settings.llm_timeout_seconds)
        parsed = DirectiveInterpretationResponse.model_validate_json(raw_json)
        return validate_interpretation(parsed.interpretations, scenario)
    except (asyncio.TimeoutError, ValidationError, ValueError, TypeError) as exc:
        logger.warning("LLM interpretation failed safely: %s", exc)
        return [noop(i) for i in range(len(scenario.operator_notes))]
    except Exception as exc:
        logger.exception("Unexpected LLM failure; using no_op fallback: %s", exc)
        return [noop(i) for i in range(len(scenario.operator_notes))]
