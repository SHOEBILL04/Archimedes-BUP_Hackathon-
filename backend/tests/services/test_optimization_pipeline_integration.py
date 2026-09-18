"""End-to-end integration tests for the internal optimization workstream pipeline.

Verifies the integrated flow:
    validated directives
    ↓
    directive preprocessing (compiler)
    ↓
    optimization input
    ↓
    LP optimizer (PuLP + CBC)
    ↓
    candidate schedule
    ↓
    independent replay validator
    ↓
    final optimization result

Test Coverage:
1. End-to-end nominal dispatch with multiple directives applied.
2. Directives enforced in output schedule (solar reduction, no-charge, reserve, max-grid).
3. Objective value and total grid costs accurately reconciled.
4. Independent replay validation passes with zero constraint violations.
5. Infeasible energy scenario produces structured failure with empty schedule (never fakes values).
6. Infeasible reserve directive produces structured failure with empty schedule.
7. Validation failure protection: if candidate schedule fails audit, schedule is rejected (empty).
8. Convenience APIs: optimize_and_validate and optimize_arrays.
9. Strict mode exception propagation.
10. JSON serialization of pipeline result.
"""

from __future__ import annotations

import pytest

from app.services.optimizer.engine import (
    OptimizationEngine,
    OptimizationPipelineInput,
    OptimizationPipelineResult,
    optimize_and_validate,
)
from app.services.optimizer.exceptions import OptimizationInfeasibleError
from app.services.optimizer.models import (
    HOURS_IN_DAY,
    BatteryConfig,
    HourlyScheduleOutput,
    NormalizedDirective,
    OptimizationInput,
    OptimizationResult,
    SolverStatus,
)


def make_synthetic_scenario(
    peak_demand: float = 40.0,
    offpeak_demand: float = 15.0,
    solar_peak: float = 35.0,
    initial_soc: float = 30.0,
    battery_capacity: float = 100.0,
    max_rate: float = 25.0,
    directives: list[NormalizedDirective] | None = None,
) -> tuple[list[float], list[float], list[float], BatteryConfig, list[NormalizedDirective]]:
    """Generate realistic synthetic 24-hour campus energy telemetry and pricing vectors."""
    # Demand profile: lower at night, high during campus working hours 9..17
    demand = [offpeak_demand if (h < 8 or h >= 18) else peak_demand for h in range(HOURS_IN_DAY)]
    # Solar profile: bell curve centered at hour 12 (active 6..17)
    base_solar = [
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        5.0,
        15.0,
        25.0,
        32.0,
        solar_peak,
        32.0,
        25.0,
        15.0,
        5.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
    ]
    # Tariff profile: cheap off-peak (BDT 6), standard daytime (BDT 10), evening peak 17..22 (BDT 18)
    tariff = [6.0 if h < 6 else (18.0 if 17 <= h < 22 else 10.0) for h in range(HOURS_IN_DAY)]

    battery = BatteryConfig(
        capacity_kwh=battery_capacity,
        initial_energy_kwh=initial_soc,
        minimum_energy_kwh=10.0,
        max_charge_kwh_per_hour=max_rate,
        max_discharge_kwh_per_hour=max_rate,
        charge_efficiency=1.0,
        discharge_efficiency=1.0,
    )

    return demand, base_solar, tariff, battery, directives or []


# ─────────────────────────────────────────────────────────────────────────────
# 1. Nominal Integration: Full Pipeline with Multiple Directives
# ─────────────────────────────────────────────────────────────────────────────


