"""Comprehensive Workstream Test Pass.

Covers all 7 verification categories:
A. Basic optimization
   - no battery
   - battery available
   - no solar
   - abundant solar
   - constant tariffs
   - varying tariffs
   - zero demand
   - normal demand
B. Battery
   - charging
   - discharging
   - capacity limit
   - charge-rate limit
   - discharge-rate limit
   - initial energy
   - final energy neutrality
   - charge efficiency
   - discharge efficiency
C. Solar
   - zero solar
   - solar less than demand
   - solar greater than demand
   - solar reduction factor 1
   - solar reduction factor 0
   - multiple solar reductions
D. Directives
   - no_op
   - no-charge
   - no-discharge
   - minimum reserve
   - max grid
   - overlapping windows
   - multiple directives affecting the same hour
   - multiple reserve directives
   - multiple max-grid directives
E. Infeasibility
   - impossible reserve
   - impossible max-grid
   - impossible battery requirements
   - insufficient total energy
   - contradictory constraints
F. Numerical validation
   - tiny floating-point differences
   - objective recalculation
   - battery state replay
   - energy balance tolerance
G. Validator attack cases
   - solver-reported valid schedule with modified grid value
   - modified battery state
   - solar value slightly above availability
   - charge slightly above maximum
   - reserve violation
   - final battery mismatch
"""

from __future__ import annotations

import copy

import pytest

from app.services.optimizer.engine import (
    OptimizationEngine,
    OptimizationPipelineInput,
    optimize_and_validate,
)
from app.services.optimizer.models import (
    HOURS_IN_DAY,
    BatteryConfig,
    HourlyScheduleOutput,
    NormalizedDirective,
    OptimizationInput,
    SolverStatus,
)
from app.services.validation.compiler import compile_directives
from app.services.validation.deterministic_replay_validator import DeterministicReplayValidator


def make_test_scenario(
    demand_val: float = 20.0,
    solar_val: float = 0.0,
    tariff_val: float = 10.0,
    battery_cap: float = 100.0,
    initial_soc: float = 40.0,
    min_soc: float = 10.0,
    max_charge: float = 25.0,
    max_discharge: float = 25.0,
    charge_eff: float = 1.0,
    discharge_eff: float = 1.0,
    directives: list[NormalizedDirective] | None = None,
) -> OptimizationPipelineInput:
    """Construct an OptimizationPipelineInput with uniform defaults."""
    demand = (
        [demand_val] * HOURS_IN_DAY if isinstance(demand_val, (int, float)) else list(demand_val)
    )
    solar = [solar_val] * HOURS_IN_DAY if isinstance(solar_val, (int, float)) else list(solar_val)
    tariff = (
        [tariff_val] * HOURS_IN_DAY if isinstance(tariff_val, (int, float)) else list(tariff_val)
    )

    battery = BatteryConfig(
        capacity_kwh=battery_cap,
        initial_energy_kwh=initial_soc,
        minimum_energy_kwh=min_soc,
        max_charge_kwh_per_hour=max_charge,
        max_discharge_kwh_per_hour=max_discharge,
        charge_efficiency=charge_eff,
        discharge_efficiency=discharge_eff,
    )

    return OptimizationPipelineInput.from_arrays(
        demand_kwh=demand,
        base_solar_kwh=solar,
        tariff_bdt_per_kwh=tariff,
        battery=battery,
        directives=directives or [],
    )


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY A: Basic Optimization
# ─────────────────────────────────────────────────────────────────────────────


