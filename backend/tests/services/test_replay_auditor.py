"""Unit tests for the independent deterministic replay validator.

Verifies independent schedule audit against:
1. A valid schedule passes validation
2. Intentionally invalid schedules fail validation:
   - energy imbalance
   - solar overuse
   - negative grid
   - negative charge
   - negative discharge
   - battery over-capacity
   - battery below zero
   - wrong battery transition
   - charge-rate violation
   - discharge-rate violation
   - no-charge violation
   - no_discharge violation
   - reserve violation
   - max-grid violation
   - final battery violation (neutrality broken)
   - incorrect objective
3. Protocol conformance (IReplayValidator)
4. Strict mode raising ReplayValidationError
5. Schedule length and ordering checks
6. Battery efficiency accounting
7. End-to-end validation with PuLpEnergyOptimizer output
"""

from __future__ import annotations

import copy

import pytest

from app.services.optimizer.models import (
    HOURS_IN_DAY,
    BatteryConfig,
    HourlyScheduleOutput,
    NormalizedDirective,
    OptimizationInput,
    ReplayValidationResult,
)
from app.services.optimizer.pulp_solver import PuLpEnergyOptimizer
from app.services.validation.compiler import compile_directives
from app.services.validation.deterministic_replay_validator import (
    DeterministicReplayValidator,
    replay_validate_dispatch,
)
from app.services.validation.exceptions import ReplayValidationError
from app.services.validation.interface import IReplayValidator


def make_baseline_fixture(
    demand_val: float = 25.0,
    solar_val: float = 0.0,
    tariff_val: float = 10.0,
    battery_cap: float = 100.0,
    initial_soc: float = 40.0,
    max_charge: float = 25.0,
    max_discharge: float = 25.0,
    charge_eff: float = 1.0,
    discharge_eff: float = 1.0,
    directives: list[NormalizedDirective] | None = None,
) -> tuple[OptimizationInput, list[HourlyScheduleOutput], float]:
    """Helper to generate a clean, baseline valid optimization input and matching schedule."""
    demand = [demand_val] * HOURS_IN_DAY
    base_solar = [solar_val] * HOURS_IN_DAY
    tariff = [tariff_val] * HOURS_IN_DAY

    battery = BatteryConfig(
        capacity_kwh=battery_cap,
        initial_energy_kwh=initial_soc,
        minimum_energy_kwh=10.0,
        max_charge_kwh_per_hour=max_charge,
        max_discharge_kwh_per_hour=max_discharge,
        charge_efficiency=charge_eff,
        discharge_efficiency=discharge_eff,
    )
    compiled = compile_directives(directives or [], base_solar, battery)
    opt_input = OptimizationInput.from_arrays(
        demand_kwh=demand,
        base_solar_kwh=base_solar,
        tariff_bdt_per_kwh=tariff,
        battery=battery,
        compiled_directives=compiled,
    )

    # Clean schedule: grid serves demand directly, battery sits idle at initial_soc
    schedule: list[HourlyScheduleOutput] = []
    total_cost = 0.0
    for h in range(HOURS_IN_DAY):
        g = demand[h]
        cost = g * tariff[h]
        total_cost += cost
        schedule.append(
            HourlyScheduleOutput(
                hour=h,
                demand_kwh=demand[h],
                effective_solar_kwh=compiled.effective_solar[h],
                solar_used_kwh=0.0,
                battery_charge_kwh=0.0,
                battery_discharge_kwh=0.0,
                battery_energy_after_kwh=initial_soc,
                grid_kwh=g,
                tariff_bdt_per_kwh=tariff[h],
                grid_cost_bdt=cost,
            )
        )

    return opt_input, schedule, total_cost


