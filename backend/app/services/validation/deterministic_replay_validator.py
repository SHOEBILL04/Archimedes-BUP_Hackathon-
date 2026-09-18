"""Deterministic Replay Validator Engine for 24-Hour Energy Dispatch.

This module independently verifies candidate optimization schedules against:
1. Schedule length & hourly sequencing (exactly 24 sequential hours 0..23).
2. Non-negative physical variables (grid, solar, charge, discharge >= -tolerance).
3. Hourly energy conservation balance: (grid + solar_used + discharge) == (demand + charge).
4. Solar availability ceiling: solar_used <= effective_solar.
5. Independent battery state-space dynamics: energy_after[t] == energy_after[t-1] + charge*eta_c - discharge/eta_d.
6. Battery capacity and non-negative bounds: -tolerance <= energy_after <= capacity + tolerance.
7. Battery charge rate limit: charge <= max_charge_rate + tolerance.
8. Battery discharge rate limit: discharge <= max_discharge_rate + tolerance.
9. Directive enforcement:
   - no_charge_window: charge <= tolerance
   - no_discharge_window: discharge <= tolerance
   - minimum_battery_reserve: energy_after >= min_reserve - tolerance
   - max_grid_window: grid <= max_grid + tolerance
10. End-of-day battery neutrality: abs(energy_after[23] - initial_energy) <= tolerance.
11. Objective cost recalculation: abs(sum(grid * tariff) - reported_total_cost) <= tolerance.

It does not invoke PuLP, does not modify optimizer models, and does not call any LLMs.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from app.services.optimizer.models import (
    HOURS_IN_DAY,
    HourlyScheduleOutput,
    OptimizationInput,
    ReplayValidationResult,
)
from app.services.validation.exceptions import ReplayValidationError
from app.services.validation.interface import IReplayValidator

logger = logging.getLogger(__name__)

# Default floating-point tolerance for physical and contractual equality
DEFAULT_TOLERANCE: float = 1e-4


def _extract_val(obj: Any, *attr_names: str, default: float = 0.0) -> float:
    """Safely extract float attribute or dict key from schedule row."""
    for name in attr_names:
        if isinstance(obj, dict) and name in obj:
            return float(obj[name])
        if hasattr(obj, name):
            val = getattr(obj, name)
            if val is not None:
                return float(val)
    return default


class DeterministicReplayValidator(IReplayValidator):
    """Independent deterministic auditor for 24-hour candidate dispatch schedules."""

    def __init__(
        self,
        default_tolerance: float = DEFAULT_TOLERANCE,
        enforce_eod_neutrality: bool = True,
    ) -> None:
        self.default_tolerance = default_tolerance
        self.enforce_eod_neutrality = enforce_eod_neutrality

    def validate(
        self,
        opt_input: OptimizationInput,
        schedule: list[HourlyScheduleOutput] | list[Any],
        reported_total_cost: float,
        tolerance: float | None = None,
        enforce_eod_neutrality: bool | None = None,
        strict: bool = False,
    ) -> ReplayValidationResult:
        """Perform comprehensive independent replay audit on a candidate dispatch schedule.

        Args:
            opt_input: Validated optimization inputs containing profile, battery, and directives.
            schedule: Candidate 24-hour schedule to audit.
            reported_total_cost: Total grid electricity cost reported by the solver.
            tolerance: Numerical tolerance threshold (defaults to self.default_tolerance).
            enforce_eod_neutrality: Whether to check end-of-day battery neutrality.
            strict: If True, raises ReplayValidationError on first set of violations.

        Returns:
            ReplayValidationResult indicating verification status, max error, and violations.

        Raises:
            ReplayValidationError: If strict=True and one or more violations occur.
        """
        tol = tolerance if tolerance is not None else self.default_tolerance
        eod_neutral = (
            enforce_eod_neutrality
            if enforce_eod_neutrality is not None
            else self.enforce_eod_neutrality
        )
        violations: list[str] = []
        max_error: float = 0.0

        # ── CHECK 1: 24 HOURS ──
        if len(schedule) != HOURS_IN_DAY:
            err = (
                f"Schedule length violation: schedule must contain exactly {HOURS_IN_DAY} "
                f"hourly entries, got {len(schedule)}"
            )
            violations.append(err)
            result = ReplayValidationResult(
                verified=False,
                max_constraint_error=1.0,
                total_grid_cost_bdt=0.0,
                violations=violations,
                details={"step": "length_check", "length": len(schedule)},
            )
            if strict:
                raise ReplayValidationError(
                    err, constraint_name="schedule_length", details={"length": len(schedule)}
                )
            return result

        # Check sequential hour indexing 0..23
        for h, row in enumerate(schedule):
            row_hour = _extract_val(row, "hour", default=-1)
            if int(row_hour) != h:
                violations.append(
                    f"Schedule hour sequence violation at index {h}: expected hour {h}, got {int(row_hour)}"
                )
                max_error = max(max_error, 1.0)

        # Retrieve scenarios & directives
        demand_profile = opt_input.energy_profile.demand_kwh
        tariff_profile = opt_input.energy_profile.tariff_bdt_per_kwh
        battery = opt_input.battery
        directives = opt_input.compiled_directives

        charge_eff = battery.charge_efficiency
        discharge_eff = battery.discharge_efficiency
        if charge_eff <= 0.0:
            charge_eff = 1.0
        if discharge_eff <= 0.0:
            discharge_eff = 1.0

        recalculated_cost = 0.0
        previous_energy = battery.initial_energy_kwh

        # ── HOURLY REPLAY LOOP ──
        for h in range(HOURS_IN_DAY):
            row = schedule[h]

            grid = _extract_val(row, "grid_kwh", "grid")
            solar_used = _extract_val(row, "solar_used_kwh", "solar_used")
            charge = _extract_val(row, "battery_charge_kwh", "battery_charge")
            discharge = _extract_val(row, "battery_discharge_kwh", "battery_discharge")
            energy_after = _extract_val(row, "battery_energy_after_kwh", "battery_energy_after")

            demand = demand_profile[h]
            tariff = tariff_profile[h]

            # ── CHECK 2: FINITENESS & NON-NEGATIVE VALUES ──
            values_to_check = {
                "grid": grid,
                "solar_used": solar_used,
                "battery_charge": charge,
                "battery_discharge": discharge,
            }
            for var_name, val in values_to_check.items():
                if not math.isfinite(val):
                    violations.append(f"Hour {h}: non-finite value in {var_name} ({val})")
                    max_error = max(max_error, 1.0)
                elif val < -tol:
                    neg_err = abs(val)
                    max_error = max(max_error, neg_err)
                    violations.append(
                        f"Hour {h}: negative value in {var_name} ({val:.6f} < {-tol})"
                    )

            # ── CHECK 3: ENERGY BALANCE ──
            # Conservation: grid[h] + solar_used[h] + battery_discharge[h] == demand[h] + battery_charge[h]
            supplied = grid + solar_used + discharge
            demanded = demand + charge
            balance_err = abs(supplied - demanded)
            if balance_err > max_error:
                max_error = balance_err
            if balance_err > tol:
                violations.append(
                    f"Hour {h}: energy balance violation (supplied={supplied:.4f} kWh, "
                    f"demanded={demanded:.4f} kWh, balance_err={balance_err:.6f} kWh > {tol})"
                )

            # ── CHECK 4: SOLAR AVAILABILITY ──
            # solar_used[h] <= effective_solar[h] + tolerance
            effective_solar = directives.effective_solar[h]
            if solar_used > effective_solar + tol:
                solar_err = solar_used - effective_solar
                if solar_err > max_error:
                    max_error = solar_err
                violations.append(
                    f"Hour {h}: solar availability violation (solar_used={solar_used:.4f} kWh "
                    f"exceeds effective_solar={effective_solar:.4f} kWh by {solar_err:.6f} kWh)"
                )

            # ── CHECK 5: BATTERY TRANSITION (CRITICAL INDEPENDENT REPLAY) ──
            # expected_energy[h] = previous_energy + charge[h] * charge_eff - discharge[h] / discharge_eff
            expected_energy = previous_energy + (charge * charge_eff) - (discharge / discharge_eff)
            transition_err = abs(energy_after - expected_energy)
            if transition_err > max_error:
                max_error = transition_err
            if transition_err > tol:
                violations.append(
                    f"Hour {h}: battery transition dynamics violation (reported={energy_after:.4f} kWh, "
                    f"expected={expected_energy:.4f} kWh, transition_err={transition_err:.6f} kWh > {tol})"
                )

            # ── CHECK 6: BATTERY CAPACITY LIMITS ──
            # energy_after[h] <= battery_capacity + tolerance
            if energy_after > battery.capacity_kwh + tol:
                cap_err = energy_after - battery.capacity_kwh
                if cap_err > max_error:
                    max_error = cap_err
                violations.append(
                    f"Hour {h}: battery capacity violation (energy_after={energy_after:.4f} kWh "
                    f"exceeds capacity={battery.capacity_kwh:.4f} kWh by {cap_err:.6f} kWh)"
                )

            # energy_after[h] >= 0 - tolerance
            if energy_after < -tol:
                below_zero_err = abs(energy_after)
                if below_zero_err > max_error:
                    max_error = below_zero_err
                violations.append(
                    f"Hour {h}: battery below zero violation (energy_after={energy_after:.4f} kWh < 0.0)"
                )

            # ── CHECK 7: BATTERY CHARGE RATE LIMIT ──
            if charge > battery.max_charge_kwh_per_hour + tol:
                chg_rate_err = charge - battery.max_charge_kwh_per_hour
                if chg_rate_err > max_error:
                    max_error = chg_rate_err
                violations.append(
                    f"Hour {h}: battery charge rate violation (charge={charge:.4f} kWh "
                    f"exceeds max_charge={battery.max_charge_kwh_per_hour:.4f} kWh by {chg_rate_err:.6f} kWh)"
                )

            # ── CHECK 8: BATTERY DISCHARGE RATE LIMIT ──
            if discharge > battery.max_discharge_kwh_per_hour + tol:
                dis_rate_err = discharge - battery.max_discharge_kwh_per_hour
                if dis_rate_err > max_error:
                    max_error = dis_rate_err
                violations.append(
                    f"Hour {h}: battery discharge rate violation (discharge={discharge:.4f} kWh "
                    f"exceeds max_discharge={battery.max_discharge_kwh_per_hour:.4f} kWh by {dis_rate_err:.6f} kWh)"
                )

            # ── CHECK 9: DIRECTIVE ENFORCEMENT ──
            # 9a. no_charge_window
            if directives.no_charge[h] and charge > tol:
                if charge > max_error:
                    max_error = charge
                violations.append(
                    f"Hour {h}: no_charge directive violation (charging={charge:.4f} kWh > {tol})"
                )

            # 9b. no_discharge_window
            if directives.no_discharge[h] and discharge > tol:
                if discharge > max_error:
                    max_error = discharge
                violations.append(
                    f"Hour {h}: no_discharge directive violation (discharging={discharge:.4f} kWh > {tol})"
                )

            # 9c. minimum_battery_reserve
            req_reserve = directives.min_reserve[h]
            if energy_after < req_reserve - tol:
                res_err = req_reserve - energy_after
                if res_err > max_error:
                    max_error = res_err
                violations.append(
                    f"Hour {h}: minimum_battery_reserve directive violation (energy_after={energy_after:.4f} kWh "
                    f"< min_reserve={req_reserve:.4f} kWh by {res_err:.6f} kWh)"
                )

            # 9d. max_grid_window
            if directives.max_grid[h] is not None:
                grid_ceiling = float(directives.max_grid[h])
                if grid > grid_ceiling + tol:
                    grid_err = grid - grid_ceiling
                    if grid_err > max_error:
                        max_error = grid_err
                    violations.append(
                        f"Hour {h}: max_grid directive violation (grid={grid:.4f} kWh "
                        f"exceeds max_grid={grid_ceiling:.4f} kWh by {grid_err:.6f} kWh)"
                    )

            # Accumulate cost and advance independent state
            recalculated_cost += grid * tariff
            previous_energy = energy_after

        # ── CHECK 10: END OF DAY BATTERY LEVEL ──
        if eod_neutral:
            final_energy = previous_energy
            initial_energy = battery.initial_energy_kwh
            eod_err = abs(final_energy - initial_energy)
            if eod_err > max_error:
                max_error = eod_err
            if eod_err > tol:
                violations.append(
                    f"End-of-day battery neutrality violation: final_energy={final_energy:.4f} kWh "
                    f"!= initial_energy={initial_energy:.4f} kWh (eod_err={eod_err:.6f} kWh > {tol})"
                )

        # ── CHECK 11: TOTAL COST RECALCULATION ──
        cost_err = abs(recalculated_cost - reported_total_cost)
        if cost_err > max_error:
            max_error = cost_err
        if cost_err > tol:
            violations.append(
                f"Objective cost recalculation violation: reported_cost={reported_total_cost:.4f} BDT "
                f"!= recalculated_cost={recalculated_cost:.4f} BDT (cost_err={cost_err:.6f} BDT > {tol})"
            )

        verified = len(violations) == 0
        if not verified:
            logger.warning(
                "DeterministicReplayValidator: schedule audit failed with %d violation(s). First: %s",
                len(violations),
                violations[0],
            )

        result = ReplayValidationResult(
            verified=verified,
            max_constraint_error=max_error,
            total_grid_cost_bdt=recalculated_cost,
            violations=violations,
            details={
                "hour_count": len(schedule),
                "tolerance": tol,
                "enforce_eod_neutrality": self.enforce_eod_neutrality,
                "recalculated_total_cost": recalculated_cost,
                "reported_total_cost": reported_total_cost,
            },
        )

        if strict and not verified:
            err_sample = "; ".join(violations[:3])
            raise ReplayValidationError(
                f"Deterministic replay validation failed with {len(violations)} violation(s): {err_sample}",
                details={"violations": violations, "max_constraint_error": max_error},
            )

        return result


def replay_validate_dispatch(
    opt_input: OptimizationInput,
    schedule: list[HourlyScheduleOutput] | list[Any],
    reported_total_cost: float,
    tolerance: float = DEFAULT_TOLERANCE,
    enforce_eod_neutrality: bool = True,
    strict: bool = False,
) -> ReplayValidationResult:
    """Convenience functional interface for deterministic schedule replay validation."""
    validator = DeterministicReplayValidator(
        default_tolerance=tolerance,
        enforce_eod_neutrality=enforce_eod_neutrality,
    )
    return validator.validate(
        opt_input=opt_input,
        schedule=schedule,
        reported_total_cost=reported_total_cost,
        tolerance=tolerance,
        strict=strict,
    )
