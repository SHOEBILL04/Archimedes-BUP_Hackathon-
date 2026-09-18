"""Tests for the dispatch LP optimizer and public orchestration service."""

from __future__ import annotations

import pytest

from app.services.optimizer import (
    BatteryInput,
    InfeasibleError,
    run_optimization,
)


@pytest.fixture
def simple_battery() -> BatteryInput:
    return BatteryInput(
        capacity_kwh=100.0,
        initial_energy_kwh=50.0,
        minimum_energy_kwh=10.0,
        max_charge_kwh_per_hour=30.0,
        max_discharge_kwh_per_hour=30.0,
    )


@pytest.fixture
def flat_demand() -> list[float]:
    return [50.0] * 24


@pytest.fixture
def flat_tariff() -> list[float]:
    return [10.0] * 24


@pytest.fixture
def zero_solar() -> list[float]:
    return [0.0] * 24


@pytest.fixture
def daytime_solar() -> list[float]:
    return [0.0] * 6 + [10, 20, 30, 40, 50, 60, 65, 60, 50, 40, 30, 15] + [0.0] * 6


# ── Basic optimization tests ──


def test_basic_no_solar(flat_demand: list[float], zero_solar: list[float], flat_tariff: list[float], simple_battery: BatteryInput):
    result = run_optimization(
        demand=flat_demand,
        base_solar=zero_solar,
        tariff=flat_tariff,
        battery=simple_battery,
        raw_interpretations=[],
        note_count=0,
    )
    assert result.solver_status == "Optimal"
    assert len(result.hourly_schedule) == 24
    assert abs(result.hourly_schedule[23].battery_energy_after_kwh - simple_battery.initial_energy_kwh) < 1e-4


def test_solar_reduces_grid_cost(
    flat_demand: list[float],
    zero_solar: list[float],
    daytime_solar: list[float],
    flat_tariff: list[float],
    simple_battery: BatteryInput,
):
    res_no_solar = run_optimization(
        demand=flat_demand,
        base_solar=zero_solar,
        tariff=flat_tariff,
        battery=simple_battery,
        raw_interpretations=[],
        note_count=0,
    )
    res_solar = run_optimization(
        demand=flat_demand,
        base_solar=daytime_solar,
        tariff=flat_tariff,
        battery=simple_battery,
        raw_interpretations=[],
        note_count=0,
    )
    assert res_solar.total_grid_cost_bdt < res_no_solar.total_grid_cost_bdt


def test_varying_tariff_charges_in_cheap_hours(
    flat_demand: list[float],
    daytime_solar: list[float],
    simple_battery: BatteryInput,
):
    tariff = [8.0] * 8 + [15.0] * 8 + [10.0] * 8
    result = run_optimization(
        demand=flat_demand,
        base_solar=daytime_solar,
        tariff=tariff,
        battery=simple_battery,
        raw_interpretations=[],
        note_count=0,
    )
    assert result.solver_status == "Optimal"
    total_cheap_charge = sum(result.hourly_schedule[h].battery_charge_kwh for h in range(8))
    assert total_cheap_charge > 0.0


def test_end_of_day_neutrality(
    flat_demand: list[float],
    daytime_solar: list[float],
    flat_tariff: list[float],
    simple_battery: BatteryInput,
):
    result = run_optimization(
        demand=flat_demand,
        base_solar=daytime_solar,
        tariff=flat_tariff,
        battery=simple_battery,
        raw_interpretations=[],
        note_count=0,
    )
    final_energy = result.hourly_schedule[23].battery_energy_after_kwh
    assert abs(final_energy - simple_battery.initial_energy_kwh) < 1e-4


def test_peak_grid_kwh_correct(
    flat_demand: list[float],
    daytime_solar: list[float],
    flat_tariff: list[float],
    simple_battery: BatteryInput,
):
    result = run_optimization(
        demand=flat_demand,
        base_solar=daytime_solar,
        tariff=flat_tariff,
        battery=simple_battery,
        raw_interpretations=[],
        note_count=0,
    )
    expected_peak = max(h.grid_kwh for h in result.hourly_schedule)
    assert pytest.approx(result.peak_grid_kwh, abs=1e-4) == expected_peak