class TestCategoryA_BasicOptimization:
    """Verify primary optimization scenarios under clean baseline conditions."""

    def test_no_battery(self) -> None:
        """No battery available (charge/discharge rates set to 0)."""
        p_in = make_test_scenario(
            demand_val=20.0,
            solar_val=0.0,
            tariff_val=10.0,
            battery_cap=1.0,
            initial_soc=0.0,
            min_soc=0.0,
            max_charge=0.0,
            max_discharge=0.0,
        )
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        assert res.total_grid_kwh == pytest.approx(480.0, abs=1e-4)
        assert res.total_grid_cost_bdt == pytest.approx(4800.0, abs=1e-4)
        for h in res.schedule:
            assert h.grid_kwh == pytest.approx(20.0, abs=1e-4)
            assert h.battery_charge_kwh == pytest.approx(0.0, abs=1e-4)
            assert h.battery_discharge_kwh == pytest.approx(0.0, abs=1e-4)

    def test_battery_available(self) -> None:
        """Battery available and actively utilized across varying tariffs."""
        tariff = [5.0] * 12 + [20.0] * 12
        p_in = make_test_scenario(
            demand_val=25.0,
            solar_val=0.0,
            tariff_val=tariff,
            battery_cap=100.0,
            initial_soc=30.0,
        )
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        assert res.is_valid is True
        # Battery should charge during cheap hours (0..11) and discharge during expensive hours (12..23)
        total_charge = sum(h.battery_charge_kwh for h in res.schedule[:12])
        total_discharge = sum(h.battery_discharge_kwh for h in res.schedule[12:])
        assert total_charge > 0.0
        assert total_discharge > 0.0

    def test_no_solar(self) -> None:
        """Zero solar generation scenario."""
        p_in = make_test_scenario(demand_val=15.0, solar_val=0.0)
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        for h in res.schedule:
            assert h.effective_solar_kwh == pytest.approx(0.0, abs=1e-4)
            assert h.solar_used_kwh == pytest.approx(0.0, abs=1e-4)

    def test_abundant_solar(self) -> None:
        """Abundant solar covers all daytime demand with excess charging battery."""
        solar = [0.0] * 6 + [60.0] * 12 + [0.0] * 6
        p_in = make_test_scenario(
            demand_val=20.0, solar_val=solar, battery_cap=150.0, initial_soc=20.0
        )
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        # During peak solar hours, grid import should drop to 0
        for h in res.schedule[6:18]:
            assert h.grid_kwh == pytest.approx(0.0, abs=1e-4)
            assert h.solar_used_kwh == pytest.approx(20.0 + h.battery_charge_kwh, abs=1e-4)

    def test_constant_tariffs(self) -> None:
        """Constant tariffs produce a valid flat dispatch without unneeded battery cycling."""
        p_in = make_test_scenario(demand_val=20.0, tariff_val=12.0)
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        assert res.total_grid_cost_bdt == pytest.approx(24 * 20.0 * 12.0, abs=1e-4)

    def test_varying_tariffs(self) -> None:
        """Varying tariffs shift grid consumption from expensive to cheap hours."""
        tariff = [6.0 if h < 12 else 18.0 for h in range(HOURS_IN_DAY)]
        p_in = make_test_scenario(demand_val=20.0, tariff_val=tariff)
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        avg_cost_without_battery = (12 * 20 * 6.0) + (12 * 20 * 18.0)  # 1440 + 4320 = 5760
        assert res.total_grid_cost_bdt < avg_cost_without_battery

    def test_zero_demand(self) -> None:
        """Zero demand results in zero grid consumption and zero cost."""
        p_in = make_test_scenario(demand_val=0.0, solar_val=0.0)
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        assert res.total_grid_kwh == pytest.approx(0.0, abs=1e-4)
        assert res.total_grid_cost_bdt == pytest.approx(0.0, abs=1e-4)

    def test_normal_demand(self) -> None:
        """Normal dynamic demand vector solved optimally and verified."""
        demand = [15.0 + (h % 10) for h in range(HOURS_IN_DAY)]
        p_in = make_test_scenario(demand_val=demand, tariff_val=10.0)
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        assert res.total_grid_kwh == pytest.approx(sum(demand), abs=1e-4)


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY B: Battery
# ─────────────────────────────────────────────────────────────────────────────