def test_pipeline_nominal_dispatch_with_directives():
    """Verify that validated directives are preprocessed, solved, and replay-validated."""
    directives = [
        # Cloud cover reduces solar by 50% between 10..12
        NormalizedDirective(
            note_index=0, directive_type="solar_reduction", hours=[10, 11, 12], factor=0.5
        ),
        # Evening reserve requirement of 40 kWh at 18..20
        NormalizedDirective(
            note_index=1,
            directive_type="minimum_battery_reserve",
            hours=[18, 19, 20],
            minimum_energy_kwh=40.0,
        ),
        # Do not charge during evening peak tariff 17..19
        NormalizedDirective(note_index=2, directive_type="no_charge_window", hours=[17, 18, 19]),
        # Grid import ceiling of 35 kWh at hour 14
        NormalizedDirective(
            note_index=3, directive_type="max_grid_window", hours=[14], max_grid_kwh=35.0
        ),
    ]

    demand, solar, tariff, battery, dirs = make_synthetic_scenario(directives=directives)
    engine = OptimizationEngine()

    pipeline_input = OptimizationPipelineInput.from_arrays(
        demand_kwh=demand,
        base_solar_kwh=solar,
        tariff_bdt_per_kwh=tariff,
        battery=battery,
        directives=dirs,
    )

    result: OptimizationPipelineResult = engine.optimize_and_validate(pipeline_input)

    # 1. Pipeline Success & Solver Status
    assert result.is_success is True
    assert result.is_optimal is True
    assert result.status == SolverStatus.OPTIMAL
    assert "Optimal energy dispatch computed" in result.message
    assert len(result.errors) == 0

    # 2. Schedule Structure
    assert len(result.schedule) == HOURS_IN_DAY
    for h, row in enumerate(result.schedule):
        assert row.hour == h
        assert row.demand_kwh == demand[h]
        assert row.tariff_bdt_per_kwh == tariff[h]
        assert row.grid_kwh >= -1e-4
        assert row.solar_used_kwh >= -1e-4
        assert row.battery_charge_kwh >= -1e-4
        assert row.battery_discharge_kwh >= -1e-4

    # 3. Directives Enforcement in Output Schedule
    # Check effective solar reduction at hour 10: base was 35, factor was 0.5 -> effective = 17.5
    assert result.schedule[10].effective_solar_kwh == pytest.approx(17.5, abs=1e-4)
    assert result.schedule[10].solar_used_kwh <= 17.5 + 1e-4

    # Check no-charge directive at 17..19
    for h in [17, 18, 19]:
        assert result.schedule[h].battery_charge_kwh <= 1e-4

    # Check minimum reserve at 18..20
    for h in [18, 19, 20]:
        assert result.schedule[h].battery_energy_after_kwh >= 40.0 - 1e-4

    # Check max grid ceiling at 14
    assert result.schedule[14].grid_kwh <= 35.0 + 1e-4

    # 4. End-of-Day Neutrality
    assert abs(result.schedule[23].battery_energy_after_kwh - battery.initial_energy_kwh) < 1e-4

    # 5. Objective Value Calculation
    recalculated_cost = sum(row.grid_kwh * row.tariff_bdt_per_kwh for row in result.schedule)
    assert abs(result.total_grid_cost_bdt - recalculated_cost) < 1e-4
    assert abs(result.objective_value - recalculated_cost) < 1e-4

    # 6. Independent Replay Validation Audit
    assert result.is_valid is True
    assert result.validation_result is not None
    assert result.validation_result.verified is True
    assert result.validation_result.max_constraint_error < 1e-4


# ─────────────────────────────────────────────────────────────────────────────
# 2. Zero-Demand Scenario
# ─────────────────────────────────────────────────────────────────────────────


def test_pipeline_zero_demand_dispatch():
    """Verify that a zero-demand scenario produces zero grid cost and passes replay validation."""
    demand = [0.0] * HOURS_IN_DAY
    solar = [0.0] * HOURS_IN_DAY
    tariff = [10.0] * HOURS_IN_DAY
    battery = BatteryConfig(
        capacity_kwh=100.0,
        initial_energy_kwh=50.0,
        minimum_energy_kwh=10.0,
        max_charge_kwh_per_hour=25.0,
        max_discharge_kwh_per_hour=25.0,
    )

    p_in = OptimizationPipelineInput.from_arrays(
        demand_kwh=demand,
        base_solar_kwh=solar,
        tariff_bdt_per_kwh=tariff,
        battery=battery,
    )
    result = optimize_and_validate(p_in)

    assert result.is_success is True
    assert result.is_valid is True
    assert result.total_grid_cost_bdt == pytest.approx(0.0, abs=1e-4)
    assert result.total_grid_kwh == pytest.approx(0.0, abs=1e-4)
    assert len(result.schedule) == HOURS_IN_DAY


