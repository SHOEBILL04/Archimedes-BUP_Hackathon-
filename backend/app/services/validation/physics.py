"""Physical definitions shared by the optimizer and the replay validator.

Both layers must agree *exactly* on what the physics are, or the validator would
be checking a different model than the one that was solved. Anything both layers
need is defined once, here.

This lives under ``validation`` rather than ``optimizer`` because the dependency
runs one way -- ``optimizer`` imports ``validation``, never the reverse -- so
this is the only placement that keeps the import graph acyclic.
"""

from __future__ import annotations

from app.schemas.optimization import BatteryParameters

from .models import NormalizedDirectives

#: ``BatteryParameters`` exposes no efficiency fields and is declared
#: ``extra="forbid"``, so a lossless round trip is this project's documented
#: battery semantics. The terms are kept explicit in both the LP and the replay
#: so that introducing real losses is a parameter change, not a reformulation.
DEFAULT_CHARGE_EFFICIENCY = 1.0
DEFAULT_DISCHARGE_EFFICIENCY = 1.0


def required_reserve_kwh(
    hour: int, battery: BatteryParameters, normalized: NormalizedDirectives
) -> float:
    """Strictest state-of-charge floor applying to an hour, in kWh.

    Two independent sources are combined:

    * ``battery.minimum_energy_kwh`` -- a physical scenario parameter that holds
      for every hour whether or not an operator said anything.
    * ``normalized.minimum_reserve[hour]`` -- the strictest operator reserve
      directive for that hour, or 0.0 when none applies.

    The guardrail layer deliberately carries only directive-imposed floors, so
    the scenario floor is folded in at the point of use. The optimizer constrains
    against this value and the validator checks against it; sharing one function
    is what guarantees they cannot drift apart.
    """
    return max(battery.minimum_energy_kwh, normalized.minimum_reserve[hour])
