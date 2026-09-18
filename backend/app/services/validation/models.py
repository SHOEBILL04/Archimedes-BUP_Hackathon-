"""Internal representation of operator directives after deterministic normalization.

These models are the contract between the guardrail layer, the LP optimizer and
the replay validator. They are deliberately *not* API schemas: the API response
shape lives in ``app.schemas.optimization`` and must not be duplicated here.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.optimization import HOURS


class DirectiveRejection(BaseModel):
    """A directive that failed a guardrail and was excluded from the optimization.

    Rejections are recorded rather than raised: a single malformed directive from
    an untrusted LLM must not fail the whole request. The optimizer only ever sees
    directives that survived every check.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    note_index: int = Field(ge=0)
    directive_type: str
    reason: str


class NormalizedDirectives(BaseModel):
    """Per-hour constraint arrays derived from accepted operator directives.

    Every field is exactly 24 entries long and indexed by hour 0..23, so the
    optimizer can read constraints positionally without re-interpreting intent.

    Defaults represent "no operator constraint":
      * ``solar_factors``  1.0  -> full baseline solar remains usable
      * ``minimum_reserve`` 0.0 -> no directive-imposed floor
      * ``no_charge``      False
      * ``no_discharge``   False
      * ``max_grid``       None -> grid import unbounded by operator directive

    ``minimum_reserve`` intentionally carries *only* directive-imposed floors.
    The battery's own ``minimum_energy_kwh`` is a physical scenario parameter,
    not an operator instruction, so the optimizer combines the two. This keeps
    the guardrail layer strictly about normalizing operator intent.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    solar_factors: tuple[float, ...] = Field(min_length=HOURS, max_length=HOURS)
    minimum_reserve: tuple[float, ...] = Field(min_length=HOURS, max_length=HOURS)
    no_charge: tuple[bool, ...] = Field(min_length=HOURS, max_length=HOURS)
    no_discharge: tuple[bool, ...] = Field(min_length=HOURS, max_length=HOURS)
    max_grid: tuple[float | None, ...] = Field(min_length=HOURS, max_length=HOURS)

    @classmethod
    def identity(cls) -> NormalizedDirectives:
        """Return the neutral element: no operator constraints on any hour."""
        return cls(
            solar_factors=tuple(1.0 for _ in range(HOURS)),
            minimum_reserve=tuple(0.0 for _ in range(HOURS)),
            no_charge=tuple(False for _ in range(HOURS)),
            no_discharge=tuple(False for _ in range(HOURS)),
            max_grid=tuple(None for _ in range(HOURS)),
        )


class GuardrailReport(BaseModel):
    """Outcome of normalizing a batch of LLM directive interpretations."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    normalized: NormalizedDirectives
    #: ``note_index`` of every directive that passed all guardrails.
    accepted: tuple[int, ...] = Field(default=())
    rejections: tuple[DirectiveRejection, ...] = Field(default=())