class TestCategoryB_Battery:
    """Verify battery physical laws, operational bounds, and dynamics."""

    def test_charging_behavior(self) -> None:
        """Verify charging increases battery state of charge."""
        solar = [0.0] * 6 + [50.0] * 6 + [0.0] * 12
        p_in = make_test_scenario(demand_val=10.0, solar_val=solar, initial_soc=20.0)
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        max_soc = max(h.battery_energy_after_kwh for h in res.schedule)
        assert max_soc > 20.0

    def test_discharging_behavior(self) -> None:
        """Verify discharging decreases battery state of charge to serve demand."""
        tariff = [10.0] * 18 + [30.0] * 6
        p_in = make_test_scenario(demand_val=20.0, tariff_val=tariff, initial_soc=60.0)
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        # Battery should discharge during hours 18..23
        discharged = sum(h.battery_discharge_kwh for h in res.schedule[18:])
        assert discharged > 0.0

    def test_capacity_limit(self) -> None:
        """Battery state of charge never exceeds physical capacity."""
        solar = [100.0] * HOURS_IN_DAY
        capacity = 80.0
        p_in = make_test_scenario(
            demand_val=5.0, solar_val=solar, battery_cap=capacity, initial_soc=40.0
        )
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        for h in res.schedule:
            assert h.battery_energy_after_kwh <= capacity + 1e-4

    def test_charge_rate_limit(self) -> None:
        """Hourly charging never exceeds inverter max charge rate."""
        solar = [100.0] * HOURS_IN_DAY
        max_chg = 15.0
        p_in = make_test_scenario(demand_val=5.0, solar_val=solar, max_charge=max_chg)
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        for h in res.schedule:
            assert h.battery_charge_kwh <= max_chg + 1e-4

    def test_discharge_rate_limit(self) -> None:
        """Hourly discharging never exceeds inverter max discharge rate."""
        tariff = [5.0] * 12 + [50.0] * 12
        max_dis = 12.0
        p_in = make_test_scenario(
            demand_val=30.0, tariff_val=tariff, initial_soc=80.0, max_discharge=max_dis
        )
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        for h in res.schedule:
            assert h.battery_discharge_kwh <= max_dis + 1e-4

    def test_initial_energy(self) -> None:
        """Solver starts simulation precisely at specified initial energy."""
        init_energy = 47.5
        p_in = make_test_scenario(initial_soc=init_energy)
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        # First hour transition: energy[0] == initial_soc + charge[0] - discharge[0]
        row0 = res.schedule[0]
        expected_soc0 = init_energy + row0.battery_charge_kwh - row0.battery_discharge_kwh
        assert row0.battery_energy_after_kwh == pytest.approx(expected_soc0, abs=1e-4)

    def test_final_energy_neutrality(self) -> None:
        """Final hour battery energy strictly equals initial energy."""
        init_energy = 55.0
        tariff = [5.0] * 12 + [25.0] * 12
        p_in = make_test_scenario(tariff_val=tariff, initial_soc=init_energy)
        res = optimize_and_validate(p_in, enforce_eod_neutrality=True)
        assert res.is_success is True
        assert res.schedule[23].battery_energy_after_kwh == pytest.approx(init_energy, abs=1e-4)

    def test_charge_efficiency(self) -> None:
        """Charge efficiency < 1.0 properly scales energy stored."""
        p_in = make_test_scenario(
            demand_val=10.0,
            tariff_val=[5.0] * 12 + [25.0] * 12,
            initial_soc=30.0,
            charge_eff=0.85,
        )
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        assert res.is_valid is True

    def test_discharge_efficiency(self) -> None:
        """Discharge efficiency < 1.0 properly scales energy consumed from battery."""
        p_in = make_test_scenario(
            demand_val=10.0,
            tariff_val=[5.0] * 12 + [25.0] * 12,
            initial_soc=60.0,
            discharge_eff=0.85,
        )
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        assert res.is_valid is True


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY C: Solar
# ─────────────────────────────────────────────────────────────────────────────


class TestCategoryC_Solar:
    """Verify solar availability, consumption, curtailment, and reduction factors."""

    def test_zero_solar(self) -> None:
        """Zero solar scenario."""
        p_in = make_test_scenario(solar_val=0.0)
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        assert all(h.solar_used_kwh == 0.0 for h in res.schedule)

    def test_solar_less_than_demand(self) -> None:
        """Solar generation is less than demand: all available solar is utilized."""
        solar = [8.0] * HOURS_IN_DAY
        p_in = make_test_scenario(demand_val=20.0, solar_val=solar)
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        for h in res.schedule:
            assert h.solar_used_kwh == pytest.approx(8.0, abs=1e-4)
            assert h.grid_kwh + h.solar_used_kwh + h.battery_discharge_kwh == pytest.approx(
                h.demand_kwh + h.battery_charge_kwh, abs=1e-4
            )

    def test_solar_greater_than_demand(self) -> None:
        """Solar exceeds demand: demand served, battery charged, excess curtailed."""
        solar = [45.0] * HOURS_IN_DAY
        p_in = make_test_scenario(demand_val=15.0, solar_val=solar, battery_cap=50.0)
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        for h in res.schedule:
            assert h.grid_kwh == pytest.approx(0.0, abs=1e-4)
            assert h.solar_used_kwh <= 45.0 + 1e-4

    def test_solar_reduction_factor_1(self) -> None:
        """Solar reduction with factor 1.0 preserves 100% of generation."""
        directive = NormalizedDirective(
            note_index=0, directive_type="solar_reduction", hours=[10, 11], factor=1.0
        )
        solar = [0.0] * 10 + [40.0, 40.0] + [0.0] * 12
        p_in = make_test_scenario(solar_val=solar, directives=[directive])
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        assert res.schedule[10].effective_solar_kwh == pytest.approx(40.0, abs=1e-4)
        assert res.schedule[11].effective_solar_kwh == pytest.approx(40.0, abs=1e-4)

    def test_solar_reduction_factor_0(self) -> None:
        """Solar reduction with factor 0.0 wipes out all generation."""
        directive = NormalizedDirective(
            note_index=0, directive_type="solar_reduction", hours=[12], factor=0.0
        )
        solar = [0.0] * 12 + [50.0] + [0.0] * 11
        p_in = make_test_scenario(solar_val=solar, directives=[directive])
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        assert res.schedule[12].effective_solar_kwh == pytest.approx(0.0, abs=1e-4)
        assert res.schedule[12].solar_used_kwh == pytest.approx(0.0, abs=1e-4)

    def test_multiple_solar_reductions_multiplicative(self) -> None:
        """Multiple overlapping solar reductions multiply factors (e.g. 0.5 * 0.4 = 0.2)."""
        d1 = NormalizedDirective(
            note_index=0, directive_type="solar_reduction", hours=[11], factor=0.5
        )
        d2 = NormalizedDirective(
            note_index=1, directive_type="solar_reduction", hours=[11], factor=0.4
        )
        solar = [0.0] * 11 + [100.0] + [0.0] * 12
        p_in = make_test_scenario(solar_val=solar, directives=[d1, d2])
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        # 100 * 0.5 * 0.4 = 20.0
        assert res.schedule[11].effective_solar_kwh == pytest.approx(20.0, abs=1e-4)
        assert res.schedule[11].solar_used_kwh <= 20.0 + 1e-4


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY D: Directives
# ─────────────────────────────────────────────────────────────────────────────