def test_total_grid_kwh_correct(
    flat_demand: list[float],
    daytime_solar: list[float],
    flat_tariff: list[float],
    simple_battery: BatteryInput,
):
    result = run_optimization(
        demand=flat_demand,
        base_solar=daytime_solar,
        tariff=flat_tariff,
        battery=simple_battery,
        raw_interpretations=[],
        note_count=0,
    )
    expected_total = sum(h.grid_kwh for h in result.hourly_schedule)
    assert pytest.approx(result.total_grid_kwh, abs=1e-4) == expected_total


def test_total_cost_correct(
    flat_demand: list[float],
    daytime_solar: list[float],
    simple_battery: BatteryInput,
):
    tariff = [8.0] * 8 + [15.0] * 8 + [10.0] * 8
    result = run_optimization(
        demand=flat_demand,
        base_solar=daytime_solar,
        tariff=tariff,
        battery=simple_battery,
        raw_interpretations=[],
        note_count=0,
    )
    expected_cost = sum(h.grid_kwh * h.tariff_bdt_per_kwh for h in result.hourly_schedule)
    assert pytest.approx(result.total_grid_cost_bdt, abs=1e-4) == expected_cost


# ── Battery constraint tests ──


def test_charge_rate_limit(flat_demand: list[float], daytime_solar: list[float], simple_battery: BatteryInput):
    tariff = [5.0] * 12 + [25.0] * 12
    result = run_optimization(
        demand=flat_demand,
        base_solar=daytime_solar,
        tariff=tariff,
        battery=simple_battery,
        raw_interpretations=[],
        note_count=0,
    )
    for h in result.hourly_schedule:
        assert h.battery_charge_kwh <= simple_battery.max_charge_kwh_per_hour + 1e-5


def test_discharge_rate_limit(flat_demand: list[float], daytime_solar: list[float], simple_battery: BatteryInput):
    tariff = [25.0] * 12 + [5.0] * 12
    result = run_optimization(
        demand=flat_demand,
        base_solar=daytime_solar,
        tariff=tariff,
        battery=simple_battery,
        raw_interpretations=[],
        note_count=0,
    )
    for h in result.hourly_schedule:
        assert h.battery_discharge_kwh <= simple_battery.max_discharge_kwh_per_hour + 1e-5


def test_battery_minimum_energy(flat_demand: list[float], daytime_solar: list[float], flat_tariff: list[float], simple_battery: BatteryInput):
    result = run_optimization(
        demand=flat_demand,
        base_solar=daytime_solar,
        tariff=flat_tariff,
        battery=simple_battery,
        raw_interpretations=[],
        note_count=0,
    )
    for h in result.hourly_schedule:
        assert h.battery_energy_after_kwh >= simple_battery.minimum_energy_kwh - 1e-5


def test_battery_capacity_limit(flat_demand: list[float], daytime_solar: list[float], flat_tariff: list[float], simple_battery: BatteryInput):
    result = run_optimization(
        demand=flat_demand,
        base_solar=daytime_solar,
        tariff=flat_tariff,
        battery=simple_battery,
        raw_interpretations=[],
        note_count=0,
    )
    for h in result.hourly_schedule:
        assert h.battery_energy_after_kwh <= simple_battery.capacity_kwh + 1e-5


# ── Directive tests ──


def test_solar_reduction_applied(
    flat_demand: list[float],
    daytime_solar: list[float],
    flat_tariff: list[float],
    simple_battery: BatteryInput,
):
    dirs = [
        {
            "note_index": 0,
            "directive_type": "solar_reduction",
            "structured_adjustment": {"hours": [12, 13], "factor": 0.2},
            "applies": True,
        }
    ]
    res_base = run_optimization(
        demand=flat_demand,
        base_solar=daytime_solar,
        tariff=flat_tariff,
        battery=simple_battery,
        raw_interpretations=[],
        note_count=0,
    )
    res_reduced = run_optimization(
        demand=flat_demand,
        base_solar=daytime_solar,
        tariff=flat_tariff,
        battery=simple_battery,
        raw_interpretations=dirs,
        note_count=1,
    )
    assert res_reduced.hourly_schedule[12].solar_used_kwh <= daytime_solar[12] * 0.2 + 1e-5
    assert res_reduced.total_grid_cost_bdt > res_base.total_grid_cost_bdt


def test_no_charge_window_applied(
    flat_demand: list[float],
    daytime_solar: list[float],
    simple_battery: BatteryInput,
):
    tariff = [5.0] * 24
    dirs = [
        {
            "note_index": 0,
            "directive_type": "no_charge_window",
            "structured_adjustment": {"hours": [18, 19, 20]},
            "applies": True,
        }
    ]
    res = run_optimization(
        demand=flat_demand,
        base_solar=daytime_solar,
        tariff=tariff,
        battery=simple_battery,
        raw_interpretations=dirs,
        note_count=1,
    )
    assert res.hourly_schedule[18].battery_charge_kwh < 1e-5
    assert res.hourly_schedule[19].battery_charge_kwh < 1e-5
    assert res.hourly_schedule[20].battery_charge_kwh < 1e-5