def clone_schedule_with_edit(
    schedule: list[HourlyScheduleOutput],
    hour: int,
    **updates: float,
) -> list[HourlyScheduleOutput]:
    """Return a deep copy of schedule with specific fields modified in one hour."""
    res: list[HourlyScheduleOutput] = []
    for row in schedule:
        if row.hour == hour:
            curr_dict = {
                "hour": row.hour,
                "demand_kwh": row.demand_kwh,
                "effective_solar_kwh": row.effective_solar_kwh,
                "solar_used_kwh": row.solar_used_kwh,
                "battery_charge_kwh": row.battery_charge_kwh,
                "battery_discharge_kwh": row.battery_discharge_kwh,
                "battery_energy_after_kwh": row.battery_energy_after_kwh,
                "grid_kwh": row.grid_kwh,
                "tariff_bdt_per_kwh": row.tariff_bdt_per_kwh,
                "grid_cost_bdt": row.grid_cost_bdt,
            }
            curr_dict.update(updates)
            res.append(HourlyScheduleOutput(**curr_dict))
        else:
            res.append(copy.copy(row))
    return res


# ─────────────────────────────────────────────────────────────────────────────
# 1. Interface Conformance & Valid Schedule Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_validator_implements_interface():
    """Verify DeterministicReplayValidator conforms to IReplayValidator protocol."""
    validator = DeterministicReplayValidator()
    assert isinstance(validator, IReplayValidator)


def test_baseline_valid_schedule_passes():
    """Verify that a standard balanced schedule passes all 11 replay checks."""
    opt_in, sched, cost = make_baseline_fixture()
    validator = DeterministicReplayValidator()
    result = validator.validate(opt_in, sched, cost)

    assert result.is_valid is True
    assert result.verified is True
    assert len(result.errors) == 0
    assert len(result.violations) == 0
    assert result.max_violation_magnitude < 1e-4
    assert abs(result.recalculated_total_cost - cost) < 1e-4


def test_convenience_function_matches():
    """Verify replay_validate_dispatch wrapper produces identical verification results."""
    opt_in, sched, cost = make_baseline_fixture()
    result = replay_validate_dispatch(opt_in, sched, cost)
    assert result.is_valid is True
    assert result.recalculated_total_cost == cost


# ─────────────────────────────────────────────────────────────────────────────
# 2. Required 16 Intentionally Invalid Schedule Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_failure_mode_1_energy_imbalance():
    """Check 3: Energy balance violation (grid + solar + discharge != demand + charge)."""
    opt_in, sched, cost = make_baseline_fixture()
    # Inject excess grid at hour 5 without demand increase
    bad_sched = clone_schedule_with_edit(sched, 5, grid_kwh=sched[5].grid_kwh + 3.0)

    validator = DeterministicReplayValidator()
    result = validator.validate(opt_in, bad_sched, cost)

    assert result.is_valid is False
    assert result.max_violation_magnitude >= 3.0 - 1e-4
    assert any("energy balance violation" in err for err in result.violations)


def test_failure_mode_2_solar_overuse():
    """Check 4: Solar used exceeds effective solar available."""
    opt_in, sched, cost = make_baseline_fixture(solar_val=10.0)
    # Effective solar is 10.0, optimizer claims to use 15.0 at hour 11
    bad_sched = clone_schedule_with_edit(
        sched,
        11,
        solar_used_kwh=15.0,
        grid_kwh=sched[11].grid_kwh - 15.0,  # preserve balance to isolate solar check
    )
    reported_cost = cost - (15.0 * 10.0)

    validator = DeterministicReplayValidator()
    result = validator.validate(opt_in, bad_sched, reported_cost)

    assert result.is_valid is False
    assert result.max_violation_magnitude >= 5.0 - 1e-4
    assert any("solar availability violation" in err for err in result.violations)


def test_failure_mode_3_negative_grid():
    """Check 2: Negative grid import rejected."""
    opt_in, sched, cost = make_baseline_fixture()
    bad_sched = clone_schedule_with_edit(sched, 4, grid_kwh=-2.5)

    validator = DeterministicReplayValidator()
    result = validator.validate(opt_in, bad_sched, cost)

    assert result.is_valid is False
    assert result.max_violation_magnitude >= 2.5 - 1e-4
    assert any("negative value in grid" in err for err in result.violations)