class TestCategoryD_Directives:
    """Verify directive guardrails, compilation, and hourly constraint enforcement."""

    def test_directive_no_op(self) -> None:
        """no_op directive does not alter physical dispatch."""
        directive = NormalizedDirective(
            note_index=0, directive_type="no_op", hours=[], applies=False
        )
        p_in = make_test_scenario(demand_val=20.0, directives=[directive])
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        assert res.total_grid_kwh == pytest.approx(480.0, abs=1e-4)

    def test_directive_no_charge(self) -> None:
        """no_charge_window strictly locks charging to zero."""
        directive = NormalizedDirective(
            note_index=0, directive_type="no_charge_window", hours=[8, 9, 10]
        )
        solar = [0.0] * 8 + [50.0, 50.0, 50.0] + [0.0] * 13
        p_in = make_test_scenario(demand_val=10.0, solar_val=solar, directives=[directive])
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        for h in [8, 9, 10]:
            assert res.schedule[h].battery_charge_kwh <= 1e-4

    def test_directive_no_discharge(self) -> None:
        """no_discharge_window strictly locks discharging to zero."""
        directive = NormalizedDirective(
            note_index=0, directive_type="no_discharge_window", hours=[18, 19]
        )
        tariff = [5.0] * 18 + [50.0, 50.0] + [5.0] * 4
        p_in = make_test_scenario(
            demand_val=20.0, tariff_val=tariff, initial_soc=60.0, directives=[directive]
        )
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        for h in [18, 19]:
            assert res.schedule[h].battery_discharge_kwh <= 1e-4

    def test_directive_minimum_reserve(self) -> None:
        """minimum_battery_reserve guarantees state of charge floor."""
        directive = NormalizedDirective(
            note_index=0,
            directive_type="minimum_battery_reserve",
            hours=[15, 16],
            minimum_energy_kwh=45.0,
        )
        p_in = make_test_scenario(initial_soc=30.0, directives=[directive])
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        for h in [15, 16]:
            assert res.schedule[h].battery_energy_after_kwh >= 45.0 - 1e-4

    def test_directive_max_grid(self) -> None:
        """max_grid_window limits grid import to ceiling."""
        directive = NormalizedDirective(
            note_index=0, directive_type="max_grid_window", hours=[12, 13], max_grid_kwh=10.0
        )
        solar = [0.0] * 12 + [20.0, 20.0] + [0.0] * 10
        p_in = make_test_scenario(demand_val=25.0, solar_val=solar, directives=[directive])
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        for h in [12, 13]:
            assert res.schedule[h].grid_kwh <= 10.0 + 1e-4

    def test_overlapping_windows(self) -> None:
        """Overlapping directive windows are correctly unified across hours."""
        d1 = NormalizedDirective(note_index=0, directive_type="no_charge_window", hours=[8, 9, 10])
        d2 = NormalizedDirective(
            note_index=1, directive_type="no_charge_window", hours=[10, 11, 12]
        )
        p_in = make_test_scenario(directives=[d1, d2])
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        for h in [8, 9, 10, 11, 12]:
            assert res.schedule[h].battery_charge_kwh <= 1e-4

    def test_multiple_directives_same_hour(self) -> None:
        """Multiple distinct directive types applied to the same hour."""
        d1 = NormalizedDirective(
            note_index=0, directive_type="solar_reduction", hours=[14], factor=0.8
        )
        d2 = NormalizedDirective(
            note_index=1, directive_type="max_grid_window", hours=[14], max_grid_kwh=30.0
        )
        d3 = NormalizedDirective(note_index=2, directive_type="no_charge_window", hours=[14])
        solar = [0.0] * 14 + [25.0] + [0.0] * 9
        p_in = make_test_scenario(demand_val=20.0, solar_val=solar, directives=[d1, d2, d3])
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        row = res.schedule[14]
        assert row.effective_solar_kwh == pytest.approx(20.0, abs=1e-4)
        assert row.grid_kwh <= 30.0 + 1e-4
        assert row.battery_charge_kwh <= 1e-4

    def test_multiple_reserve_directives_highest_wins(self) -> None:
        """Multiple reserve directives on the same hour: highest reserve takes precedence."""
        d1 = NormalizedDirective(
            note_index=0,
            directive_type="minimum_battery_reserve",
            hours=[15],
            minimum_energy_kwh=35.0,
        )
        d2 = NormalizedDirective(
            note_index=1,
            directive_type="minimum_battery_reserve",
            hours=[15],
            minimum_energy_kwh=55.0,
        )
        p_in = make_test_scenario(initial_soc=20.0, directives=[d1, d2])
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        assert res.schedule[15].battery_energy_after_kwh >= 55.0 - 1e-4

    def test_multiple_max_grid_directives_lowest_ceiling_wins(self) -> None:
        """Multiple max_grid directives on the same hour: lowest ceiling takes precedence."""
        d1 = NormalizedDirective(
            note_index=0, directive_type="max_grid_window", hours=[10], max_grid_kwh=40.0
        )
        d2 = NormalizedDirective(
            note_index=1, directive_type="max_grid_window", hours=[10], max_grid_kwh=20.0
        )
        solar = [0.0] * 10 + [20.0] + [0.0] * 13
        p_in = make_test_scenario(demand_val=30.0, solar_val=solar, directives=[d1, d2])
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        assert res.schedule[10].grid_kwh <= 20.0 + 1e-4


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY E: Infeasibility
# ─────────────────────────────────────────────────────────────────────────────