def test_no_discharge_window_applied(
    flat_demand: list[float],
    daytime_solar: list[float],
    simple_battery: BatteryInput,
):
    tariff = [25.0] * 24
    dirs = [
        {
            "note_index": 0,
            "directive_type": "no_discharge_window",
            "structured_adjustment": {"hours": [8, 9, 10]},
            "applies": True,
        }
    ]
    res = run_optimization(
        demand=flat_demand,
        base_solar=daytime_solar,
        tariff=tariff,
        battery=simple_battery,
        raw_interpretations=dirs,
        note_count=1,
    )
    assert res.hourly_schedule[8].battery_discharge_kwh < 1e-5
    assert res.hourly_schedule[9].battery_discharge_kwh < 1e-5
    assert res.hourly_schedule[10].battery_discharge_kwh < 1e-5


def test_minimum_reserve_applied(
    flat_demand: list[float],
    daytime_solar: list[float],
    flat_tariff: list[float],
    simple_battery: BatteryInput,
):
    dirs = [
        {
            "note_index": 0,
            "directive_type": "minimum_battery_reserve",
            "structured_adjustment": {"hours": [20, 21, 22], "minimum_energy_kwh": 80.0},
            "applies": True,
        }
    ]
    res = run_optimization(
        demand=flat_demand,
        base_solar=daytime_solar,
        tariff=flat_tariff,
        battery=simple_battery,
        raw_interpretations=dirs,
        note_count=1,
    )
    assert res.hourly_schedule[20].battery_energy_after_kwh >= 80.0 - 1e-5
    assert res.hourly_schedule[21].battery_energy_after_kwh >= 80.0 - 1e-5
    assert res.hourly_schedule[22].battery_energy_after_kwh >= 80.0 - 1e-5


def test_max_grid_applied(
    flat_demand: list[float],
    daytime_solar: list[float],
    flat_tariff: list[float],
    simple_battery: BatteryInput,
):
    dirs = [
        {
            "note_index": 0,
            "directive_type": "max_grid_window",
            "structured_adjustment": {"hours": [9, 10, 11], "max_grid_kwh": 30.0},
            "applies": True,
        }
    ]
    res = run_optimization(
        demand=flat_demand,
        base_solar=daytime_solar,
        tariff=flat_tariff,
        battery=simple_battery,
        raw_interpretations=dirs,
        note_count=1,
    )
    assert res.hourly_schedule[9].grid_kwh <= 30.0 + 1e-5
    assert res.hourly_schedule[10].grid_kwh <= 30.0 + 1e-5
    assert res.hourly_schedule[11].grid_kwh <= 30.0 + 1e-5


def test_multiple_solar_reductions_multiply(
    flat_demand: list[float],
    daytime_solar: list[float],
    flat_tariff: list[float],
    simple_battery: BatteryInput,
):
    dirs = [
        {
            "note_index": 0,
            "directive_type": "solar_reduction",
            "structured_adjustment": {"hours": [12], "factor": 0.5},
            "applies": True,
        },
        {
            "note_index": 1,
            "directive_type": "solar_reduction",
            "structured_adjustment": {"hours": [12], "factor": 0.4},
            "applies": True,
        },
    ]
    res = run_optimization(
        demand=flat_demand,
        base_solar=daytime_solar,
        tariff=flat_tariff,
        battery=simple_battery,
        raw_interpretations=dirs,
        note_count=2,
    )
    assert pytest.approx(res.hourly_schedule[12].effective_solar_kwh, rel=1e-5) == daytime_solar[12] * 0.2


def test_overlapping_no_charge_and_no_discharge(
    flat_demand: list[float],
    daytime_solar: list[float],
    flat_tariff: list[float],
    simple_battery: BatteryInput,
):
    dirs = [
        {
            "note_index": 0,
            "directive_type": "no_charge_window",
            "structured_adjustment": {"hours": [14]},
            "applies": True,
        },
        {
            "note_index": 1,
            "directive_type": "no_discharge_window",
            "structured_adjustment": {"hours": [14]},
            "applies": True,
        },
    ]
    res = run_optimization(
        demand=flat_demand,
        base_solar=daytime_solar,
        tariff=flat_tariff,
        battery=simple_battery,
        raw_interpretations=dirs,
        note_count=2,
    )
    assert res.hourly_schedule[14].battery_charge_kwh < 1e-5
    assert res.hourly_schedule[14].battery_discharge_kwh < 1e-5