def test_failure_mode_4_negative_charge():
    """Check 2: Negative battery charge rejected."""
    opt_in, sched, cost = make_baseline_fixture()
    bad_sched = clone_schedule_with_edit(sched, 8, battery_charge_kwh=-1.5)

    validator = DeterministicReplayValidator()
    result = validator.validate(opt_in, bad_sched, cost)

    assert result.is_valid is False
    assert result.max_violation_magnitude >= 1.5 - 1e-4
    assert any("negative value in battery_charge" in err for err in result.violations)


def test_failure_mode_5_negative_discharge():
    """Check 2: Negative battery discharge rejected."""
    opt_in, sched, cost = make_baseline_fixture()
    bad_sched = clone_schedule_with_edit(sched, 14, battery_discharge_kwh=-3.0)

    validator = DeterministicReplayValidator()
    result = validator.validate(opt_in, bad_sched, cost)

    assert result.is_valid is False
    assert result.max_violation_magnitude >= 3.0 - 1e-4
    assert any("negative value in battery_discharge" in err for err in result.violations)


def test_failure_mode_6_battery_over_capacity():
    """Check 6: Battery state of charge exceeds physical capacity."""
    opt_in, sched, cost = make_baseline_fixture(battery_cap=100.0)
    # Set battery state to 110.0 kWh (exceeds 100.0)
    bad_sched = clone_schedule_with_edit(sched, 9, battery_energy_after_kwh=110.0)

    validator = DeterministicReplayValidator()
    result = validator.validate(opt_in, bad_sched, cost)

    assert result.is_valid is False
    assert result.max_violation_magnitude >= 10.0 - 1e-4
    assert any("battery capacity violation" in err for err in result.violations)


def test_failure_mode_7_battery_below_zero():
    """Check 6: Battery state of charge drops below zero."""
    opt_in, sched, cost = make_baseline_fixture()
    bad_sched = clone_schedule_with_edit(sched, 12, battery_energy_after_kwh=-2.0)

    validator = DeterministicReplayValidator()
    result = validator.validate(opt_in, bad_sched, cost)

    assert result.is_valid is False
    assert result.max_violation_magnitude >= 2.0 - 1e-4
    assert any("battery below zero violation" in err for err in result.violations)


def test_failure_mode_8_wrong_battery_transition():
    """Check 5: Battery state jump inconsistent with charge/discharge dynamics."""
    opt_in, sched, cost = make_baseline_fixture(initial_soc=40.0)
    # At hour 3, energy is reported as 55.0 without any charging (charge=0, discharge=0)
    bad_sched = clone_schedule_with_edit(sched, 3, battery_energy_after_kwh=55.0)

    validator = DeterministicReplayValidator()
    result = validator.validate(opt_in, bad_sched, cost)

    assert result.is_valid is False
    assert result.max_violation_magnitude >= 15.0 - 1e-4
    assert any("battery transition dynamics violation" in err for err in result.violations)


def test_failure_mode_9_charge_rate_violation():
    """Check 7: Charge rate exceeds inverter maximum limit."""
    opt_in, sched, cost = make_baseline_fixture(max_charge=20.0)
    # Charge rate is 28.0 (exceeds max 20.0)
    bad_sched = clone_schedule_with_edit(
        sched,
        2,
        battery_charge_kwh=28.0,
        battery_energy_after_kwh=68.0,  # maintain dynamics from 40 to isolate rate check
        grid_kwh=sched[2].grid_kwh + 28.0,  # maintain balance
    )
    reported_cost = cost + (28.0 * 10.0)

    validator = DeterministicReplayValidator(enforce_eod_neutrality=False)
    result = validator.validate(opt_in, bad_sched, reported_cost)

    assert result.is_valid is False
    assert result.max_violation_magnitude >= 8.0 - 1e-4
    assert any("battery charge rate violation" in err for err in result.violations)


