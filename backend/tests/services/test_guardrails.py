"""Tests for deterministic directive guardrails and constraint compilation."""

from __future__ import annotations

import pytest

from app.services.optimizer.guardrails import (
    compile_directives,
    noop,
    validate_interpretations,
)


@pytest.fixture
def battery_capacity() -> float:
    return 100.0


@pytest.fixture
def battery_min() -> float:
    return 10.0


@pytest.fixture
def base_solar() -> list[float]:
    return [0.0] * 6 + [10, 20, 30, 40, 50, 60, 65, 60, 50, 40, 30, 15] + [0.0] * 6


# ── Tests for validate_interpretations() ──


def test_valid_solar_reduction(battery_capacity: float):
    raw = [
        {
            "note_index": 0,
            "directive_type": "solar_reduction",
            "structured_adjustment": {"hours": [13, 14], "factor": 0.2},
            "applies": True,
        }
    ]
    res = validate_interpretations(raw, note_count=1, battery_capacity=battery_capacity)
    assert len(res) == 1
    assert res[0]["directive_type"] == "solar_reduction"
    assert res[0]["applies"] is True
    assert res[0]["structured_adjustment"] == {"hours": [13, 14], "factor": 0.2}


def test_valid_no_charge_window(battery_capacity: float):
    raw = [
        {
            "note_index": 0,
            "directive_type": "no_charge_window",
            "structured_adjustment": {"hours": [18, 19]},
            "applies": True,
        }
    ]
    res = validate_interpretations(raw, note_count=1, battery_capacity=battery_capacity)
    assert res[0]["directive_type"] == "no_charge_window"
    assert res[0]["applies"] is True
    assert res[0]["structured_adjustment"] == {"hours": [18, 19]}


def test_valid_no_discharge_window(battery_capacity: float):
    raw = [
        {
            "note_index": 0,
            "directive_type": "no_discharge_window",
            "structured_adjustment": {"hours": [6, 7]},
            "applies": True,
        }
    ]
    res = validate_interpretations(raw, note_count=1, battery_capacity=battery_capacity)
    assert res[0]["directive_type"] == "no_discharge_window"
    assert res[0]["applies"] is True
    assert res[0]["structured_adjustment"] == {"hours": [6, 7]}


def test_valid_minimum_reserve(battery_capacity: float):
    raw = [
        {
            "note_index": 0,
            "directive_type": "minimum_battery_reserve",
            "structured_adjustment": {"hours": [20, 21], "minimum_energy_kwh": 50.0},
            "applies": True,
        }
    ]
    res = validate_interpretations(raw, note_count=1, battery_capacity=battery_capacity)
    assert res[0]["directive_type"] == "minimum_battery_reserve"
    assert res[0]["applies"] is True
    assert res[0]["structured_adjustment"] == {"hours": [20, 21], "minimum_energy_kwh": 50.0}


def test_valid_max_grid_window(battery_capacity: float):
    raw = [
        {
            "note_index": 0,
            "directive_type": "max_grid_window",
            "structured_adjustment": {"hours": [10, 11], "max_grid_kwh": 100.0},
            "applies": True,
        }
    ]
    res = validate_interpretations(raw, note_count=1, battery_capacity=battery_capacity)
    assert res[0]["directive_type"] == "max_grid_window"
    assert res[0]["applies"] is True
    assert res[0]["structured_adjustment"] == {"hours": [10, 11], "max_grid_kwh": 100.0}


def test_valid_no_op(battery_capacity: float):
    raw = [
        {
            "note_index": 0,
            "directive_type": "no_op",
            "structured_adjustment": None,
            "applies": False,
        }
    ]
    res = validate_interpretations(raw, note_count=1, battery_capacity=battery_capacity)
    assert res[0]["directive_type"] == "no_op"
    assert res[0]["applies"] is False
    assert res[0]["structured_adjustment"] is None


def test_wrong_note_count(battery_capacity: float):
    raw = [noop(0), noop(1), noop(2)]
    res = validate_interpretations(raw, note_count=2, battery_capacity=battery_capacity)
    assert len(res) == 2
    assert all(r["directive_type"] == "no_op" for r in res)


def test_out_of_order_note_indexes(battery_capacity: float):
    raw = [
        {
            "note_index": 1,
            "directive_type": "no_charge_window",
            "structured_adjustment": {"hours": [18, 19]},
            "applies": True,
        },
        {
            "note_index": 0,
            "directive_type": "solar_reduction",
            "structured_adjustment": {"hours": [13, 14], "factor": 0.2},
            "applies": True,
        },
    ]
    res = validate_interpretations(raw, note_count=2, battery_capacity=battery_capacity)
    assert [r["note_index"] for r in res] == [0, 1]
    assert res[0]["directive_type"] == "solar_reduction"
    assert res[1]["directive_type"] == "no_charge_window"