class TestCategoryE_Infeasibility:
    """Verify structured failure handling without manufacturing fake schedules."""

    def test_impossible_reserve(self) -> None:
        """Mandatory reserve cannot be reached because charging is locked."""
        d_res = NormalizedDirective(
            note_index=0,
            directive_type="minimum_battery_reserve",
            hours=[3],
            minimum_energy_kwh=80.0,
        )
        d_lock = NormalizedDirective(
            note_index=1, directive_type="no_charge_window", hours=[0, 1, 2, 3]
        )
        p_in = make_test_scenario(initial_soc=20.0, directives=[d_res, d_lock])
        res = optimize_and_validate(p_in)
        assert res.is_success is False
        assert res.status == SolverStatus.INFEASIBLE
        assert res.schedule == []  # MUST BE EMPTY!
        assert len(res.errors) > 0

    def test_impossible_max_grid(self) -> None:
        """Max grid limit is less than demand with zero solar and zero battery."""
        d_grid = NormalizedDirective(
            note_index=0, directive_type="max_grid_window", hours=[5], max_grid_kwh=5.0
        )
        p_in = make_test_scenario(
            demand_val=30.0,
            solar_val=0.0,
            battery_cap=1.0,
            initial_soc=0.0,
            min_soc=0.0,
            max_charge=0.0,
            max_discharge=0.0,
            directives=[d_grid],
        )
        res = optimize_and_validate(p_in)
        assert res.is_success is False
        assert res.status == SolverStatus.INFEASIBLE
        assert res.schedule == []

    def test_impossible_battery_requirements(self) -> None:
        """Reserve requirement exceeds battery physical capacity, resulting in infeasible status."""
        d_bad = NormalizedDirective(
            note_index=0,
            directive_type="minimum_battery_reserve",
            hours=[5],
            minimum_energy_kwh=150.0,
        )
        p_in = make_test_scenario(battery_cap=100.0, directives=[d_bad])
        res = optimize_and_validate(p_in)
        assert res.is_success is False
        assert res.status == SolverStatus.INFEASIBLE
        assert res.schedule == []

    def test_insufficient_total_energy(self) -> None:
        """Campus total demand exceeds combined grid ceiling, solar, and battery capacity."""
        d_grid = NormalizedDirective(
            note_index=0,
            directive_type="max_grid_window",
            hours=list(range(HOURS_IN_DAY)),
            max_grid_kwh=5.0,
        )
        p_in = make_test_scenario(
            demand_val=50.0,
            solar_val=0.0,
            battery_cap=100.0,
            initial_soc=10.0,
            directives=[d_grid],
        )
        res = optimize_and_validate(p_in)
        assert res.is_success is False
        assert res.status == SolverStatus.INFEASIBLE
        assert res.schedule == []

    def test_contradictory_constraints(self) -> None:
        """Contradictory directives: max grid 0 when no other energy source exists."""
        d_grid = NormalizedDirective(
            note_index=0, directive_type="max_grid_window", hours=[10], max_grid_kwh=0.0
        )
        d_dis = NormalizedDirective(note_index=1, directive_type="no_discharge_window", hours=[10])
        solar = [0.0] * HOURS_IN_DAY
        p_in = make_test_scenario(demand_val=20.0, solar_val=solar, directives=[d_grid, d_dis])
        res = optimize_and_validate(p_in)
        assert res.is_success is False
        assert res.status == SolverStatus.INFEASIBLE
        assert res.schedule == []


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY F: Numerical Validation
# ─────────────────────────────────────────────────────────────────────────────


