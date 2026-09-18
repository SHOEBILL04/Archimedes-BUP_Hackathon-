"""Guardrail normalization tests: one test per documented rule."""

from __future__ import annotations

import pytest

from app.schemas.optimization import HOURS
from app.services.validation import (
    apply_solar_directives,
    normalize_directives,
)

from .conftest import directive, make_battery, make_scenario


def _normalize(directives, scenario=None):
    return normalize_directives(scenario or make_scenario(), directives)


# --------------------------------------------------------------------------- #
# Hour validation
# --------------------------------------------------------------------------- #


def test_valid_ascending_unique_hours_are_accepted():
    report = _normalize([directive("no_charge_window", {"hours": [5, 6, 7, 8]})])

    assert report.rejections == ()
    assert report.accepted == (0,)
    assert [h for h in range(HOURS) if report.normalized.no_charge[h]] == [5, 6, 7, 8]


@pytest.mark.parametrize(
    ("hours", "expected_fragment"),
    [
        ([5, 5, 6], "unique"),
        ([8, 6, 7], "ascending"),
        ([-1, 2], "out of range"),
        ([24], "out of range"),
        ([1, 2.5], "integers"),
        ([True, 2], "boolean"),
        ([], "must not be empty"),
    ],
)
def test_malformed_hours_are_rejected(hours, expected_fragment):
    report = _normalize([directive("no_charge_window", {"hours": hours})])

    assert report.accepted == ()
    assert len(report.rejections) == 1
    assert expected_fragment in report.rejections[0].reason
    # A rejected directive must not leak any constraint into the LP.
    assert not any(report.normalized.no_charge)


def test_hours_field_missing_is_rejected():
    report = _normalize([directive("no_charge_window", {})])

    assert len(report.rejections) == 1
    assert "hours" in report.rejections[0].reason


def test_integral_float_hours_are_tolerated():
    report = _normalize([directive("no_charge_window", {"hours": [5.0, 6.0]})])

    assert report.rejections == ()
    assert report.normalized.no_charge[5] is True
    assert report.normalized.no_charge[6] is True


# --------------------------------------------------------------------------- #
# Solar reduction
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("factor", [0.0, 0.2, 1.0])
def test_valid_solar_factor_applied(factor):
    report = _normalize([directive("solar_reduction", {"hours": [13], "factor": factor})])

    assert report.rejections == ()
    assert report.normalized.solar_factors[13] == pytest.approx(factor)
    # Untouched hours keep the full baseline.
    assert report.normalized.solar_factors[0] == pytest.approx(1.0)


@pytest.mark.parametrize("factor", [-0.1, 1.5])
def test_out_of_range_solar_factor_rejected(factor):
    report = _normalize([directive("solar_reduction", {"hours": [13], "factor": factor})])

    assert len(report.rejections) == 1
    assert "factor" in report.rejections[0].reason
    assert report.normalized.solar_factors[13] == pytest.approx(1.0)


def test_overlapping_solar_reductions_multiply():
    # 0.5 then 0.4 on the same hour leaves 0.2 of baseline, not 0.5 or 0.4.
    report = _normalize(
        [
            directive("solar_reduction", {"hours": [10, 11], "factor": 0.5}, note_index=0),
            directive("solar_reduction", {"hours": [11, 12], "factor": 0.4}, note_index=1),
        ]
    )

    assert report.rejections == ()
    assert report.normalized.solar_factors[10] == pytest.approx(0.5)
    assert report.normalized.solar_factors[11] == pytest.approx(0.2)
    assert report.normalized.solar_factors[12] == pytest.approx(0.4)


def test_apply_solar_directives_scales_baseline():
    report = _normalize(
        [
            directive("solar_reduction", {"hours": [1], "factor": 0.5}, note_index=0),
            directive("solar_reduction", {"hours": [1], "factor": 0.4}, note_index=1),
        ]
    )
    base = [100.0] * HOURS

    effective = apply_solar_directives(base, report.normalized)

    assert effective[1] == pytest.approx(20.0)
    assert effective[0] == pytest.approx(100.0)
    # The physical input array must not be mutated.
    assert base == [100.0] * HOURS


