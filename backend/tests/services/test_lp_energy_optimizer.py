"""Unit tests for deterministic 24-hour LP energy optimizer using PuLP + CBC.

Covers all 20 required verification scenarios:
1. Basic demand with no battery
2. Solar reduces grid usage
3. Battery discharge
4. Battery charging
5. Varying tariffs
6. Battery capacity
7. Charge-rate limit
8. Discharge-rate limit
9. Initial battery energy
10. Final battery neutrality
11. No-charge directive
12. No-discharge directive
13. Minimum reserve
14. Maximum grid
15. Solar reduction
16. Multiple overlapping directives
17. Infeasible reserve
18. Infeasible max-grid
19. Infeasible overall energy scenario
20. No simultaneous charge/discharge in economically meaningful solutions
"""

from __future__ import annotations

import pytest

from app.services.optimizer import (
    BatteryConfig,
    HourlyEnergyProfile,
    NormalizedDirective,
    OptimizationInfeasibleError,
    OptimizationInput,
    OptimizationResult,
    PuLpEnergyOptimizer,
    SolverStatus,
    optimize,
)
from app.services.validation import compile_directives

HOURS: int = 24


def make_test_input(
    demand: list[float] | None = None,
    solar: list[float] | None = None,
    tariff: list[float] | None = None,
    battery: BatteryConfig | None = None,
    directives: list[NormalizedDirective] | None = None,
) -> OptimizationInput:
    """Helper creating typed OptimizationInput with compiled directives."""
    dem = demand if demand is not None else [20.0] * HOURS
    sol = solar if solar is not None else [0.0] * HOURS
    tar = tariff if tariff is not None else [10.0] * HOURS

    bat = (
        battery
        if battery is not None
        else BatteryConfig(
            capacity_kwh=100.0,
            initial_energy_kwh=40.0,
            minimum_energy_kwh=10.0,
            max_charge_kwh_per_hour=25.0,
            max_discharge_kwh_per_hour=25.0,
        )
    )

    dirs = directives or []
    compiled = compile_directives(dirs, sol, bat)

    return OptimizationInput.from_arrays(
        demand_kwh=dem,
        base_solar_kwh=sol,
        tariff_bdt_per_kwh=tar,
        battery=bat,
        compiled_directives=compiled,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Basic demand with no battery
# ─────────────────────────────────────────────────────────────────────────────


def test_1_basic_demand_no_battery() -> None:
    battery = BatteryConfig(
        capacity_kwh=1.0,
        initial_energy_kwh=0.0,
        minimum_energy_kwh=0.0,
        max_charge_kwh_per_hour=0.0,
        max_discharge_kwh_per_hour=0.0,
    )
    opt_in = make_test_input(
        demand=[10.0] * HOURS,
        solar=[0.0] * HOURS,
        tariff=[10.0] * HOURS,
        battery=battery,
    )

    res = optimize(opt_in)
    assert res.solver_status == SolverStatus.OPTIMAL
    assert res.is_optimal is True
    assert res.total_grid_kwh == pytest.approx(240.0)
    assert res.total_grid_cost_bdt == pytest.approx(2400.0)
    for h in res.schedule:
        assert h.grid_kwh == pytest.approx(10.0)
        assert h.battery_charge_kwh == pytest.approx(0.0)
        assert h.battery_discharge_kwh == pytest.approx(0.0)


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Solar reduces grid usage
# ─────────────────────────────────────────────────────────────────────────────


def test_2_solar_reduces_grid_usage() -> None:
    # 20 kWh demand everywhere, 10 kWh solar on hours 10..15
    solar = [0.0] * 10 + [10.0] * 6 + [0.0] * 8
    battery = BatteryConfig(
        capacity_kwh=1.0,
        initial_energy_kwh=0.0,
        minimum_energy_kwh=0.0,
        max_charge_kwh_per_hour=0.0,
        max_discharge_kwh_per_hour=0.0,
    )
    opt_in = make_test_input(
        demand=[20.0] * HOURS,
        solar=solar,
        tariff=[10.0] * HOURS,
        battery=battery,
    )

    res = optimize(opt_in)
    assert res.is_optimal is True
    # During solar hours, grid should be 10 kWh, otherwise 20 kWh
    for h in res.schedule:
        if 10 <= h.hour <= 15:
            assert h.solar_used_kwh == pytest.approx(10.0)
            assert h.grid_kwh == pytest.approx(10.0)
        else:
            assert h.solar_used_kwh == pytest.approx(0.0)
            assert h.grid_kwh == pytest.approx(20.0)

    expected_grid = 18 * 20.0 + 6 * 10.0  # 420.0
    assert res.total_grid_kwh == pytest.approx(expected_grid)


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Battery discharge
# ─────────────────────────────────────────────────────────────────────────────


def test_3_battery_discharge() -> None:
    # High tariff at hour 18 (50 BDT vs 5 BDT)
    tariff = [5.0] * HOURS
    tariff[18] = 50.0

    battery = BatteryConfig(
        capacity_kwh=100.0,
        initial_energy_kwh=50.0,
        minimum_energy_kwh=10.0,
        max_charge_kwh_per_hour=25.0,
        max_discharge_kwh_per_hour=25.0,
    )
    opt_in = make_test_input(
        demand=[10.0] * HOURS,
        tariff=tariff,
        battery=battery,
    )

    res = optimize(opt_in)
    assert res.is_optimal is True
    # Battery should discharge during peak hour 18
    hour_18 = res.schedule[18]
    assert hour_18.battery_discharge_kwh > 0.0
    assert hour_18.grid_kwh < 10.0


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Battery charging
# ─────────────────────────────────────────────────────────────────────────────


def test_4_battery_charging() -> None:
    # Very cheap off-peak hours (1 BDT) at night, expensive during day (20 BDT)
    tariff = [1.0] * 6 + [20.0] * 18
    battery = BatteryConfig(
        capacity_kwh=100.0,
        initial_energy_kwh=20.0,
        minimum_energy_kwh=10.0,
        max_charge_kwh_per_hour=20.0,
        max_discharge_kwh_per_hour=20.0,
    )
    opt_in = make_test_input(
        demand=[10.0] * HOURS,
        tariff=tariff,
        battery=battery,
    )

    res = optimize(opt_in)
    assert res.is_optimal is True
    # Should charge during cheap hours 0..5
    cheap_charges = sum(res.schedule[h].battery_charge_kwh for h in range(6))
    assert cheap_charges > 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Varying tariffs
# ─────────────────────────────────────────────────────────────────────────────


def test_5_varying_tariffs() -> None:
    # TOU tariff: low (2 BDT), mid (10 BDT), peak (30 BDT)
    tariff = [2.0] * 6 + [10.0] * 10 + [30.0] * 4 + [10.0] * 4
    battery = BatteryConfig(
        capacity_kwh=100.0,
        initial_energy_kwh=30.0,
        minimum_energy_kwh=10.0,
        max_charge_kwh_per_hour=25.0,
        max_discharge_kwh_per_hour=25.0,
    )
    opt_in = make_test_input(
        demand=[15.0] * HOURS,
        tariff=tariff,
        battery=battery,
    )

    res = optimize(opt_in)
    assert res.is_optimal is True
    # During peak hours (16..19), grid usage should be minimized via battery discharge
    peak_grid = sum(res.schedule[h].grid_kwh for h in range(16, 20))
    peak_demand = 15.0 * 4
    assert peak_grid < peak_demand


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Battery capacity
# ─────────────────────────────────────────────────────────────────────────────


def test_6_battery_capacity() -> None:
    # Giant solar surplus (500 kWh)
    solar = [500.0] * HOURS
    battery = BatteryConfig(
        capacity_kwh=80.0,
        initial_energy_kwh=20.0,
        minimum_energy_kwh=10.0,
        max_charge_kwh_per_hour=50.0,
        max_discharge_kwh_per_hour=50.0,
    )
    opt_in = make_test_input(
        demand=[5.0] * HOURS,
        solar=solar,
        battery=battery,
    )

    res = optimize(opt_in)
    assert res.is_optimal is True
    for h in res.schedule:
        assert h.battery_energy_after_kwh <= battery.capacity_kwh + 1e-6


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Charge-rate limit
# ─────────────────────────────────────────────────────────────────────────────


def test_7_charge_rate_limit() -> None:
    # Max charge limit 15 kWh/h with abundant cheap energy
    max_charge = 15.0
    battery = BatteryConfig(
        capacity_kwh=100.0,
        initial_energy_kwh=10.0,
        minimum_energy_kwh=10.0,
        max_charge_kwh_per_hour=max_charge,
        max_discharge_kwh_per_hour=25.0,
    )
    opt_in = make_test_input(
        demand=[5.0] * HOURS,
        solar=[100.0] * HOURS,
        battery=battery,
    )

    res = optimize(opt_in)
    assert res.is_optimal is True
    for h in res.schedule:
        assert h.battery_charge_kwh <= max_charge + 1e-6


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Discharge-rate limit
# ─────────────────────────────────────────────────────────────────────────────


def test_8_discharge_rate_limit() -> None:
    # Max discharge limit 12 kWh/h during massive demand
    max_discharge = 12.0
    tariff = [5.0] * HOURS
    tariff[18] = 100.0
    battery = BatteryConfig(
        capacity_kwh=100.0,
        initial_energy_kwh=60.0,
        minimum_energy_kwh=10.0,
        max_charge_kwh_per_hour=25.0,
        max_discharge_kwh_per_hour=max_discharge,
    )
    opt_in = make_test_input(
        demand=[50.0] * HOURS,
        tariff=tariff,
        battery=battery,
    )

    res = optimize(opt_in)
    assert res.is_optimal is True
    for h in res.schedule:
        assert h.battery_discharge_kwh <= max_discharge + 1e-6


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Initial battery energy
# ─────────────────────────────────────────────────────────────────────────────


def test_9_initial_battery_energy() -> None:
    initial_e = 45.0
    battery = BatteryConfig(
        capacity_kwh=100.0,
        initial_energy_kwh=initial_e,
        minimum_energy_kwh=10.0,
        max_charge_kwh_per_hour=20.0,
        max_discharge_kwh_per_hour=20.0,
    )
    opt_in = make_test_input(battery=battery)

    res = optimize(opt_in)
    assert res.is_optimal is True
    h0 = res.schedule[0]
    expected_e0 = initial_e + h0.battery_charge_kwh - h0.battery_discharge_kwh
    assert h0.battery_energy_after_kwh == pytest.approx(expected_e0)


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: Final battery neutrality
# ─────────────────────────────────────────────────────────────────────────────


def test_10_final_battery_neutrality() -> None:
    initial_e = 35.0
    battery = BatteryConfig(
        capacity_kwh=100.0,
        initial_energy_kwh=initial_e,
        minimum_energy_kwh=10.0,
        max_charge_kwh_per_hour=20.0,
        max_discharge_kwh_per_hour=20.0,
    )
    opt_in = make_test_input(battery=battery)

    res = optimize(opt_in)
    assert res.is_optimal is True
    # Hour 23 must equal initial_energy exactly
    assert res.schedule[23].battery_energy_after_kwh == pytest.approx(initial_e, abs=1e-5)


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: No-charge directive
# ─────────────────────────────────────────────────────────────────────────────


def test_11_no_charge_directive() -> None:
    # Off-peak hours 1..4 have a no-charge directive
    dirs = [
        NormalizedDirective(
            note_index=0,
            directive_type="no_charge_window",
            hours=[1, 2, 3, 4],
        )
    ]
    tariff = [1.0] * 6 + [20.0] * 18
    opt_in = make_test_input(
        tariff=tariff,
        directives=dirs,
    )

    res = optimize(opt_in)
    assert res.is_optimal is True
    for h in [1, 2, 3, 4]:
        assert res.schedule[h].battery_charge_kwh == pytest.approx(0.0)


# ─────────────────────────────────────────────────────────────────────────────
# Test 12: No-discharge directive
# ─────────────────────────────────────────────────────────────────────────────


def test_12_no_discharge_directive() -> None:
    # Peak hour 18 has a no-discharge directive
    dirs = [
        NormalizedDirective(
            note_index=0,
            directive_type="no_discharge_window",
            hours=[18, 19],
        )
    ]
    tariff = [5.0] * HOURS
    tariff[18] = 50.0
    tariff[19] = 50.0
    opt_in = make_test_input(
        tariff=tariff,
        directives=dirs,
    )

    res = optimize(opt_in)
    assert res.is_optimal is True
    for h in [18, 19]:
        assert res.schedule[h].battery_discharge_kwh == pytest.approx(0.0)


# ─────────────────────────────────────────────────────────────────────────────
# Test 13: Minimum reserve
# ─────────────────────────────────────────────────────────────────────────────


def test_13_minimum_reserve() -> None:
    # Elevate minimum reserve to 50 kWh on hours 12..16
    dirs = [
        NormalizedDirective(
            note_index=0,
            directive_type="minimum_battery_reserve",
            hours=[12, 13, 14, 15, 16],
            minimum_energy_kwh=50.0,
        )
    ]
    battery = BatteryConfig(
        capacity_kwh=100.0,
        initial_energy_kwh=60.0,
        minimum_energy_kwh=10.0,
        max_charge_kwh_per_hour=25.0,
        max_discharge_kwh_per_hour=25.0,
    )
    opt_in = make_test_input(
        battery=battery,
        directives=dirs,
    )

    res = optimize(opt_in)
    assert res.is_optimal is True
    for h in range(12, 17):
        assert res.schedule[h].battery_energy_after_kwh >= 50.0 - 1e-6


# ─────────────────────────────────────────────────────────────────────────────
# Test 14: Maximum grid
# ─────────────────────────────────────────────────────────────────────────────


def test_14_maximum_grid() -> None:
    # Max grid 5.0 kWh on hours 17..19
    max_cap = 5.0
    dirs = [
        NormalizedDirective(
            note_index=0,
            directive_type="max_grid_window",
            hours=[17, 18, 19],
            max_grid_kwh=max_cap,
        )
    ]
    # Demand 15 kWh, initial battery 60 kWh to ensure feasibility
    battery = BatteryConfig(
        capacity_kwh=100.0,
        initial_energy_kwh=60.0,
        minimum_energy_kwh=10.0,
        max_charge_kwh_per_hour=25.0,
        max_discharge_kwh_per_hour=25.0,
    )
    opt_in = make_test_input(
        demand=[15.0] * HOURS,
        battery=battery,
        directives=dirs,
    )

    res = optimize(opt_in)
    assert res.is_optimal is True
    for h in [17, 18, 19]:
        assert res.schedule[h].grid_kwh <= max_cap + 1e-6


# ─────────────────────────────────────────────────────────────────────────────
# Test 15: Solar reduction
# ─────────────────────────────────────────────────────────────────────────────


def test_15_solar_reduction() -> None:
    # Solar 100 kWh reduced by 50% (factor 0.5) on hours 10..12
    solar = [0.0] * 10 + [100.0] * 3 + [0.0] * 11
    dirs = [
        NormalizedDirective(
            note_index=0,
            directive_type="solar_reduction",
            hours=[10, 11, 12],
            factor=0.5,
        )
    ]
    opt_in = make_test_input(
        demand=[60.0] * HOURS,
        solar=solar,
        directives=dirs,
    )

    res = optimize(opt_in)
    assert res.is_optimal is True
    # Effective solar should be 50.0 kWh; solar_used cannot exceed 50.0
    for h in [10, 11, 12]:
        assert res.schedule[h].solar_used_kwh <= 50.0 + 1e-6


# ─────────────────────────────────────────────────────────────────────────────
# Test 16: Multiple overlapping directives
# ─────────────────────────────────────────────────────────────────────────────


def test_16_multiple_overlapping_directives() -> None:
    dirs = [
        NormalizedDirective(
            note_index=0,
            directive_type="solar_reduction",
            hours=[10, 11, 12],
            factor=0.8,
        ),
        NormalizedDirective(
            note_index=1,
            directive_type="solar_reduction",
            hours=[11, 12, 13],
            factor=0.5,
        ),
        NormalizedDirective(
            note_index=2,
            directive_type="minimum_battery_reserve",
            hours=[11, 12],
            minimum_energy_kwh=30.0,
        ),
        NormalizedDirective(
            note_index=3,
            directive_type="no_charge_window",
            hours=[11],
        ),
    ]
    solar = [50.0] * HOURS
    battery = BatteryConfig(
        capacity_kwh=100.0,
        initial_energy_kwh=40.0,
        minimum_energy_kwh=10.0,
        max_charge_kwh_per_hour=25.0,
        max_discharge_kwh_per_hour=25.0,
    )
    opt_in = make_test_input(
        demand=[20.0] * HOURS,
        solar=solar,
        battery=battery,
        directives=dirs,
    )

    res = optimize(opt_in)
    assert res.is_optimal is True
    # Hour 11 has: solar reduction (0.8 * 0.5 = 0.4 -> 20 kWh), min reserve 30, no charge
    h11 = res.schedule[11]
    assert h11.solar_used_kwh <= 20.0 + 1e-6
    assert h11.battery_charge_kwh == pytest.approx(0.0)
    assert h11.battery_energy_after_kwh >= 30.0 - 1e-6


# ─────────────────────────────────────────────────────────────────────────────
# Test 17: Infeasible reserve
# ─────────────────────────────────────────────────────────────────────────────


def test_17_infeasible_reserve() -> None:
    # Reserve requirement exceeds battery capacity (150 kWh > 100 kWh)
    battery = BatteryConfig(
        capacity_kwh=100.0,
        initial_energy_kwh=50.0,
        minimum_energy_kwh=10.0,
        max_charge_kwh_per_hour=25.0,
        max_discharge_kwh_per_hour=25.0,
    )
    # Manually compiled with impossible reserve
    opt_in = make_test_input(battery=battery)
    # Inject impossible reserve into compiled directives
    compiled = opt_in.compiled_directives
    impossible_reserve = list(compiled.min_reserve)
    impossible_reserve[12] = 150.0
    bad_directives = type(compiled)(
        solar_factor=compiled.solar_factor,
        effective_solar=compiled.effective_solar,
        min_reserve=impossible_reserve,
        no_charge=compiled.no_charge,
        no_discharge=compiled.no_discharge,
        max_grid=compiled.max_grid,
    )
    bad_input = OptimizationInput(
        energy_profile=opt_in.energy_profile,
        battery=battery,
        compiled_directives=bad_directives,
    )

    res = optimize(bad_input)
    assert res.solver_status == SolverStatus.INFEASIBLE
    assert res.is_optimal is False
    assert len(res.schedule) == 0

    with pytest.raises(OptimizationInfeasibleError):
        optimize(bad_input, raise_on_error=True)


# ─────────────────────────────────────────────────────────────────────────────
# Test 18: Infeasible max-grid
# ─────────────────────────────────────────────────────────────────────────────


def test_18_infeasible_max_grid() -> None:
    # Demand 50 kWh, solar 0, battery empty (initial=0, min=0, capacity=10), max_grid 0 kWh
    battery = BatteryConfig(
        capacity_kwh=10.0,
        initial_energy_kwh=0.0,
        minimum_energy_kwh=0.0,
        max_charge_kwh_per_hour=0.0,
        max_discharge_kwh_per_hour=0.0,
    )
    dirs = [
        NormalizedDirective(
            note_index=0,
            directive_type="max_grid_window",
            hours=[12],
            max_grid_kwh=0.0,
        )
    ]
    opt_in = make_test_input(
        demand=[50.0] * HOURS,
        solar=[0.0] * HOURS,
        battery=battery,
        directives=dirs,
    )

    res = optimize(opt_in)
    assert res.solver_status == SolverStatus.INFEASIBLE
    assert res.is_optimal is False
    assert len(res.schedule) == 0


# ─────────────────────────────────────────────────────────────────────────────
# Test 19: Infeasible overall energy scenario
# ─────────────────────────────────────────────────────────────────────────────


def test_19_infeasible_overall_energy_scenario() -> None:
    # Initial energy 10 kWh, neutrality requires final=10 kWh, but min reserve on hour 23 is 50 kWh
    battery = BatteryConfig(
        capacity_kwh=100.0,
        initial_energy_kwh=10.0,
        minimum_energy_kwh=10.0,
        max_charge_kwh_per_hour=25.0,
        max_discharge_kwh_per_hour=25.0,
    )
    dirs = [
        NormalizedDirective(
            note_index=0,
            directive_type="minimum_battery_reserve",
            hours=[23],
            minimum_energy_kwh=50.0,
        )
    ]
    opt_in = make_test_input(
        battery=battery,
        directives=dirs,
    )

    # Neutrality forces energy_after[23] == 10, but directive forces energy_after[23] >= 50 -> Infeasible!
    res = optimize(opt_in)
    assert res.solver_status == SolverStatus.INFEASIBLE
    assert res.is_optimal is False
    assert len(res.schedule) == 0


# ─────────────────────────────────────────────────────────────────────────────
# Test 20: No simultaneous charge/discharge in economically meaningful solutions
# ─────────────────────────────────────────────────────────────────────────────


def test_20_no_simultaneous_charge_discharge() -> None:
    # Solve a realistic TOU scenario with solar and battery
    tariff = [3.0] * 6 + [10.0] * 10 + [25.0] * 4 + [8.0] * 4
    solar = [0.0] * 6 + [30.0] * 8 + [10.0] * 4 + [0.0] * 6
    demand = [15.0] * 6 + [25.0] * 10 + [40.0] * 4 + [20.0] * 4
    battery = BatteryConfig(
        capacity_kwh=100.0,
        initial_energy_kwh=30.0,
        minimum_energy_kwh=10.0,
        max_charge_kwh_per_hour=20.0,
        max_discharge_kwh_per_hour=20.0,
        charge_efficiency=0.95,
        discharge_efficiency=0.95,
    )
    opt_in = make_test_input(
        demand=demand,
        solar=solar,
        tariff=tariff,
        battery=battery,
    )

    res = optimize(opt_in)
    assert res.is_optimal is True

    # For every hour, verify that charging and discharging are mutually exclusive
    for h in res.schedule:
        simultaneous = min(h.battery_charge_kwh, h.battery_discharge_kwh)
        assert simultaneous == pytest.approx(0.0, abs=1e-5), (
            f"Hour {h.hour}: simultaneous charge ({h.battery_charge_kwh}) "
            f"and discharge ({h.battery_discharge_kwh}) detected!"
        )


def test_pulp_energy_optimizer_class_interface() -> None:
    optimizer = PuLpEnergyOptimizer(default_timeout_seconds=5.0)
    opt_in = make_test_input()
    res1: OptimizationResult = optimizer.solve(opt_in)
    res2: OptimizationResult = optimizer.optimize(opt_in)
    assert res1.solver_status == SolverStatus.OPTIMAL
    assert res2.solver_status == SolverStatus.OPTIMAL
    assert isinstance(opt_in.energy_profile, HourlyEnergyProfile)