class TestCategoryF_NumericalValidation:
    """Verify floating-point precision, objective reconciliation, and state replay."""

    def test_tiny_floating_point_differences(self) -> None:
        """Tiny floating point solver precision artifacts (e.g. 1e-7) do not cause validation failure."""
        validator = DeterministicReplayValidator(default_tolerance=1e-4)
        p_in = make_test_scenario()
        engine = OptimizationEngine(validator=validator)
        res = engine.optimize_and_validate(p_in)
        assert res.is_success is True
        assert res.is_valid is True

    def test_objective_recalculation(self) -> None:
        """Independent validator exactly reconciles reported grid costs with grid * tariff."""
        tariff = [7.5 + (h * 0.5) for h in range(HOURS_IN_DAY)]
        p_in = make_test_scenario(demand_val=18.5, tariff_val=tariff)
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        recalc_cost = sum(row.grid_kwh * row.tariff_bdt_per_kwh for row in res.schedule)
        assert abs(res.total_grid_cost_bdt - recalc_cost) < 1e-4
        assert abs(res.objective_value - recalc_cost) < 1e-4

    def test_battery_state_replay(self) -> None:
        """Step-by-step state transition is re-simulated forward from initial energy."""
        tariff = [5.0] * 12 + [20.0] * 12
        init_soc = 35.0
        p_in = make_test_scenario(tariff_val=tariff, initial_soc=init_soc)
        res = optimize_and_validate(p_in)
        assert res.is_success is True

        prev_e = init_soc
        for row in res.schedule:
            expected_e = prev_e + row.battery_charge_kwh - row.battery_discharge_kwh
            assert abs(row.battery_energy_after_kwh - expected_e) < 1e-4
            prev_e = row.battery_energy_after_kwh

    def test_energy_balance_tolerance(self) -> None:
        """Hourly conservation: abs((grid + solar + discharge) - (demand + charge)) <= tolerance."""
        solar = [0.0] * 6 + [30.0] * 12 + [0.0] * 6
        p_in = make_test_scenario(demand_val=22.5, solar_val=solar)
        res = optimize_and_validate(p_in)
        assert res.is_success is True
        for row in res.schedule:
            supplied = row.grid_kwh + row.solar_used_kwh + row.battery_discharge_kwh
            demanded = row.demand_kwh + row.battery_charge_kwh
            assert abs(supplied - demanded) < 1e-4


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY G: Validator Attack Cases (Deliberately Plausible Malicious Schedules)
# ─────────────────────────────────────────────────────────────────────────────