def test_apply_solar_directives_rejects_wrong_length():
    report = _normalize([])

    with pytest.raises(ValueError, match="exactly 24"):
        apply_solar_directives([1.0] * 23, report.normalized)


def test_solar_factor_field_missing_is_rejected():
    report = _normalize([directive("solar_reduction", {"hours": [1]})])

    assert len(report.rejections) == 1
    assert "factor" in report.rejections[0].reason


# --------------------------------------------------------------------------- #
# Minimum battery reserve
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("reserve", [0.0, 50.0, 100.0])
def test_reserve_within_capacity_accepted(reserve):
    report = _normalize(
        [directive("minimum_battery_reserve", {"hours": [3], "minimum_energy_kwh": reserve})]
    )

    assert report.rejections == ()
    assert report.normalized.minimum_reserve[3] == pytest.approx(reserve)


def test_reserve_above_capacity_rejected():
    report = _normalize(
        [directive("minimum_battery_reserve", {"hours": [3], "minimum_energy_kwh": 150.0})]
    )

    assert len(report.rejections) == 1
    assert "exceeds battery capacity" in report.rejections[0].reason
    assert report.normalized.minimum_reserve[3] == pytest.approx(0.0)


def test_negative_reserve_rejected():
    report = _normalize(
        [directive("minimum_battery_reserve", {"hours": [3], "minimum_energy_kwh": -5.0})]
    )

    assert len(report.rejections) == 1
    assert ">= 0" in report.rejections[0].reason


def test_overlapping_reserves_take_maximum():
    report = _normalize(
        [
            directive(
                "minimum_battery_reserve",
                {"hours": [5, 6], "minimum_energy_kwh": 20.0},
                note_index=0,
            ),
            directive(
                "minimum_battery_reserve",
                {"hours": [6, 7], "minimum_energy_kwh": 35.0},
                note_index=1,
            ),
        ]
    )

    assert report.normalized.minimum_reserve[5] == pytest.approx(20.0)
    assert report.normalized.minimum_reserve[6] == pytest.approx(35.0)
    assert report.normalized.minimum_reserve[7] == pytest.approx(35.0)


# --------------------------------------------------------------------------- #
# Charge / discharge windows
# --------------------------------------------------------------------------- #


def test_overlapping_no_charge_windows_union():
    report = _normalize(
        [
            directive("no_charge_window", {"hours": [5, 6, 7]}, note_index=0),
            directive("no_charge_window", {"hours": [7, 8, 9]}, note_index=1),
        ]
    )

    assert [h for h in range(HOURS) if report.normalized.no_charge[h]] == [5, 6, 7, 8, 9]
    assert not any(report.normalized.no_discharge)


def test_overlapping_no_discharge_windows_union():
    report = _normalize(
        [
            directive("no_discharge_window", {"hours": [18, 19]}, note_index=0),
            directive("no_discharge_window", {"hours": [19, 20]}, note_index=1),
        ]
    )

    assert [h for h in range(HOURS) if report.normalized.no_discharge[h]] == [18, 19, 20]
    assert not any(report.normalized.no_charge)


# --------------------------------------------------------------------------- #
# Maximum grid
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("limit", [0.0, 80.0])
def test_valid_max_grid_accepted(limit):
    report = _normalize([directive("max_grid_window", {"hours": [2], "max_grid_kwh": limit})])

    assert report.rejections == ()
    assert report.normalized.max_grid[2] == pytest.approx(limit)
    assert report.normalized.max_grid[0] is None


def test_negative_max_grid_rejected():
    report = _normalize([directive("max_grid_window", {"hours": [2], "max_grid_kwh": -1.0})])

    assert len(report.rejections) == 1
    assert ">= 0" in report.rejections[0].reason
    assert report.normalized.max_grid[2] is None


