"""Unit tests for optimization and validation domain models and interface contracts."""

from __future__ import annotations

import pytest

from app.services.optimizer.interface import IOptimizer
from app.services.optimizer.models import (
    HOURS_IN_DAY,
    SUPPORTED_DIRECTIVE_TYPES,
    BatteryConfig,
    CompiledDirectives,
    HourlyEnergyData,
    HourlyEnergyProfile,
    HourlyScheduleOutput,
    NormalizedDirective,
    OptimizationInput,
    OptimizationResult,
    SolverStatus,
)
from app.services.validation.interface import (
    IReplayValidator,
)
from app.services.validation.models import ReplayValidationResult

# ─────────────────────────────────────────────────────────────────────────────
# 1. Hourly Energy Input Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_hourly_energy_data_valid() -> None:
    data = HourlyEnergyData(hour=14, demand_kwh=45.5, base_solar_kwh=30.0, tariff_bdt_per_kwh=12.0)
    assert data.hour == 14
    assert data.demand_kwh == 45.5
    assert data.base_solar_kwh == 30.0
    assert data.tariff_bdt_per_kwh == 12.0


def test_hourly_energy_data_invalid_hour() -> None:
    with pytest.raises(ValueError, match="Hour must be in range"):
        HourlyEnergyData(hour=24, demand_kwh=10.0, base_solar_kwh=0.0, tariff_bdt_per_kwh=10.0)


def test_hourly_energy_data_negative_value() -> None:
    with pytest.raises(ValueError, match="demand_kwh must be non-negative"):
        HourlyEnergyData(hour=0, demand_kwh=-5.0, base_solar_kwh=0.0, tariff_bdt_per_kwh=10.0)


def test_hourly_energy_profile_valid() -> None:
    profile = HourlyEnergyProfile(
        demand_kwh=[30.0] * 24,
        base_solar_kwh=[10.0] * 24,
        tariff_bdt_per_kwh=[8.0] * 24,
    )
    assert len(profile.demand_kwh) == 24
    snapshot = profile.get_hour(5)
    assert snapshot.hour == 5
    assert snapshot.demand_kwh == 30.0
    assert len(profile.to_hourly_list()) == 24