# ─────────────────────────────────────────────────────────────────────────────
# 3. Structured Failure Reporting (No Fake Schedules)
# ─────────────────────────────────────────────────────────────────────────────


def test_pipeline_infeasible_scenario_returns_structured_failure():
    """Infeasible energy constraints must return a structured failure with schedule = [].

    Scenario: Campus demands 50 kWh at hour 10, but solar is 0, battery is empty,
    and a max_grid directive sets the ceiling to 10 kWh. Impossible to meet demand.
    """
    demand = [10.0] * HOURS_IN_DAY
    demand[10] = 50.0
    solar = [0.0] * HOURS_IN_DAY
    tariff = [10.0] * HOURS_IN_DAY
    battery = BatteryConfig(
        capacity_kwh=50.0,
        initial_energy_kwh=0.0,
        minimum_energy_kwh=0.0,
        max_charge_kwh_per_hour=20.0,
        max_discharge_kwh_per_hour=20.0,
    )
    impossible_grid_directive = NormalizedDirective(
        note_index=0, directive_type="max_grid_window", hours=[10], max_grid_kwh=10.0
    )

    p_in = OptimizationPipelineInput.from_arrays(
        demand_kwh=demand,
        base_solar_kwh=solar,
        tariff_bdt_per_kwh=tariff,
        battery=battery,
        directives=[impossible_grid_directive],
    )

    engine = OptimizationEngine()
    result = engine.optimize_and_validate(p_in)

    # Must fail cleanly without manufacturing fake schedules
    assert result.is_success is False
    assert result.status == SolverStatus.INFEASIBLE
    assert result.schedule == []  # CRITICAL FAILURE RULE: NEVER MANUFACTURE VALUES
    assert len(result.errors) > 0
    assert any("infeasible" in err.lower() for err in result.errors)


def test_pipeline_infeasible_reserve_returns_structured_failure():
    """Infeasible reserve (e.g. reserve cannot be reached due to no-charge lock) fails cleanly."""
    demand = [20.0] * HOURS_IN_DAY
    solar = [0.0] * HOURS_IN_DAY
    tariff = [10.0] * HOURS_IN_DAY
    battery = BatteryConfig(
        capacity_kwh=100.0,
        initial_energy_kwh=20.0,
        minimum_energy_kwh=10.0,
        max_charge_kwh_per_hour=25.0,
        max_discharge_kwh_per_hour=25.0,
    )
    # Require 80 kWh reserve at hour 5, but prohibit charging during hours 0..4
    directives = [
        NormalizedDirective(
            note_index=0,
            directive_type="minimum_battery_reserve",
            hours=[5],
            minimum_energy_kwh=80.0,
        ),
        NormalizedDirective(
            note_index=1,
            directive_type="no_charge_window",
            hours=[0, 1, 2, 3, 4],
        ),
    ]

    p_in = OptimizationPipelineInput.from_arrays(
        demand_kwh=demand,
        base_solar_kwh=solar,
        tariff_bdt_per_kwh=tariff,
        battery=battery,
        directives=directives,
    )

    engine = OptimizationEngine()
    result = engine.optimize_and_validate(p_in)

    assert result.is_success is False
    assert result.status == SolverStatus.INFEASIBLE
    assert result.schedule == []
    assert len(result.errors) > 0


# ─────────────────────────────────────────────────────────────────────────────
# 4. Failure Rule: Replay Validation Rejection
# ─────────────────────────────────────────────────────────────────────────────


class MockDefectiveSolver:
    """Mock solver that returns an optimal status with a corrupted, physically impossible schedule."""

    def solve(self, opt_input: OptimizationInput, **kwargs) -> OptimizationResult:
        # Intentionally produce schedule that violates energy balance
        schedule = [
            HourlyScheduleOutput(
                hour=h,
                demand_kwh=20.0,
                effective_solar_kwh=0.0,
                solar_used_kwh=0.0,
                battery_charge_kwh=0.0,
                battery_discharge_kwh=0.0,
                battery_energy_after_kwh=40.0,
                grid_kwh=5.0,  # Supplies only 5 kWh for 20 kWh demand!
                tariff_bdt_per_kwh=10.0,
                grid_cost_bdt=50.0,
            )
            for h in range(HOURS_IN_DAY)
        ]
        return OptimizationResult(
            schedule=schedule,
            total_grid_kwh=120.0,
            total_grid_cost_bdt=1200.0,
            objective_value=1200.0,
            solver_status=SolverStatus.OPTIMAL,
            message="Optimal reported by defective solver",
        )