def test_failure_mode_10_discharge_rate_violation():
    """Check 8: Discharge rate exceeds inverter maximum limit."""
    opt_in, sched, cost = make_baseline_fixture(max_discharge=20.0)
    # Discharge rate is 27.0 (exceeds max 20.0)
    bad_sched = clone_schedule_with_edit(
        sched,
        18,
        battery_discharge_kwh=27.0,
        battery_energy_after_kwh=13.0,  # maintain dynamics from 40 to isolate rate check
        grid_kwh=sched[18].grid_kwh - 27.0,  # maintain balance
    )
    reported_cost = cost - (27.0 * 10.0)

    validator = DeterministicReplayValidator(enforce_eod_neutrality=False)
    result = validator.validate(opt_in, bad_sched, reported_cost)

    assert result.is_valid is False
    assert result.max_violation_magnitude >= 7.0 - 1e-4
    assert any("battery discharge rate violation" in err for err in result.violations)


def test_failure_mode_11_no_charge_violation():
    """Check 9a: Charging occurs during a no_charge_window."""
    directive = NormalizedDirective(
        note_index=0,
        directive_type="no_charge_window",
        hours=[10, 11, 12],
    )
    opt_in, sched, cost = make_baseline_fixture(directives=[directive])
    # Schedule charges 6.0 kWh at hour 11 despite no_charge directive
    bad_sched = clone_schedule_with_edit(sched, 11, battery_charge_kwh=6.0)

    validator = DeterministicReplayValidator()
    result = validator.validate(opt_in, bad_sched, cost)

    assert result.is_valid is False
    assert result.max_violation_magnitude >= 6.0 - 1e-4
    assert any("no_charge directive violation" in err for err in result.violations)


def test_failure_mode_12_no_discharge_violation():
    """Check 9b: Discharging occurs during a no_discharge_window."""
    directive = NormalizedDirective(
        note_index=0,
        directive_type="no_discharge_window",
        hours=[17, 18, 19],
    )
    opt_in, sched, cost = make_baseline_fixture(directives=[directive])
    # Schedule discharges 8.0 kWh at hour 18 despite no_discharge directive
    bad_sched = clone_schedule_with_edit(sched, 18, battery_discharge_kwh=8.0)

    validator = DeterministicReplayValidator()
    result = validator.validate(opt_in, bad_sched, cost)

    assert result.is_valid is False
    assert result.max_violation_magnitude >= 8.0 - 1e-4
    assert any("no_discharge directive violation" in err for err in result.violations)


def test_failure_mode_13_reserve_violation():
    """Check 9c: Battery drops below mandatory minimum_battery_reserve."""
    directive = NormalizedDirective(
        note_index=0,
        directive_type="minimum_battery_reserve",
        hours=[14, 15, 16],
        minimum_energy_kwh=50.0,
    )
    opt_in, sched, cost = make_baseline_fixture(initial_soc=40.0, directives=[directive])
    # Baseline schedule has energy=40.0, but reserve requires 50.0 at hours 14, 15, 16
    validator = DeterministicReplayValidator()
    result = validator.validate(opt_in, sched, cost)

    assert result.is_valid is False
    assert result.max_violation_magnitude >= 10.0 - 1e-4
    assert any("minimum_battery_reserve directive violation" in err for err in result.violations)


def test_failure_mode_14_max_grid_violation():
    """Check 9d: Grid import exceeds max_grid_window directive limit."""
    directive = NormalizedDirective(
        note_index=0,
        directive_type="max_grid_window",
        hours=[7, 8],
        max_grid_kwh=15.0,
    )
    opt_in, sched, cost = make_baseline_fixture(demand_val=25.0, directives=[directive])
    # Schedule imports 25.0 kWh grid at hour 7, but ceiling is 15.0 kWh
    validator = DeterministicReplayValidator()
    result = validator.validate(opt_in, sched, cost)

    assert result.is_valid is False
    assert result.max_violation_magnitude >= 10.0 - 1e-4
    assert any("max_grid directive violation" in err for err in result.violations)