class TestCategoryG_ValidatorAttackCases:
    """Construct schedules that look plausible but contain subtle physical/contractual violations.

    The independent replay validator must reject every single one of them.
    """

    @pytest.fixture
    def baseline_valid_run(self) -> tuple[OptimizationInput, list[HourlyScheduleOutput], float]:
        """Obtain a genuine optimal schedule from PuLP solver as base for corruption attacks."""
        p_in = make_test_scenario(demand_val=20.0, tariff_val=10.0, initial_soc=40.0)
        engine = OptimizationEngine()
        res = engine.optimize_and_validate(p_in)
        assert res.is_success is True

        compiled = compile_directives([], p_in.base_solar_kwh, p_in.battery)
        opt_input = OptimizationInput.from_arrays(
            demand_kwh=p_in.demand_kwh,
            base_solar_kwh=p_in.base_solar_kwh,
            tariff_bdt_per_kwh=p_in.tariff_bdt_per_kwh,
            battery=p_in.battery,
            compiled_directives=compiled,
        )
        return opt_input, res.schedule, res.total_grid_cost_bdt

    def test_attack_modified_grid_value(self, baseline_valid_run) -> None:
        """Attack: Attacker reduces reported grid by 0.5 kWh at hour 5 to falsely claim lower cost."""
        opt_input, sched, cost = baseline_valid_run
        corrupted = copy.deepcopy(sched)
        corrupted[5] = HourlyScheduleOutput(
            hour=5,
            demand_kwh=corrupted[5].demand_kwh,
            effective_solar_kwh=corrupted[5].effective_solar_kwh,
            solar_used_kwh=corrupted[5].solar_used_kwh,
            battery_charge_kwh=corrupted[5].battery_charge_kwh,
            battery_discharge_kwh=corrupted[5].battery_discharge_kwh,
            battery_energy_after_kwh=corrupted[5].battery_energy_after_kwh,
            grid_kwh=corrupted[5].grid_kwh - 0.5,  # Plausible subtle cheat
            tariff_bdt_per_kwh=corrupted[5].tariff_bdt_per_kwh,
            grid_cost_bdt=(corrupted[5].grid_kwh - 0.5) * corrupted[5].tariff_bdt_per_kwh,
        )

        validator = DeterministicReplayValidator()
        val_res = validator.validate(opt_input, corrupted, cost - 5.0)
        assert val_res.is_valid is False
        assert any("energy balance violation" in err for err in val_res.violations)

    def test_attack_modified_battery_state(self, baseline_valid_run) -> None:
        """Attack: Battery state has unearned 1.0 kWh jump without charging."""
        opt_input, sched, cost = baseline_valid_run
        corrupted = copy.deepcopy(sched)
        corrupted[8] = HourlyScheduleOutput(
            hour=8,
            demand_kwh=corrupted[8].demand_kwh,
            effective_solar_kwh=corrupted[8].effective_solar_kwh,
            solar_used_kwh=corrupted[8].solar_used_kwh,
            battery_charge_kwh=corrupted[8].battery_charge_kwh,
            battery_discharge_kwh=corrupted[8].battery_discharge_kwh,
            battery_energy_after_kwh=corrupted[8].battery_energy_after_kwh + 1.0,  # Phantom energy
            grid_kwh=corrupted[8].grid_kwh,
            tariff_bdt_per_kwh=corrupted[8].tariff_bdt_per_kwh,
            grid_cost_bdt=corrupted[8].grid_cost_bdt,
        )

        validator = DeterministicReplayValidator()
        val_res = validator.validate(opt_input, corrupted, cost)
        assert val_res.is_valid is False
        assert any("battery transition dynamics violation" in err for err in val_res.violations)

    def test_attack_solar_slightly_above_availability(self, baseline_valid_run) -> None:
        """Attack: Solar used is 0.05 kWh above effective availability."""
        opt_input, sched, cost = baseline_valid_run
        corrupted = copy.deepcopy(sched)
        # At hour 10, claim solar_used = 0.05 when available is 0.0
        corrupted[10] = HourlyScheduleOutput(
            hour=10,
            demand_kwh=corrupted[10].demand_kwh,
            effective_solar_kwh=0.0,
            solar_used_kwh=0.05,  # Exceeds availability
            battery_charge_kwh=corrupted[10].battery_charge_kwh,
            battery_discharge_kwh=corrupted[10].battery_discharge_kwh,
            battery_energy_after_kwh=corrupted[10].battery_energy_after_kwh,
            grid_kwh=corrupted[10].grid_kwh - 0.05,  # Balance preserved to mask error
            tariff_bdt_per_kwh=corrupted[10].tariff_bdt_per_kwh,
            grid_cost_bdt=(corrupted[10].grid_kwh - 0.05) * corrupted[10].tariff_bdt_per_kwh,
        )

        validator = DeterministicReplayValidator()
        val_res = validator.validate(opt_input, corrupted, cost - 0.5)
        assert val_res.is_valid is False
        assert any("solar availability violation" in err for err in val_res.violations)

    def test_attack_charge_slightly_above_maximum(self, baseline_valid_run) -> None:
        """Attack: Battery charging rate is 25.05 kWh (max rate is 25.0 kWh)."""
        opt_input, sched, cost = baseline_valid_run
        corrupted = copy.deepcopy(sched)
        corrupted[2] = HourlyScheduleOutput(
            hour=2,
            demand_kwh=corrupted[2].demand_kwh,
            effective_solar_kwh=corrupted[2].effective_solar_kwh,
            solar_used_kwh=corrupted[2].solar_used_kwh,
            battery_charge_kwh=25.05,  # Exceeds max 25.0
            battery_discharge_kwh=0.0,
            battery_energy_after_kwh=40.0 + 25.05,
            grid_kwh=corrupted[2].demand_kwh + 25.05,
            tariff_bdt_per_kwh=corrupted[2].tariff_bdt_per_kwh,
            grid_cost_bdt=(corrupted[2].demand_kwh + 25.05) * corrupted[2].tariff_bdt_per_kwh,
        )

        validator = DeterministicReplayValidator(enforce_eod_neutrality=False)
        val_res = validator.validate(opt_input, corrupted, cost + (25.05 * 10.0))
        assert val_res.is_valid is False
        assert any("battery charge rate violation" in err for err in val_res.violations)

    def test_attack_reserve_violation(self) -> None:
        """Attack: Battery state drops 0.1 kWh below mandatory reserve."""
        d_res = NormalizedDirective(
            note_index=0,
            directive_type="minimum_battery_reserve",
            hours=[15],
            minimum_energy_kwh=35.0,
        )
        p_in = make_test_scenario(initial_soc=40.0, directives=[d_res])
        engine = OptimizationEngine()
        res = engine.optimize_and_validate(p_in)
        assert res.is_success is True

        # Corrupt hour 15 to drop to 34.9 kWh (below reserve 35.0)
        corrupted = copy.deepcopy(res.schedule)
        corrupted[15] = HourlyScheduleOutput(
            hour=15,
            demand_kwh=corrupted[15].demand_kwh,
            effective_solar_kwh=corrupted[15].effective_solar_kwh,
            solar_used_kwh=corrupted[15].solar_used_kwh,
            battery_charge_kwh=corrupted[15].battery_charge_kwh,
            battery_discharge_kwh=corrupted[15].battery_discharge_kwh,
            battery_energy_after_kwh=34.9,  # Subtle reserve violation
            grid_kwh=corrupted[15].grid_kwh,
            tariff_bdt_per_kwh=corrupted[15].tariff_bdt_per_kwh,
            grid_cost_bdt=corrupted[15].grid_cost_bdt,
        )

        compiled = compile_directives([d_res], p_in.base_solar_kwh, p_in.battery)
        opt_input = OptimizationInput.from_arrays(
            demand_kwh=p_in.demand_kwh,
            base_solar_kwh=p_in.base_solar_kwh,
            tariff_bdt_per_kwh=p_in.tariff_bdt_per_kwh,
            battery=p_in.battery,
            compiled_directives=compiled,
        )

        validator = DeterministicReplayValidator()
        val_res = validator.validate(opt_input, corrupted, res.total_grid_cost_bdt)
        assert val_res.is_valid is False
        assert any(
            "minimum_battery_reserve directive violation" in err for err in val_res.violations
        )

    def test_attack_final_battery_mismatch(self, baseline_valid_run) -> None:
        """Attack: End-of-day battery neutrality is broken by 0.5 kWh."""
        opt_input, sched, cost = baseline_valid_run
        corrupted = copy.deepcopy(sched)
        corrupted[23] = HourlyScheduleOutput(
            hour=23,
            demand_kwh=corrupted[23].demand_kwh,
            effective_solar_kwh=corrupted[23].effective_solar_kwh,
            solar_used_kwh=corrupted[23].solar_used_kwh,
            battery_charge_kwh=corrupted[23].battery_charge_kwh,
            battery_discharge_kwh=corrupted[23].battery_discharge_kwh,
            battery_energy_after_kwh=opt_input.battery.initial_energy_kwh
            - 0.5,  # Unreturned energy
            grid_kwh=corrupted[23].grid_kwh,
            tariff_bdt_per_kwh=corrupted[23].tariff_bdt_per_kwh,
            grid_cost_bdt=corrupted[23].grid_cost_bdt,
        )

        validator = DeterministicReplayValidator(enforce_eod_neutrality=True)
        val_res = validator.validate(opt_input, corrupted, cost)
        assert val_res.is_valid is False
        assert any("End-of-day battery neutrality violation" in err for err in val_res.violations)
