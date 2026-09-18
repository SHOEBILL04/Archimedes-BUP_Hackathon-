"""Unit tests for deterministic directive guardrail and validation layer.

Covers all 13 required scenarios:
1. Valid solar reduction
2. Invalid solar reduction factor
3. Valid reserve
4. Reserve above capacity
5. Valid no-charge window
6. Invalid hour
7. Duplicate hour
8. Unsorted hours
9. Valid no-discharge window
10. Valid max-grid directive
11. Negative max-grid value
12. Unknown directive type
13. Valid no_op

Also covers additional boundary, batch, and interface conformance tests.
"""

from __future__ import annotations

import pytest

from app.services.optimizer.models import NormalizedDirective
from app.services.validation import (
    BatchDirectiveValidationResult,
    DeterministicDirectiveGuardrail,
    GuardrailValidationError,
    IDirectiveGuardrail,
    validate_directive,
    validate_directive_batch,
    validate_directive_batch_strict,
    validate_directive_strict,
)

BATTERY_CAPACITY_KWH = 100.0


# ─────────────────────────────────────────────────────────────────────────────
# Required Test 1: Valid solar reduction
# ─────────────────────────────────────────────────────────────────────────────


def test_1_valid_solar_reduction() -> None:
    raw = {
        "note_index": 0,
        "directive_type": "solar_reduction",
        "hours": [10, 11, 12, 13],
        "factor": 0.5,
    }
    res = validate_directive(raw)
    assert res.is_valid is True
    assert len(res.errors) == 0
    assert isinstance(res.directive, NormalizedDirective)
    assert res.directive.directive_type == "solar_reduction"
    assert res.directive.hours == [10, 11, 12, 13]
    assert res.directive.factor == 0.5
    assert res.directive.applies is True

    # Test nested structured_adjustment format as well
    nested_raw = {
        "note_index": 0,
        "directive_type": "solar_reduction",
        "structured_adjustment": {"hours": [10, 11, 12, 13], "factor": 0.5},
    }
    res_nested = validate_directive(nested_raw)
    assert res_nested.is_valid is True
    assert res_nested.directive == res.directive


# ─────────────────────────────────────────────────────────────────────────────
# Required Test 2: Invalid solar reduction factor
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("bad_factor", [1.5, -0.2, 2.0, -0.01])
def test_2_invalid_solar_reduction_factor(bad_factor: float) -> None:
    raw = {
        "note_index": 0,
        "directive_type": "solar_reduction",
        "hours": [10, 11, 12],
        "factor": bad_factor,
    }
    res = validate_directive(raw)
    assert res.is_valid is False
    assert res.directive is None
    codes = [e.code for e in res.errors]
    assert "FACTOR_OUT_OF_BOUNDS" in codes

    with pytest.raises(GuardrailValidationError) as exc_info:
        validate_directive_strict(raw)
    assert "FACTOR_OUT_OF_BOUNDS" in str(exc_info.value) or "factor" in str(exc_info.value)


def test_2b_missing_or_non_numeric_factor() -> None:
    # Missing factor
    raw_missing = {
        "note_index": 0,
        "directive_type": "solar_reduction",
        "hours": [10, 11],
    }
    res_missing = validate_directive(raw_missing)
    assert res_missing.is_valid is False
    assert any(e.code == "MISSING_FACTOR" for e in res_missing.errors)

    # Non-numeric factor (e.g. boolean or string)
    raw_bool = {
        "note_index": 0,
        "directive_type": "solar_reduction",
        "hours": [10, 11],
        "factor": True,
    }
    res_bool = validate_directive(raw_bool)
    assert res_bool.is_valid is False
    assert any(e.code == "INVALID_FACTOR_TYPE" for e in res_bool.errors)


# ─────────────────────────────────────────────────────────────────────────────
# Required Test 3: Valid reserve
# ─────────────────────────────────────────────────────────────────────────────


def test_3_valid_reserve() -> None:
    raw = {
        "note_index": 1,
        "directive_type": "minimum_battery_reserve",
        "hours": [1, 2, 3, 4],
        "minimum_energy_kwh": 30.0,
    }
    res = validate_directive(raw, battery_capacity=BATTERY_CAPACITY_KWH)
    assert res.is_valid is True
    assert res.directive is not None
    assert res.directive.directive_type == "minimum_battery_reserve"
    assert res.directive.hours == [1, 2, 3, 4]
    assert res.directive.minimum_energy_kwh == 30.0
    assert res.directive.applies is True

    # Also accepts 'reserve' key
    raw_alias = {
        "note_index": 1,
        "directive_type": "minimum_battery_reserve",
        "hours": [1, 2, 3, 4],
        "reserve": 30.0,
    }
    res_alias = validate_directive(raw_alias, battery_capacity=BATTERY_CAPACITY_KWH)
    assert res_alias.is_valid is True
    assert res_alias.directive.minimum_energy_kwh == 30.0


# ─────────────────────────────────────────────────────────────────────────────
# Required Test 4: Reserve above capacity
# ─────────────────────────────────────────────────────────────────────────────