def test_overlapping_max_grid_takes_minimum():
    report = _normalize(
        [
            directive("max_grid_window", {"hours": [4], "max_grid_kwh": 100.0}, note_index=0),
            directive("max_grid_window", {"hours": [4], "max_grid_kwh": 80.0}, note_index=1),
            directive("max_grid_window", {"hours": [4], "max_grid_kwh": 60.0}, note_index=2),
        ]
    )

    assert report.normalized.max_grid[4] == pytest.approx(60.0)


# --------------------------------------------------------------------------- #
# no_op and unsupported types
# --------------------------------------------------------------------------- #


def test_no_op_produces_no_constraints():
    report = _normalize([directive("no_op", None)])

    assert report.rejections == ()
    assert report.accepted == (0,)
    normalized = report.normalized
    assert all(f == 1.0 for f in normalized.solar_factors)
    assert all(r == 0.0 for r in normalized.minimum_reserve)
    assert not any(normalized.no_charge)
    assert not any(normalized.no_discharge)
    assert all(m is None for m in normalized.max_grid)


def test_directive_marked_not_applying_produces_no_constraints():
    report = _normalize(
        [directive("no_charge_window", {"hours": [5]}, applies=False)]
    )

    assert not any(report.normalized.no_charge)


def test_unsupported_directive_type_rejected():
    # Bypass the Literal type check the way malformed LLM output would.
    bad = directive("no_op")
    object.__setattr__(bad, "directive_type", "drain_the_battery")

    report = _normalize([bad])

    assert len(report.rejections) == 1
    assert "unsupported directive type" in report.rejections[0].reason


def test_missing_structured_adjustment_rejected():
    report = _normalize([directive("solar_reduction", None)])

    assert len(report.rejections) == 1
    assert "required" in report.rejections[0].reason


def test_non_object_structured_adjustment_rejected():
    bad = directive("solar_reduction", {"hours": [1], "factor": 0.5})
    object.__setattr__(bad, "structured_adjustment", ["not", "an", "object"])

    report = _normalize([bad])

    assert len(report.rejections) == 1
    assert "JSON object" in report.rejections[0].reason


# --------------------------------------------------------------------------- #
# Integrity and determinism
# --------------------------------------------------------------------------- #


def test_guardrails_never_mutate_physical_inputs():
    scenario = make_scenario(
        demand=[12.0] * HOURS,
        base_solar=[7.0] * HOURS,
        tariff=[3.0] * HOURS,
        battery=make_battery(capacity_kwh=80.0, initial_energy_kwh=30.0),
    )
    before = scenario.model_dump()

    _normalize(
        [
            directive("solar_reduction", {"hours": [10], "factor": 0.1}, note_index=0),
            directive(
                "minimum_battery_reserve",
                {"hours": [10], "minimum_energy_kwh": 50.0},
                note_index=1,
            ),
        ],
        scenario,
    )

    assert scenario.model_dump() == before


def test_normalization_is_deterministic():
    directives = [
        directive("solar_reduction", {"hours": [10, 11], "factor": 0.5}, note_index=0),
        directive("no_charge_window", {"hours": [18, 19]}, note_index=1),
        directive("max_grid_window", {"hours": [3], "max_grid_kwh": 42.0}, note_index=2),
    ]

    results = [_normalize(directives) for _ in range(5)]

    assert all(r.normalized == results[0].normalized for r in results)
    assert all(r.rejections == results[0].rejections for r in results)


def test_valid_and_invalid_directives_coexist():
    """One malformed directive must not discard the valid ones."""
    report = _normalize(
        [
            directive("no_charge_window", {"hours": [5]}, note_index=0),
            directive("solar_reduction", {"hours": [9], "factor": 9.0}, note_index=1),
            directive("max_grid_window", {"hours": [3], "max_grid_kwh": 10.0}, note_index=2),
        ]
    )

    assert report.accepted == (0, 2)
    assert len(report.rejections) == 1
    assert report.rejections[0].note_index == 1
    assert report.normalized.no_charge[5] is True
    assert report.normalized.max_grid[3] == pytest.approx(10.0)