def test_failure_mode_15_final_battery_violation():
    """Check 10: End-of-day battery neutrality broken."""
    opt_in, sched, cost = make_baseline_fixture(initial_soc=40.0)
    # Hour 23 battery energy is 65.0 instead of initial 40.0
    bad_sched = clone_schedule_with_edit(sched, 23, battery_energy_after_kwh=65.0)

    validator = DeterministicReplayValidator(enforce_eod_neutrality=True)
    result = validator.validate(opt_in, bad_sched, cost)

    assert result.is_valid is False
    assert result.max_violation_magnitude >= 25.0 - 1e-4
    assert any("End-of-day battery neutrality violation" in err for err in result.violations)


def test_failure_mode_16_incorrect_objective():
    """Check 11: Reported total cost does not reconcile with grid * tariff."""
    opt_in, sched, cost = make_baseline_fixture()
    reported_cost = cost + 150.0  # discrepancy

    validator = DeterministicReplayValidator()
    result = validator.validate(opt_in, sched, reported_cost)

    assert result.is_valid is False
    assert result.max_violation_magnitude >= 150.0 - 1e-4
    assert any("Objective cost recalculation violation" in err for err in result.violations)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Schedule Length, Ordering, Strict Mode, and Efficiency Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_wrong_schedule_length_truncated():
    """Check 1: Less than 24 hours in candidate schedule fails."""
    opt_in, sched, cost = make_baseline_fixture()
    truncated_sched = sched[:20]

    validator = DeterministicReplayValidator()
    result = validator.validate(opt_in, truncated_sched, cost)

    assert result.is_valid is False
    assert any("Schedule length violation" in err for err in result.violations)


def test_wrong_schedule_length_excess():
    """Check 1: More than 24 hours in candidate schedule fails."""
    opt_in, sched, cost = make_baseline_fixture()
    excess_sched = sched + [sched[0]]

    validator = DeterministicReplayValidator()
    result = validator.validate(opt_in, excess_sched, cost)

    assert result.is_valid is False
    assert any("Schedule length violation" in err for err in result.violations)


def test_non_sequential_hour_ordering():
    """Check 1: Hours not in 0..23 sequence fails."""
    opt_in, sched, cost = make_baseline_fixture()
    swapped = copy.copy(sched)
    # Swap hour 2 and hour 3
    swapped[2], swapped[3] = swapped[3], swapped[2]

    validator = DeterministicReplayValidator()
    result = validator.validate(opt_in, swapped, cost)

    assert result.is_valid is False
    assert any("Schedule hour sequence violation" in err for err in result.violations)


def test_strict_mode_raises_exception():
    """Strict mode immediately raises ReplayValidationError on violation."""
    opt_in, sched, cost = make_baseline_fixture()
    bad_sched = clone_schedule_with_edit(sched, 5, grid_kwh=-5.0)

    validator = DeterministicReplayValidator()
    with pytest.raises(ReplayValidationError) as exc_info:
        validator.validate(opt_in, bad_sched, cost, strict=True)

    assert "Deterministic replay validation failed" in str(exc_info.value)
    assert exc_info.value.details["max_constraint_error"] >= 5.0 - 1e-4


def test_strict_mode_length_violation_raises():
    """Strict mode raises ReplayValidationError on wrong length."""
    opt_in, sched, cost = make_baseline_fixture()
    validator = DeterministicReplayValidator()

    with pytest.raises(ReplayValidationError) as exc_info:
        validator.validate(opt_in, sched[:10], cost, strict=True)

    assert "Schedule length violation" in str(exc_info.value)