def test_duplicate_note_indexes(battery_capacity: float):
    raw = [noop(0), noop(0)]
    res = validate_interpretations(raw, note_count=2, battery_capacity=battery_capacity)
    assert len(res) == 2
    assert all(r["directive_type"] == "no_op" for r in res)


def test_invalid_hour_negative(battery_capacity: float):
    raw = [
        {
            "note_index": 0,
            "directive_type": "no_charge_window",
            "structured_adjustment": {"hours": [-1, 5]},
            "applies": True,
        }
    ]
    res = validate_interpretations(raw, note_count=1, battery_capacity=battery_capacity)
    assert res[0]["directive_type"] == "no_op"


def test_invalid_hour_too_large(battery_capacity: float):
    raw = [
        {
            "note_index": 0,
            "directive_type": "no_charge_window",
            "structured_adjustment": {"hours": [23, 24]},
            "applies": True,
        }
    ]
    res = validate_interpretations(raw, note_count=1, battery_capacity=battery_capacity)
    assert res[0]["directive_type"] == "no_op"


def test_hours_not_ascending(battery_capacity: float):
    raw = [
        {
            "note_index": 0,
            "directive_type": "no_charge_window",
            "structured_adjustment": {"hours": [14, 13]},
            "applies": True,
        }
    ]
    res = validate_interpretations(raw, note_count=1, battery_capacity=battery_capacity)
    assert res[0]["directive_type"] == "no_op"


def test_hours_not_unique(battery_capacity: float):
    raw = [
        {
            "note_index": 0,
            "directive_type": "no_charge_window",
            "structured_adjustment": {"hours": [13, 13]},
            "applies": True,
        }
    ]
    res = validate_interpretations(raw, note_count=1, battery_capacity=battery_capacity)
    assert res[0]["directive_type"] == "no_op"


def test_factor_above_1(battery_capacity: float):
    raw = [
        {
            "note_index": 0,
            "directive_type": "solar_reduction",
            "structured_adjustment": {"hours": [12, 13], "factor": 1.5},
            "applies": True,
        }
    ]
    res = validate_interpretations(raw, note_count=1, battery_capacity=battery_capacity)
    assert res[0]["directive_type"] == "no_op"


def test_factor_below_0(battery_capacity: float):
    raw = [
        {
            "note_index": 0,
            "directive_type": "solar_reduction",
            "structured_adjustment": {"hours": [12, 13], "factor": -0.1},
            "applies": True,
        }
    ]
    res = validate_interpretations(raw, note_count=1, battery_capacity=battery_capacity)
    assert res[0]["directive_type"] == "no_op"


def test_factor_zero_accepted(battery_capacity: float):
    raw = [
        {
            "note_index": 0,
            "directive_type": "solar_reduction",
            "structured_adjustment": {"hours": [12, 13], "factor": 0.0},
            "applies": True,
        }
    ]
    res = validate_interpretations(raw, note_count=1, battery_capacity=battery_capacity)
    assert res[0]["directive_type"] == "solar_reduction"
    assert res[0]["structured_adjustment"]["factor"] == 0.0


def test_factor_one_accepted(battery_capacity: float):
    raw = [
        {
            "note_index": 0,
            "directive_type": "solar_reduction",
            "structured_adjustment": {"hours": [12, 13], "factor": 1.0},
            "applies": True,
        }
    ]
    res = validate_interpretations(raw, note_count=1, battery_capacity=battery_capacity)
    assert res[0]["directive_type"] == "solar_reduction"
    assert res[0]["structured_adjustment"]["factor"] == 1.0


def test_reserve_above_capacity(battery_capacity: float):
    raw = [
        {
            "note_index": 0,
            "directive_type": "minimum_battery_reserve",
            "structured_adjustment": {"hours": [10, 11], "minimum_energy_kwh": battery_capacity + 10.0},
            "applies": True,
        }
    ]
    res = validate_interpretations(raw, note_count=1, battery_capacity=battery_capacity)
    assert res[0]["directive_type"] == "no_op"


def test_reserve_zero_accepted(battery_capacity: float):
    raw = [
        {
            "note_index": 0,
            "directive_type": "minimum_battery_reserve",
            "structured_adjustment": {"hours": [10, 11], "minimum_energy_kwh": 0.0},
            "applies": True,
        }
    ]
    res = validate_interpretations(raw, note_count=1, battery_capacity=battery_capacity)
    assert res[0]["directive_type"] == "minimum_battery_reserve"
    assert res[0]["structured_adjustment"]["minimum_energy_kwh"] == 0.0


def test_max_grid_negative(battery_capacity: float):
    raw = [
        {
            "note_index": 0,
            "directive_type": "max_grid_window",
            "structured_adjustment": {"hours": [10, 11], "max_grid_kwh": -1.0},
            "applies": True,
        }
    ]
    res = validate_interpretations(raw, note_count=1, battery_capacity=battery_capacity)
    assert res[0]["directive_type"] == "no_op"