def test_pipeline_rejects_schedule_failing_replay_validation():
    """Verify that even if solver reports OPTIMAL, if replay validation fails, schedule is rejected."""
    demand = [20.0] * HOURS_IN_DAY
    solar = [0.0] * HOURS_IN_DAY
    tariff = [10.0] * HOURS_IN_DAY
    battery = BatteryConfig(
        capacity_kwh=100.0,
        initial_energy_kwh=40.0,
        minimum_energy_kwh=10.0,
        max_charge_kwh_per_hour=25.0,
        max_discharge_kwh_per_hour=25.0,
    )

    p_in = OptimizationPipelineInput.from_arrays(
        demand_kwh=demand,
        base_solar_kwh=solar,
        tariff_bdt_per_kwh=tariff,
        battery=battery,
    )

    # Engine equipped with mock solver producing corrupt schedule
    engine = OptimizationEngine(solver=MockDefectiveSolver())
    result = engine.optimize_and_validate(p_in)

    # Replay validator must catch the energy balance violation and reject the schedule
    assert result.is_success is False
    assert result.status == SolverStatus.ERROR
    assert result.schedule == []  # Rule: never return a schedule that fails validation!
    assert len(result.errors) > 0
    assert any("energy balance violation" in err for err in result.errors)
    assert result.validation_result is not None
    assert result.validation_result.is_valid is False


# ─────────────────────────────────────────────────────────────────────────────
# 5. Convenience Methods & Strict Mode
# ─────────────────────────────────────────────────────────────────────────────


def test_optimize_arrays_convenience_method():
    """Verify OptimizationEngine.optimize_arrays works seamlessly with raw arguments."""
    demand, solar, tariff, battery, _ = make_synthetic_scenario()
    engine = OptimizationEngine()

    result = engine.optimize_arrays(
        demand=demand,
        base_solar=solar,
        tariff=tariff,
        battery=battery,
    )

    assert result.is_success is True
    assert result.is_valid is True
    assert len(result.schedule) == HOURS_IN_DAY


def test_strict_mode_raises_on_infeasibility():
    """Verify strict=True raises OptimizationInfeasibleError instead of returning structured result."""
    demand = [10.0] * HOURS_IN_DAY
    demand[5] = 100.0
    solar = [0.0] * HOURS_IN_DAY
    tariff = [10.0] * HOURS_IN_DAY
    battery = BatteryConfig(
        capacity_kwh=50.0,
        initial_energy_kwh=0.0,
        minimum_energy_kwh=0.0,
        max_charge_kwh_per_hour=10.0,
        max_discharge_kwh_per_hour=10.0,
    )
    impossible_grid = NormalizedDirective(
        note_index=0, directive_type="max_grid_window", hours=[5], max_grid_kwh=10.0
    )

    p_in = OptimizationPipelineInput.from_arrays(
        demand_kwh=demand,
        base_solar_kwh=solar,
        tariff_bdt_per_kwh=tariff,
        battery=battery,
        directives=[impossible_grid],
        strict=True,
    )

    engine = OptimizationEngine()
    with pytest.raises(OptimizationInfeasibleError):
        engine.optimize_and_validate(p_in)


def test_pipeline_result_to_dict():
    """Verify serialization of OptimizationPipelineResult."""
    demand, solar, tariff, battery, _ = make_synthetic_scenario()
    result = optimize_and_validate(
        OptimizationPipelineInput.from_arrays(demand, solar, tariff, battery)
    )

    d = result.to_dict()
    assert d["success"] is True
    assert d["status"] == "OPTIMAL"
    assert d["verified"] is True
    assert len(d["schedule"]) == HOURS_IN_DAY
    assert "total_grid_cost_bdt" in d
    assert "objective_value" in d
