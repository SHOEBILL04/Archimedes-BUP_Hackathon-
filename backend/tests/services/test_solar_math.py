"""Solar arithmetic: normalization factors and the pure effective-solar helper.

These tests exercise the maths directly rather than through the solver, so a
failure points at the arithmetic instead of at a dispatch decision.
"""

from __future__ import annotations

import pytest

from app.schemas.optimization import HOURS
from app.services.validation import (
    NormalizedDirectives,
    apply_solar_directives,
    normalize_directives,
)

from .conftest import directive, make_scenario


def _factors(directives) -> tuple[float, ...]:
    return normalize_directives(make_scenario(), directives).normalized.solar_factors


# --------------------------------------------------------------------------- #
# Single factor
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("factor", "base", "expected"),
    [
        (1.0, 100.0, 100.0),  # full generation remains
        (0.0, 100.0, 0.0),  # total curtailment
        (0.5, 100.0, 50.0),  # half remains
        (0.2, 100.0, 20.0),  # an "80% reduction"
    ],
)
def test_single_factor_scales_baseline(factor, base, expected):
    normalized = normalize_directives(
        make_scenario(),
        [directive("solar_reduction", {"hours": [7], "factor": factor})],
    ).normalized

    effective = apply_solar_directives([base] * HOURS, normalized)

    assert effective[7] == pytest.approx(expected)


def test_factor_one_is_the_identity():
    normalized = normalize_directives(
        make_scenario(),
        [directive("solar_reduction", {"hours": list(range(HOURS)), "factor": 1.0})],
    ).normalized

    base = [float(h) for h in range(HOURS)]
    assert list(apply_solar_directives(base, normalized)) == pytest.approx(base)


# --------------------------------------------------------------------------- #
# Compounding factors
# --------------------------------------------------------------------------- #


def test_two_factors_multiply_to_ten_percent():
    """The worked example: 100 x 0.5 x 0.2 = 10."""
    normalized = normalize_directives(
        make_scenario(),
        [
            directive("solar_reduction", {"hours": [9], "factor": 0.5}, note_index=0),
            directive("solar_reduction", {"hours": [9], "factor": 0.2}, note_index=1),
        ],
    ).normalized

    effective = apply_solar_directives([100.0] * HOURS, normalized)

    assert normalized.solar_factors[9] == pytest.approx(0.1)
    assert effective[9] == pytest.approx(10.0)


def test_three_factors_compound():
    normalized = normalize_directives(
        make_scenario(),
        [
            directive("solar_reduction", {"hours": [4], "factor": 0.5}, note_index=0),
            directive("solar_reduction", {"hours": [4], "factor": 0.5}, note_index=1),
            directive("solar_reduction", {"hours": [4], "factor": 0.5}, note_index=2),
        ],
    ).normalized

    assert normalized.solar_factors[4] == pytest.approx(0.125)


def test_zero_factor_dominates_regardless_of_order():
    """A total curtailment cannot be undone by another directive."""
    forward = _factors(
        [
            directive("solar_reduction", {"hours": [3], "factor": 0.0}, note_index=0),
            directive("solar_reduction", {"hours": [3], "factor": 0.9}, note_index=1),
        ]
    )
    reverse = _factors(
        [
            directive("solar_reduction", {"hours": [3], "factor": 0.9}, note_index=0),
            directive("solar_reduction", {"hours": [3], "factor": 0.0}, note_index=1),
        ]
    )

    assert forward[3] == pytest.approx(0.0)
    assert reverse[3] == pytest.approx(0.0)


def test_factor_combination_is_order_independent():
    """Multiplication commutes, so directive ordering cannot change the result."""
    forward = _factors(
        [
            directive("solar_reduction", {"hours": [2], "factor": 0.25}, note_index=0),
            directive("solar_reduction", {"hours": [2], "factor": 0.8}, note_index=1),
        ]
    )
    reverse = _factors(
        [
            directive("solar_reduction", {"hours": [2], "factor": 0.8}, note_index=0),
            directive("solar_reduction", {"hours": [2], "factor": 0.25}, note_index=1),
        ]
    )

    assert forward[2] == pytest.approx(reverse[2]) == pytest.approx(0.2)


def test_partially_overlapping_windows_only_compound_on_the_overlap():
    normalized = normalize_directives(
        make_scenario(),
        [
            directive("solar_reduction", {"hours": [10, 11, 12], "factor": 0.5}, note_index=0),
            directive("solar_reduction", {"hours": [12, 13, 14], "factor": 0.4}, note_index=1),
        ],
    ).normalized

    assert normalized.solar_factors[10] == pytest.approx(0.5)
    assert normalized.solar_factors[11] == pytest.approx(0.5)
    assert normalized.solar_factors[12] == pytest.approx(0.2)  # overlap
    assert normalized.solar_factors[13] == pytest.approx(0.4)
    assert normalized.solar_factors[14] == pytest.approx(0.4)


# --------------------------------------------------------------------------- #
# Untouched hours
# --------------------------------------------------------------------------- #


def test_hours_without_a_directive_keep_full_baseline():
    normalized = normalize_directives(
        make_scenario(),
        [directive("solar_reduction", {"hours": [12], "factor": 0.1})],
    ).normalized
    base = [50.0] * HOURS

    effective = apply_solar_directives(base, normalized)

    assert effective[12] == pytest.approx(5.0)
    assert all(effective[h] == pytest.approx(50.0) for h in range(HOURS) if h != 12)


def test_identity_directives_leave_every_hour_untouched():
    base = [float(h) * 2 for h in range(HOURS)]

    effective = apply_solar_directives(base, NormalizedDirectives.identity())

    assert list(effective) == pytest.approx(base)


def test_zero_baseline_stays_zero_under_any_factor():
    """Curtailing nothing still yields nothing; no division is involved."""
    normalized = normalize_directives(
        make_scenario(),
        [directive("solar_reduction", {"hours": [0, 1], "factor": 0.5})],
    ).normalized

    effective = apply_solar_directives([0.0] * HOURS, normalized)

    assert all(value == pytest.approx(0.0) for value in effective)


def test_non_solar_directives_do_not_touch_solar_factors():
    normalized = normalize_directives(
        make_scenario(),
        [
            directive("no_charge_window", {"hours": [5]}, note_index=0),
            directive("max_grid_window", {"hours": [6], "max_grid_kwh": 3.0}, note_index=1),
        ],
    ).normalized

    assert all(factor == 1.0 for factor in normalized.solar_factors)


def test_rejected_solar_directive_leaves_factors_untouched():
    normalized = normalize_directives(
        make_scenario(),
        [directive("solar_reduction", {"hours": [8], "factor": 1.5})],
    ).normalized

    assert normalized.solar_factors[8] == pytest.approx(1.0)