def test_max_grid_zero_accepted(battery_capacity: float):
    raw = [
        {
            "note_index": 0,
            "directive_type": "max_grid_window",
            "structured_adjustment": {"hours": [10, 11], "max_grid_kwh": 0.0},
            "applies": True,
        }
    ]
    res = validate_interpretations(raw, note_count=1, battery_capacity=battery_capacity)
    assert res[0]["directive_type"] == "max_grid_window"
    assert res[0]["structured_adjustment"]["max_grid_kwh"] == 0.0


def test_extra_keys_rejected(battery_capacity: float):
    raw = [
        {
            "note_index": 0,
            "directive_type": "no_charge_window",
            "structured_adjustment": {"hours": [10, 11], "unexpected_key": 123},
            "applies": True,
        }
    ]
    res = validate_interpretations(raw, note_count=1, battery_capacity=battery_capacity)
    assert res[0]["directive_type"] == "no_op"


def test_missing_required_key(battery_capacity: float):
    raw = [
        {
            "note_index": 0,
            "directive_type": "solar_reduction",
            "structured_adjustment": {"hours": [10, 11]},
            "applies": True,
        }
    ]
    res = validate_interpretations(raw, note_count=1, battery_capacity=battery_capacity)
    assert res[0]["directive_type"] == "no_op"


# ── Tests for compile_directives() ──


def test_no_directives_defaults(base_solar: list[float], battery_capacity: float, battery_min: float):
    compiled = compile_directives([], base_solar, battery_capacity, battery_min)
    assert compiled.solar_factor == [1.0] * 24
    assert compiled.effective_solar == base_solar
    assert compiled.min_reserve == [battery_min] * 24
    assert compiled.no_charge == [False] * 24
    assert compiled.no_discharge == [False] * 24
    assert compiled.max_grid == [None] * 24


def test_solar_reduction_factor(base_solar: list[float], battery_capacity: float, battery_min: float):
    dirs = [
        {
            "directive_type": "solar_reduction",
            "structured_adjustment": {"hours": [12, 13], "factor": 0.25},
            "applies": True,
        }
    ]
    compiled = compile_directives(dirs, base_solar, battery_capacity, battery_min)
    assert compiled.solar_factor[12] == 0.25
    assert compiled.solar_factor[13] == 0.25
    assert compiled.solar_factor[14] == 1.0
    assert compiled.effective_solar[12] == base_solar[12] * 0.25


def test_two_solar_reductions_same_hour(base_solar: list[float], battery_capacity: float, battery_min: float):
    dirs = [
        {
            "directive_type": "solar_reduction",
            "structured_adjustment": {"hours": [12], "factor": 0.5},
            "applies": True,
        },
        {
            "directive_type": "solar_reduction",
            "structured_adjustment": {"hours": [12], "factor": 0.6},
            "applies": True,
        },
    ]
    compiled = compile_directives(dirs, base_solar, battery_capacity, battery_min)
    assert pytest.approx(compiled.solar_factor[12], rel=1e-5) == 0.3
    assert pytest.approx(compiled.effective_solar[12], rel=1e-5) == base_solar[12] * 0.3


def test_reserve_max_wins(base_solar: list[float], battery_capacity: float, battery_min: float):
    dirs = [
        {
            "directive_type": "minimum_battery_reserve",
            "structured_adjustment": {"hours": [15], "minimum_energy_kwh": 30.0},
            "applies": True,
        },
        {
            "directive_type": "minimum_battery_reserve",
            "structured_adjustment": {"hours": [15], "minimum_energy_kwh": 70.0},
            "applies": True,
        },
    ]
    compiled = compile_directives(dirs, base_solar, battery_capacity, battery_min)
    assert compiled.min_reserve[15] == 70.0
    assert compiled.min_reserve[14] == battery_min


def test_no_charge_union(base_solar: list[float], battery_capacity: float, battery_min: float):
    dirs = [
        {
            "directive_type": "no_charge_window",
            "structured_adjustment": {"hours": [10, 11]},
            "applies": True,
        },
        {
            "directive_type": "no_charge_window",
            "structured_adjustment": {"hours": [11, 12]},
            "applies": True,
        },
    ]
    compiled = compile_directives(dirs, base_solar, battery_capacity, battery_min)
    assert compiled.no_charge[10] is True
    assert compiled.no_charge[11] is True
    assert compiled.no_charge[12] is True
    assert compiled.no_charge[13] is False


def test_max_grid_min_wins(base_solar: list[float], battery_capacity: float, battery_min: float):
    dirs = [
        {
            "directive_type": "max_grid_window",
            "structured_adjustment": {"hours": [8], "max_grid_kwh": 100.0},
            "applies": True,
        },
        {
            "directive_type": "max_grid_window",
            "structured_adjustment": {"hours": [8], "max_grid_kwh": 40.0},
            "applies": True,
        },
    ]
    compiled = compile_directives(dirs, base_solar, battery_capacity, battery_min)
    assert compiled.max_grid[8] == 40.0
    assert compiled.max_grid[7] is None
