"""Pure, independently testable solar arithmetic.

Shared deliberately by the optimizer (which needs effective solar to build the
LP) and the replay validator (which must recompute it from the original inputs
rather than trusting the optimizer's reported value).
"""

from __future__ import annotations

from collections.abc import Sequence

from app.schemas.optimization import HOURS

from .models import NormalizedDirectives


def apply_solar_directives(
    base_solar_kwh: Sequence[float],
    normalized: NormalizedDirectives,
) -> tuple[float, ...]:
    """Return usable solar per hour after applying normalized solar directives.

    ``effective_solar[h] = base_solar[h] * product(applicable factors)``

    The product of the applicable factors is precomputed into
    ``normalized.solar_factors[h]`` by the guardrail layer, so this function is a
    single deterministic multiply per hour.

    The baseline ``base_solar_kwh`` is never mutated: guardrails normalize
    operator instructions, they do not alter physical input data.
    """
    if len(base_solar_kwh) != HOURS:
        raise ValueError(f"base_solar_kwh must contain exactly {HOURS} hourly values")

    return tuple(
        base_solar_kwh[hour] * normalized.solar_factors[hour] for hour in range(HOURS)
    )
