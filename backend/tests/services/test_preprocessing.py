"""Unit tests for deterministic preprocessing of validated directives into optimization constraints.

Covers all 10 required scenarios:
1. No directives
2. One solar reduction
3. Multiple solar reductions (non-overlapping)
4. Overlapping solar reductions (multiplicative chaining, never additive)
5. No-charge window
6. No-discharge window
7. One reserve directive
8. Overlapping reserve directives (highest reserve wins)
9. Overlapping max-grid directives (smallest maximum wins)
10. Multiple directive types affecting the same hour (conflicts preserved, zero silent resolution)

Also covers protocol conformance for IDirectiveCompiler and conflict diagnostics.
"""

from __future__ import annotations

import pytest

from app.services.optimizer.models import (
    HOURS_IN_DAY,
    BatteryConfig,
    CompiledDirectives,
    NormalizedDirective,
)
from app.services.validation import (
    DeterministicDirectiveCompiler,
    IDirectiveCompiler,
    compile_directives,
    preprocess_directives,
)

BASE_SOLAR_100: list[float] = [100.0] * HOURS_IN_DAY
BASELINE_MIN_RESERVE: float = 10.0
BATTERY_CAPACITY: float = 100.0


@pytest.fixture
def battery_config() -> BatteryConfig:
    return BatteryConfig(
        capacity_kwh=BATTERY_CAPACITY,
        initial_energy_kwh=40.0,
        minimum_energy_kwh=BASELINE_MIN_RESERVE,
        max_charge_kwh_per_hour=25.0,
        max_discharge_kwh_per_hour=25.0,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. No Directives
# ─────────────────────────────────────────────────────────────────────────────


def test_1_no_directives(battery_config: BatteryConfig) -> None:
    """When no directives are provided, base solar and baseline reserves are untouched."""
    compiled: CompiledDirectives = preprocess_directives(
        directives=[],
        base_solar=BASE_SOLAR_100,
        battery_min_energy=battery_config.minimum_energy_kwh,
        battery_capacity=battery_config.capacity_kwh,
    )

    assert len(compiled.solar_factor) == HOURS_IN_DAY
    assert all(f == 1.0 for f in compiled.solar_factor)
    assert compiled.effective_solar == BASE_SOLAR_100
    assert all(r == BASELINE_MIN_RESERVE for r in compiled.min_reserve)
    assert all(not nc for nc in compiled.no_charge)
    assert all(not nd for nd in compiled.no_discharge)
    assert all(mg is None for mg in compiled.max_grid)
    assert len(compiled.conflicts) == 0


# ─────────────────────────────────────────────────────────────────────────────
# 2. One Solar Reduction
# ─────────────────────────────────────────────────────────────────────────────


def test_2_one_solar_reduction() -> None:
    """Single solar reduction applies exact factor to target hours only."""
    # base_solar = 100, factor = 0.2 -> effective_solar = 20
    d = NormalizedDirective(
        note_index=0,
        directive_type="solar_reduction",
        hours=[10, 11],
        factor=0.2,
    )
    compiled = preprocess_directives(
        directives=[d],
        base_solar=BASE_SOLAR_100,
        battery_min_energy=BASELINE_MIN_RESERVE,
    )

    for h in range(HOURS_IN_DAY):
        if h in (10, 11):
            assert compiled.solar_factor[h] == pytest.approx(0.2)
            assert compiled.effective_solar[h] == pytest.approx(20.0)
        else:
            assert compiled.solar_factor[h] == pytest.approx(1.0)
            assert compiled.effective_solar[h] == pytest.approx(100.0)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Multiple Solar Reductions (Non-overlapping)
# ─────────────────────────────────────────────────────────────────────────────


def test_3_multiple_solar_reductions_non_overlapping() -> None:
    """Multiple non-overlapping reductions apply independently."""
    d1 = NormalizedDirective(
        note_index=0,
        directive_type="solar_reduction",
        hours=[8, 9],
        factor=0.5,
    )
    d2 = NormalizedDirective(
        note_index=1,
        directive_type="solar_reduction",
        hours=[14, 15, 16],
        factor=0.8,
    )
    compiled = preprocess_directives(
        directives=[d1, d2],
        base_solar=BASE_SOLAR_100,
    )

    for h in [8, 9]:
        assert compiled.solar_factor[h] == pytest.approx(0.5)
        assert compiled.effective_solar[h] == pytest.approx(50.0)

    for h in [14, 15, 16]:
        assert compiled.solar_factor[h] == pytest.approx(0.8)
        assert compiled.effective_solar[h] == pytest.approx(80.0)

    unaffected = set(range(HOURS_IN_DAY)) - {8, 9, 14, 15, 16}
    for h in unaffected:
        assert compiled.solar_factor[h] == pytest.approx(1.0)
        assert compiled.effective_solar[h] == pytest.approx(100.0)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Overlapping Solar Reductions (Multiplicative Chaining)
# ─────────────────────────────────────────────────────────────────────────────


def test_4_overlapping_solar_reductions() -> None:
    """Overlapping reductions MUST multiply their remaining usable factors (100 * 0.5 * 0.2 = 10).

    Must NEVER add the factors together.
    """
    d1 = NormalizedDirective(
        note_index=0,
        directive_type="solar_reduction",
        hours=[10, 11, 12],
        factor=0.5,
    )
    d2 = NormalizedDirective(
        note_index=1,
        directive_type="solar_reduction",
        hours=[11, 12, 13],
        factor=0.2,
    )
    compiled = preprocess_directives(
        directives=[d1, d2],
        base_solar=BASE_SOLAR_100,
    )

    # Hour 10: only d1 applies (100 * 0.5 = 50.0)
    assert compiled.solar_factor[10] == pytest.approx(0.5)
    assert compiled.effective_solar[10] == pytest.approx(50.0)

    # Hours 11 & 12: both d1 and d2 apply: 100 * 0.5 * 0.2 = 10.0 (NOT additive!)
    assert compiled.solar_factor[11] == pytest.approx(0.1)
    assert compiled.effective_solar[11] == pytest.approx(10.0)
    assert compiled.solar_factor[12] == pytest.approx(0.1)
    assert compiled.effective_solar[12] == pytest.approx(10.0)

    # Hour 13: only d2 applies (100 * 0.2 = 20.0)
    assert compiled.solar_factor[13] == pytest.approx(0.2)
    assert compiled.effective_solar[13] == pytest.approx(20.0)


# ─────────────────────────────────────────────────────────────────────────────
# 5. No-Charge Window
# ─────────────────────────────────────────────────────────────────────────────


def test_5_no_charge_window() -> None:
    """No-charge window sets no_charge[h]=True, equivalent to battery_charge[h]=0."""
    d = NormalizedDirective(
        note_index=0,
        directive_type="no_charge_window",
        hours=[17, 18, 19, 20],
    )
    compiled = preprocess_directives(directives=[d], base_solar=BASE_SOLAR_100)

    for h in range(HOURS_IN_DAY):
        if 17 <= h <= 20:
            assert compiled.no_charge[h] is True
            assert compiled.is_charge_allowed(h) is False
        else:
            assert compiled.no_charge[h] is False
            assert compiled.is_charge_allowed(h) is True


# ─────────────────────────────────────────────────────────────────────────────
# 6. No-Discharge Window
# ─────────────────────────────────────────────────────────────────────────────


def test_6_no_discharge_window() -> None:
    """No-discharge window sets no_discharge[h]=True, equivalent to battery_discharge[h]=0."""
    d = NormalizedDirective(
        note_index=0,
        directive_type="no_discharge_window",
        hours=[0, 1, 2, 3, 4, 5],
    )
    compiled = preprocess_directives(directives=[d], base_solar=BASE_SOLAR_100)

    for h in range(HOURS_IN_DAY):
        if 0 <= h <= 5:
            assert compiled.no_discharge[h] is True
            assert compiled.is_discharge_allowed(h) is False
        else:
            assert compiled.no_discharge[h] is False
            assert compiled.is_discharge_allowed(h) is True


# ─────────────────────────────────────────────────────────────────────────────
# 7. One Reserve Directive
# ─────────────────────────────────────────────────────────────────────────────


def test_7_one_reserve_directive() -> None:
    """Single reserve directive elevates required reserve above baseline for target hours."""
    d = NormalizedDirective(
        note_index=0,
        directive_type="minimum_battery_reserve",
        hours=[10, 11],
        minimum_energy_kwh=35.0,
    )
    compiled = preprocess_directives(
        directives=[d],
        base_solar=BASE_SOLAR_100,
        battery_min_energy=BASELINE_MIN_RESERVE,
    )

    for h in range(HOURS_IN_DAY):
        if h in (10, 11):
            assert compiled.min_reserve[h] == pytest.approx(35.0)
        else:
            assert compiled.min_reserve[h] == pytest.approx(BASELINE_MIN_RESERVE)


# ─────────────────────────────────────────────────────────────────────────────
# 8. Overlapping Reserve Directives (Highest Reserve Wins)
# ─────────────────────────────────────────────────────────────────────────────


def test_8_overlapping_reserve_directives() -> None:
    """If multiple reserve directives affect the same hour, HIGHEST reserve wins."""
    d1 = NormalizedDirective(
        note_index=0,
        directive_type="minimum_battery_reserve",
        hours=[10, 11, 12],
        minimum_energy_kwh=30.0,
    )
    d2 = NormalizedDirective(
        note_index=1,
        directive_type="minimum_battery_reserve",
        hours=[11, 12, 13],
        minimum_energy_kwh=50.0,
    )
    compiled = preprocess_directives(
        directives=[d1, d2],
        base_solar=BASE_SOLAR_100,
        battery_min_energy=BASELINE_MIN_RESERVE,
    )

    # Hour 10: max(10, 30) = 30.0
    assert compiled.min_reserve[10] == pytest.approx(30.0)

    # Hours 11 & 12: max(10, 30, 50) = 50.0 (HIGHEST wins)
    assert compiled.min_reserve[11] == pytest.approx(50.0)
    assert compiled.min_reserve[12] == pytest.approx(50.0)

    # Hour 13: max(10, 50) = 50.0
    assert compiled.min_reserve[13] == pytest.approx(50.0)

    # Others: baseline 10.0
    assert compiled.min_reserve[0] == pytest.approx(10.0)


# ─────────────────────────────────────────────────────────────────────────────
# 9. Overlapping Max-Grid Directives (Smallest Maximum Wins)
# ─────────────────────────────────────────────────────────────────────────────


def test_9_overlapping_max_grid_directives() -> None:
    """If multiple max-grid directives affect the same hour, SMALLEST maximum wins."""
    d1 = NormalizedDirective(
        note_index=0,
        directive_type="max_grid_window",
        hours=[18, 19, 20],
        max_grid_kwh=25.0,
    )
    d2 = NormalizedDirective(
        note_index=1,
        directive_type="max_grid_window",
        hours=[19, 20, 21],
        max_grid_kwh=15.0,
    )
    compiled = preprocess_directives(
        directives=[d1, d2],
        base_solar=BASE_SOLAR_100,
    )

    # Hour 18: only d1 applies (25.0)
    assert compiled.max_grid[18] == pytest.approx(25.0)

    # Hours 19 & 20: both apply: min(25.0, 15.0) = 15.0 (SMALLEST wins)
    assert compiled.max_grid[19] == pytest.approx(15.0)
    assert compiled.max_grid[20] == pytest.approx(15.0)

    # Hour 21: only d2 applies (15.0)
    assert compiled.max_grid[21] == pytest.approx(15.0)

    # Unconstrained hours remain None
    assert compiled.max_grid[0] is None
    assert compiled.max_grid[22] is None


# ─────────────────────────────────────────────────────────────────────────────
# 10. Multiple Directive Types Affecting Same Hour
# ─────────────────────────────────────────────────────────────────────────────


def test_10_multiple_directive_types_same_hour() -> None:
    """Multiple distinct directive types on the exact same hour all hold simultaneously.

    None are silently resolved or dropped.
    """
    directives = [
        NormalizedDirective(
            note_index=0,
            directive_type="solar_reduction",
            hours=[12],
            factor=0.4,
        ),
        NormalizedDirective(
            note_index=1,
            directive_type="no_charge_window",
            hours=[12],
        ),
        NormalizedDirective(
            note_index=2,
            directive_type="no_discharge_window",
            hours=[12],
        ),
        NormalizedDirective(
            note_index=3,
            directive_type="minimum_battery_reserve",
            hours=[12],
            minimum_energy_kwh=40.0,
        ),
        NormalizedDirective(
            note_index=4,
            directive_type="max_grid_window",
            hours=[12],
            max_grid_kwh=20.0,
        ),
    ]

    compiled = preprocess_directives(
        directives=directives,
        base_solar=BASE_SOLAR_100,
        battery_min_energy=BASELINE_MIN_RESERVE,
    )

    # Hour 12: all 5 constraints are simultaneously active
    assert compiled.solar_factor[12] == pytest.approx(0.4)
    assert compiled.effective_solar[12] == pytest.approx(40.0)
    assert compiled.no_charge[12] is True
    assert compiled.no_discharge[12] is True
    assert compiled.has_battery_lock(12) is True
    assert compiled.min_reserve[12] == pytest.approx(40.0)
    assert compiled.max_grid[12] == pytest.approx(20.0)

    # The potential battery lock conflict was noted, not silently relaxed
    assert any("Hour 12" in c and "battery locked" in c for c in compiled.conflicts)


# ─────────────────────────────────────────────────────────────────────────────
# Conformance & Compatibility Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_compiler_protocol_conformance(battery_config: BatteryConfig) -> None:
    """DeterministicDirectiveCompiler implements IDirectiveCompiler protocol."""
    compiler = DeterministicDirectiveCompiler()
    assert isinstance(compiler, IDirectiveCompiler)

    d = NormalizedDirective(
        note_index=0,
        directive_type="solar_reduction",
        hours=[10],
        factor=0.5,
    )
    result = compiler.compile(
        directives=[d],
        base_solar=BASE_SOLAR_100,
        battery=battery_config,
    )
    assert isinstance(result, CompiledDirectives)
    assert result.effective_solar[10] == pytest.approx(50.0)


def test_compile_directives_universal_wrapper(battery_config: BatteryConfig) -> None:
    """compile_directives wrapper correctly handles direct lists and configs."""
    d = NormalizedDirective(
        note_index=0,
        directive_type="max_grid_window",
        hours=[19],
        max_grid_kwh=10.0,
    )
    res = compile_directives([d], BASE_SOLAR_100, battery_config)
    assert res.max_grid[19] == pytest.approx(10.0)