def test_4_reserve_above_capacity() -> None:
    raw = {
        "note_index": 1,
        "directive_type": "minimum_battery_reserve",
        "hours": [1, 2, 3, 4],
        "minimum_energy_kwh": 150.0,  # exceeds 100.0
    }
    res = validate_directive(raw, battery_capacity=BATTERY_CAPACITY_KWH)
    assert res.is_valid is False
    assert res.directive is None
    assert any(e.code == "RESERVE_EXCEEDS_CAPACITY" for e in res.errors)

    with pytest.raises(GuardrailValidationError):
        validate_directive_strict(raw, battery_capacity=BATTERY_CAPACITY_KWH)


def test_4b_negative_reserve() -> None:
    raw = {
        "note_index": 1,
        "directive_type": "minimum_battery_reserve",
        "hours": [1, 2],
        "minimum_energy_kwh": -10.0,
    }
    res = validate_directive(raw, battery_capacity=BATTERY_CAPACITY_KWH)
    assert res.is_valid is False
    assert any(e.code == "NEGATIVE_RESERVE" for e in res.errors)


# ─────────────────────────────────────────────────────────────────────────────
# Required Test 5: Valid no-charge window
# ─────────────────────────────────────────────────────────────────────────────


def test_5_valid_no_charge_window() -> None:
    raw = {
        "note_index": 2,
        "directive_type": "no_charge_window",
        "hours": [17, 18, 19, 20],
    }
    res = validate_directive(raw)
    assert res.is_valid is True
    assert res.directive is not None
    assert res.directive.directive_type == "no_charge_window"
    assert res.directive.hours == [17, 18, 19, 20]
    assert res.directive.applies is True


# ─────────────────────────────────────────────────────────────────────────────
# Required Test 6: Invalid hour
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("bad_hour", [24, -1, 100, -20])
def test_6_invalid_hour_bounds(bad_hour: int) -> None:
    raw = {
        "note_index": 0,
        "directive_type": "no_charge_window",
        "hours": [10, bad_hour],
    }
    res = validate_directive(raw)
    assert res.is_valid is False
    assert any(e.code == "HOUR_OUT_OF_BOUNDS" for e in res.errors)


@pytest.mark.parametrize("non_int_hour", [10.5, "12", True, None])
def test_6b_non_integer_hour(non_int_hour: object) -> None:
    raw = {
        "note_index": 0,
        "directive_type": "no_charge_window",
        "hours": [1, non_int_hour, 3],
    }
    res = validate_directive(raw)
    assert res.is_valid is False
    assert any(e.code == "INVALID_HOUR_TYPE" for e in res.errors)


# ─────────────────────────────────────────────────────────────────────────────
# Required Test 7: Duplicate hour
# ─────────────────────────────────────────────────────────────────────────────


def test_7_duplicate_hour() -> None:
    raw = {
        "note_index": 0,
        "directive_type": "no_charge_window",
        "hours": [10, 10, 11],
    }
    res = validate_directive(raw)
    assert res.is_valid is False
    assert any(e.code == "DUPLICATE_HOURS" for e in res.errors)

    with pytest.raises(GuardrailValidationError):
        validate_directive_strict(raw)


# ─────────────────────────────────────────────────────────────────────────────
# Required Test 8: Unsorted hours
# ─────────────────────────────────────────────────────────────────────────────


def test_8_unsorted_hours() -> None:
    raw = {
        "note_index": 0,
        "directive_type": "no_charge_window",
        "hours": [14, 10],
    }
    res = validate_directive(raw)
    assert res.is_valid is False
    assert any(e.code == "UNSORTED_HOURS" for e in res.errors)

    with pytest.raises(GuardrailValidationError):
        validate_directive_strict(raw)


# ─────────────────────────────────────────────────────────────────────────────
# Required Test 9: Valid no-discharge window
# ─────────────────────────────────────────────────────────────────────────────


def test_9_valid_no_discharge_window() -> None:
    raw = {
        "note_index": 3,
        "directive_type": "no_discharge_window",
        "hours": [0, 1, 2, 3, 4, 5],
    }
    res = validate_directive(raw)
    assert res.is_valid is True
    assert res.directive is not None
    assert res.directive.directive_type == "no_discharge_window"
    assert res.directive.hours == [0, 1, 2, 3, 4, 5]
    assert res.directive.applies is True


# ─────────────────────────────────────────────────────────────────────────────
# Required Test 10: Valid max-grid directive
# ─────────────────────────────────────────────────────────────────────────────


def test_10_valid_max_grid_directive() -> None:
    raw = {
        "note_index": 4,
        "directive_type": "max_grid_window",
        "hours": [18, 19, 20, 21],
        "max_grid_kwh": 15.0,
    }
    res = validate_directive(raw)
    assert res.is_valid is True
    assert res.directive is not None
    assert res.directive.directive_type == "max_grid_window"
    assert res.directive.hours == [18, 19, 20, 21]
    assert res.directive.max_grid_kwh == 15.0
    assert res.directive.applies is True

    # Also accepts 'max_grid' key
    raw_alias = {
        "note_index": 4,
        "directive_type": "max_grid_window",
        "hours": [18, 19],
        "max_grid": 10.0,
    }
    res_alias = validate_directive(raw_alias)
    assert res_alias.is_valid is True
    assert res_alias.directive.max_grid_kwh == 10.0