# ── Edge case tests ──


def test_all_demand_zero(daytime_solar: list[float], flat_tariff: list[float], simple_battery: BatteryInput):
    res = run_optimization(
        demand=[0.0] * 24,
        base_solar=daytime_solar,
        tariff=flat_tariff,
        battery=simple_battery,
        raw_interpretations=[],
        note_count=0,
    )
    assert res.total_grid_cost_bdt == 0.0
    assert res.total_grid_kwh == 0.0
    assert all(h.grid_kwh == 0.0 for h in res.hourly_schedule)


def test_all_solar_zero(flat_demand: list[float], zero_solar: list[float], flat_tariff: list[float], simple_battery: BatteryInput):
    res = run_optimization(
        demand=flat_demand,
        base_solar=zero_solar,
        tariff=flat_tariff,
        battery=simple_battery,
        raw_interpretations=[],
        note_count=0,
    )
    assert res.solver_status == "Optimal"
    assert all(h.solar_used_kwh == 0.0 for h in res.hourly_schedule)


def test_infeasible_impossible_reserve(
    flat_demand: list[float],
    daytime_solar: list[float],
    flat_tariff: list[float],
    simple_battery: BatteryInput,
):
    # Guardrails will downgrade this to no_op if passed through raw_interpretations;
    # to test solver InfeasibleError directly, we compile an impossible directive or call optimize
    from app.services.optimizer.guardrails import CompiledDirectives
    from app.services.optimizer.lp_optimizer import OptimizationInput, optimize

    dirs = CompiledDirectives(
        solar_factor=[1.0] * 24,
        effective_solar=daytime_solar,
        min_reserve=[simple_battery.capacity_kwh + 20.0] * 24,
        no_charge=[False] * 24,
        no_discharge=[False] * 24,
        max_grid=[None] * 24,
    )
    opt_in = OptimizationInput(
        demand=flat_demand,
        tariff=flat_tariff,
        battery=simple_battery,
        compiled_directives=dirs,
    )
    with pytest.raises(InfeasibleError):
        optimize(opt_in)


def test_infeasible_impossible_max_grid(simple_battery: BatteryInput):
    dirs = [
        {
            "note_index": 0,
            "directive_type": "max_grid_window",
            "structured_adjustment": {"hours": list(range(24)), "max_grid_kwh": 0.0},
            "applies": True,
        }
    ]
    # Demand is 200 kWh every hour, but max_grid is 0, solar is 0, max discharge is only 30 kWh
    with pytest.raises(InfeasibleError):
        run_optimization(
            demand=[200.0] * 24,
            base_solar=[0.0] * 24,
            tariff=[10.0] * 24,
            battery=simple_battery,
            raw_interpretations=dirs,
            note_count=1,
        )


def test_input_wrong_length(zero_solar: list[float], flat_tariff: list[float], simple_battery: BatteryInput):
    with pytest.raises(ValueError, match="All hourly arrays must contain exactly 24 values"):
        run_optimization(
            demand=[50.0] * 23,
            base_solar=zero_solar,
            tariff=flat_tariff,
            battery=simple_battery,
            raw_interpretations=[],
            note_count=0,
        )


def test_input_negative_demand(zero_solar: list[float], flat_tariff: list[float], simple_battery: BatteryInput):
    bad_demand = [50.0] * 24
    bad_demand[5] = -1.0
    with pytest.raises(ValueError, match="Hourly values must be non-negative"):
        run_optimization(
            demand=bad_demand,
            base_solar=zero_solar,
            tariff=flat_tariff,
            battery=simple_battery,
            raw_interpretations=[],
            note_count=0,
        )


def test_input_nan_value(flat_demand: list[float], zero_solar: list[float], simple_battery: BatteryInput):
    bad_tariff = [10.0] * 24
    bad_tariff[3] = float("nan")
    with pytest.raises(ValueError, match="Non-finite values found in input"):
        run_optimization(
            demand=flat_demand,
            base_solar=zero_solar,
            tariff=bad_tariff,
            battery=simple_battery,
            raw_interpretations=[],
            note_count=0,
        )