def test_battery_round_trip_efficiency_transition():
    """Check 5: Independent state replay respects charge & discharge efficiency factors."""
    charge_eff = 0.90
    discharge_eff = 0.80
    opt_in, sched, cost = make_baseline_fixture(
        initial_soc=30.0,
        charge_eff=charge_eff,
        discharge_eff=discharge_eff,
    )

    # In hour 1: charge 10 kWh. Expected new energy = 30 + (10 * 0.90) = 39.0 kWh
    # In hour 2: discharge 8 kWh. Expected new energy = 39 - (8 / 0.80) = 29.0 kWh
    edit_h = clone_schedule_with_edit(
        sched,
        1,
        battery_charge_kwh=10.0,
        battery_energy_after_kwh=39.0,
        grid_kwh=sched[1].grid_kwh + 10.0,
    )
    edit_h = clone_schedule_with_edit(
        edit_h,
        2,
        battery_discharge_kwh=8.0,
        battery_energy_after_kwh=29.0,
        grid_kwh=sched[2].grid_kwh - 8.0,
    )
    # Subsequent hours idle at 29.0 kWh
    for h in range(3, HOURS_IN_DAY):
        edit_h = clone_schedule_with_edit(edit_h, h, battery_energy_after_kwh=29.0)

    validator = DeterministicReplayValidator(enforce_eod_neutrality=False)
    # Total grid cost adjusted for extra charging / discharging:
    cost_adjusted = cost + (10.0 * 10.0) - (8.0 * 10.0)
    result = validator.validate(opt_in, edit_h, cost_adjusted)

    # Transition dynamics should match correctly with efficiency included
    assert not any("battery transition dynamics violation" in err for err in result.violations)


# ─────────────────────────────────────────────────────────────────────────────
# 4. End-to-End Integration with PuLp Optimizer
# ─────────────────────────────────────────────────────────────────────────────


def test_pulp_optimizer_output_passes_deterministic_replay():
    """Solve a complex dispatch scenario with PuLp and verify it passes DeterministicReplayValidator."""
    demand = [20.0] * 6 + [50.0] * 6 + [30.0] * 6 + [15.0] * 6
    solar = [0.0] * 6 + [40.0] * 6 + [20.0] * 6 + [0.0] * 6
    tariff = [5.0] * 6 + [15.0] * 6 + [10.0] * 6 + [5.0] * 6

    directives = [
        NormalizedDirective(
            note_index=0, directive_type="solar_reduction", hours=[8, 9], factor=0.8
        ),
        NormalizedDirective(
            note_index=1,
            directive_type="minimum_battery_reserve",
            hours=[10, 11],
            minimum_energy_kwh=25.0,
        ),
        NormalizedDirective(note_index=2, directive_type="no_charge_window", hours=[12, 13]),
        NormalizedDirective(
            note_index=3, directive_type="max_grid_window", hours=[14, 15], max_grid_kwh=40.0
        ),
    ]

    battery = BatteryConfig(
        capacity_kwh=120.0,
        initial_energy_kwh=35.0,
        minimum_energy_kwh=10.0,
        max_charge_kwh_per_hour=30.0,
        max_discharge_kwh_per_hour=30.0,
    )

    compiled = compile_directives(directives, solar, battery)
    opt_in = OptimizationInput.from_arrays(
        demand_kwh=demand,
        base_solar_kwh=solar,
        tariff_bdt_per_kwh=tariff,
        battery=battery,
        compiled_directives=compiled,
    )

    # Solve with PuLp optimizer
    solver = PuLpEnergyOptimizer()
    opt_res = solver.solve(opt_in)
    assert opt_res.is_optimal is True

    # Audit candidate schedule with independent replay validator
    validator = DeterministicReplayValidator(default_tolerance=1e-4, enforce_eod_neutrality=True)
    audit_res: ReplayValidationResult = validator.validate(
        opt_input=opt_in,
        schedule=opt_res.schedule,
        reported_total_cost=opt_res.total_grid_cost_bdt,
    )

    assert audit_res.is_valid is True
    assert audit_res.verified is True
    assert len(audit_res.violations) == 0
    assert audit_res.max_violation_magnitude < 1e-4
    assert abs(audit_res.recalculated_total_cost - opt_res.total_grid_cost_bdt) < 1e-4