# ─────────────────────────────────────────────────────────────────────────────
# Required Test 11: Negative max-grid value
# ─────────────────────────────────────────────────────────────────────────────


def test_11_negative_max_grid_value() -> None:
    raw = {
        "note_index": 4,
        "directive_type": "max_grid_window",
        "hours": [18, 19],
        "max_grid_kwh": -5.0,
    }
    res = validate_directive(raw)
    assert res.is_valid is False
    assert any(e.code == "NEGATIVE_MAX_GRID" for e in res.errors)

    with pytest.raises(GuardrailValidationError):
        validate_directive_strict(raw)


# ─────────────────────────────────────────────────────────────────────────────
# Required Test 12: Unknown directive type
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "bad_type",
    [
        "battery_boost",
        "curtail_wind",
        "unknown_op",
        "",
        "solar_boost",
        123,
    ],
)
def test_12_unknown_directive_type(bad_type: object) -> None:
    raw = {
        "note_index": 0,
        "directive_type": bad_type,
        "hours": [10, 11],
    }
    res = validate_directive(raw)
    assert res.is_valid is False
    assert any(e.code == "UNKNOWN_DIRECTIVE_TYPE" for e in res.errors)

    with pytest.raises(GuardrailValidationError):
        validate_directive_strict(raw)


# ─────────────────────────────────────────────────────────────────────────────
# Required Test 13: Valid no_op
# ─────────────────────────────────────────────────────────────────────────────


def test_13_valid_no_op() -> None:
    raw = {
        "note_index": 5,
        "directive_type": "no_op",
    }
    res = validate_directive(raw)
    assert res.is_valid is True
    assert res.directive is not None
    assert res.directive.directive_type == "no_op"
    # Must not impose physical constraints
    assert res.directive.applies is False
    assert res.directive.hours == []
    assert res.directive.factor is None
    assert res.directive.minimum_energy_kwh is None
    assert res.directive.max_grid_kwh is None


def test_13b_no_op_with_invalid_hours_rejected() -> None:
    # If a no_op explicitly contains invalid hours, hour rules must still be enforced
    raw = {
        "note_index": 5,
        "directive_type": "no_op",
        "hours": [24, -1],
    }
    res = validate_directive(raw)
    assert res.is_valid is False
    assert any(e.code == "HOUR_OUT_OF_BOUNDS" for e in res.errors)


# ─────────────────────────────────────────────────────────────────────────────
# Batch Validation and IDirectiveGuardrail Conformance Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_batch_validation_success() -> None:
    batch_raw = [
        {
            "directive_type": "solar_reduction",
            "hours": [11, 12, 13],
            "factor": 0.8,
        },
        {
            "directive_type": "no_charge_window",
            "hours": [17, 18, 19],
        },
        {
            "directive_type": "no_op",
        },
    ]
    batch_res: BatchDirectiveValidationResult = validate_directive_batch(
        batch_raw, battery_capacity=BATTERY_CAPACITY_KWH
    )
    assert batch_res.is_valid is True
    assert len(batch_res.directives) == 3
    assert len(batch_res.errors) == 0

    strict_list = validate_directive_batch_strict(batch_raw, battery_capacity=BATTERY_CAPACITY_KWH)
    assert len(strict_list) == 3


def test_batch_validation_failure_contains_all_errors() -> None:
    batch_raw = [
        {
            "directive_type": "solar_reduction",
            "hours": [11, 12],
            "factor": 1.5,  # Error 1
        },
        {
            "directive_type": "unknown_type",  # Error 2
            "hours": [17, 18],
        },
        {
            "directive_type": "no_charge_window",
            "hours": [20, 19],  # Error 3: unsorted
        },
    ]
    batch_res = validate_directive_batch(batch_raw)
    assert batch_res.is_valid is False
    assert len(batch_res.directives) == 0
    assert len(batch_res.errors) >= 3

    with pytest.raises(GuardrailValidationError) as exc:
        validate_directive_batch_strict(batch_raw)
    assert len(exc.value.errors) >= 3


def test_guardrail_class_protocol_conformance() -> None:
    guardrail = DeterministicDirectiveGuardrail()
    assert isinstance(guardrail, IDirectiveGuardrail)

    # Test sanitize fallback
    raw_directives = [
        {"note_index": 0, "directive_type": "solar_reduction", "hours": [10], "factor": 0.5},
        {"note_index": 1, "directive_type": "bad_type", "hours": [11]},  # should degrade to no_op
    ]
    sanitized = guardrail.sanitize(raw_directives, note_count=2, battery_capacity=100.0)
    assert len(sanitized) == 2
    assert sanitized[0].directive_type == "solar_reduction"
    assert sanitized[0].applies is True
    assert sanitized[1].directive_type == "no_op"
    assert sanitized[1].applies is False