def test_hourly_energy_profile_wrong_length() -> None:
    with pytest.raises(ValueError, match="must contain exactly 24 values"):
        HourlyEnergyProfile(
            demand_kwh=[10.0] * 12,  # Only 12
            base_solar_kwh=[0.0] * 24,
            tariff_bdt_per_kwh=[10.0] * 24,
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Battery Configuration Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_battery_config_valid() -> None:
    battery = BatteryConfig(
        capacity_kwh=100.0,
        initial_energy_kwh=40.0,
        minimum_energy_kwh=10.0,
        max_charge_kwh_per_hour=25.0,
        max_discharge_kwh_per_hour=25.0,
    )
    assert battery.capacity_kwh == 100.0
    assert battery.initial_energy_kwh == 40.0


def test_battery_config_invalid_relationships() -> None:
    # initial energy below minimum reserve
    with pytest.raises(ValueError, match="cannot be below minimum_energy_kwh"):
        BatteryConfig(
            capacity_kwh=100.0,
            initial_energy_kwh=5.0,
            minimum_energy_kwh=10.0,
            max_charge_kwh_per_hour=25.0,
            max_discharge_kwh_per_hour=25.0,
        )

    # initial energy exceeds capacity
    with pytest.raises(ValueError, match="cannot exceed capacity_kwh"):
        BatteryConfig(
            capacity_kwh=100.0,
            initial_energy_kwh=120.0,
            minimum_energy_kwh=10.0,
            max_charge_kwh_per_hour=25.0,
            max_discharge_kwh_per_hour=25.0,
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Normalized Directives Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_supported_directive_types() -> None:
    expected = {
        "solar_reduction",
        "minimum_battery_reserve",
        "no_charge_window",
        "no_discharge_window",
        "max_grid_window",
        "no_op",
    }
    assert set(SUPPORTED_DIRECTIVE_TYPES) == expected


def test_normalized_directive_solar_reduction() -> None:
    d = NormalizedDirective(
        note_index=0,
        directive_type="solar_reduction",
        hours=[13, 14, 15],
        factor=0.2,
        applies=True,
    )
    assert d.directive_type == "solar_reduction"
    assert d.factor == 0.2
    assert d.hours == [13, 14, 15]


def test_normalized_directive_invalid_type() -> None:
    with pytest.raises(ValueError, match="Unsupported directive_type"):
        # Type error intentional for testing boundary
        NormalizedDirective(note_index=0, directive_type="unsupported_type")  # type: ignore[arg-type]


def test_compiled_directives_structure() -> None:
    cd = CompiledDirectives(
        solar_factor=[1.0] * 24,
        effective_solar=[20.0] * 24,
        min_reserve=[10.0] * 24,
        no_charge=[False] * 24,
        no_discharge=[False] * 24,
        max_grid=[None] * 24,
    )
    d = cd.to_dict()
    assert "solar_factor" in d
    assert len(d["solar_factor"]) == 24


# ─────────────────────────────────────────────────────────────────────────────
# 4. Optimization Input Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_optimization_input_creation() -> None:
    battery = BatteryConfig(100.0, 40.0, 10.0, 25.0, 25.0)
    directives = CompiledDirectives(
        solar_factor=[1.0] * 24,
        effective_solar=[15.0] * 24,
        min_reserve=[10.0] * 24,
        no_charge=[False] * 24,
        no_discharge=[False] * 24,
        max_grid=[None] * 24,
    )
    opt_input = OptimizationInput.from_arrays(
        demand_kwh=[35.0] * 24,
        base_solar_kwh=[15.0] * 24,
        tariff_bdt_per_kwh=[10.0] * 24,
        battery=battery,
        compiled_directives=directives,
    )
    assert len(opt_input.energy_profile.demand_kwh) == 24
    assert opt_input.battery.capacity_kwh == 100.0


# ─────────────────────────────────────────────────────────────────────────────
# 5. Schedule Output & Aliases Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_hourly_schedule_output_aliases() -> None:
    row = HourlyScheduleOutput(
        hour=10,
        grid_kwh=25.0,
        solar_used_kwh=15.0,
        battery_charge_kwh=0.0,
        battery_discharge_kwh=5.0,
        battery_energy_after_kwh=35.0,
    )
    # Test strict field values
    assert row.hour == 10
    assert row.grid_kwh == 25.0
    # Test challenge property aliases
    assert row.grid == 25.0
    assert row.solar_used == 15.0
    assert row.battery_charge == 0.0
    assert row.battery_discharge == 5.0
    assert row.battery_energy_after == 35.0


# ─────────────────────────────────────────────────────────────────────────────
# 6. Optimization Result Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_optimization_result_structure() -> None:
    schedule = [
        HourlyScheduleOutput(
            hour=h,
            grid_kwh=30.0,
            solar_used_kwh=10.0,
            battery_charge_kwh=0.0,
            battery_discharge_kwh=0.0,
            battery_energy_after_kwh=40.0,
        )
        for h in range(HOURS_IN_DAY)
    ]
    result = OptimizationResult(
        schedule=schedule,
        total_grid_kwh=720.0,
        total_grid_cost_bdt=7200.0,
        objective_value=7200.0,
        solver_status=SolverStatus.OPTIMAL,
        message="Optimal solution found",
    )
    assert result.solver_status == SolverStatus.OPTIMAL
    assert result.total_grid_cost_bdt == 7200.0
    assert len(result.schedule) == 24


# ─────────────────────────────────────────────────────────────────────────────
# 7. Validation Result Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_validation_result_structure() -> None:
    res = ReplayValidationResult(
        verified=True,
        max_constraint_error=1.2e-7,
        total_grid_cost_bdt=7200.0,
        violations=[],
    )
    assert res.verified is True
    assert res.max_constraint_error < 1e-5
    assert len(res.violations) == 0


# ─────────────────────────────────────────────────────────────────────────────
# 8. Protocols and Interfaces Verification
# ─────────────────────────────────────────────────────────────────────────────


def test_protocol_definitions() -> None:
    # Verify mock class satisfying IOptimizer protocol
    class MockOptimizer:
        def solve(
            self, opt_input: OptimizationInput, timeout_seconds: float = 5.0
        ) -> OptimizationResult:
            schedule = [
                HourlyScheduleOutput(h, 0.0, 0.0, 0.0, 0.0, 40.0) for h in range(HOURS_IN_DAY)
            ]
            return OptimizationResult(
                schedule=schedule,
                total_grid_kwh=0.0,
                total_grid_cost_bdt=0.0,
                objective_value=0.0,
                solver_status=SolverStatus.OPTIMAL,
            )

    mock = MockOptimizer()
    assert isinstance(mock, IOptimizer)

    # Verify mock class satisfying IReplayValidator protocol
    class MockValidator:
        def validate(
            self,
            opt_input: OptimizationInput,
            schedule: list[HourlyScheduleOutput],
            reported_total_cost: float,
            tolerance: float = 1e-4,
        ) -> ReplayValidationResult:
            return ReplayValidationResult(
                verified=True,
                max_constraint_error=0.0,
                total_grid_cost_bdt=reported_total_cost,
            )

    validator = MockValidator()
    assert isinstance(validator, IReplayValidator)
