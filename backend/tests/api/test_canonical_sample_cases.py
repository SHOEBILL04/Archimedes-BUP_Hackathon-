from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SAMPLE_CASES_FILE = (
    Path(__file__).resolve().parents[3]
    / "BUP_CSE_FEST_2026_Participant_Docs"
    / "BUP_CSE_FEST_2026_Preli_Public_Sample_Cases.json"
)


def load_sample_cases() -> list[dict]:
    with open(SAMPLE_CASES_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return data["cases"]


ALL_SAMPLE_CASES = load_sample_cases()


@pytest.mark.parametrize("case", ALL_SAMPLE_CASES, ids=[c["id"] for c in ALL_SAMPLE_CASES])
def test_canonical_sample_cases_end_to_end(case: dict) -> None:
    """Validate each of the 10 official BUP CSE Fest public sample cases against the API contract."""
    payload = case["input"]
    expected_out = case["expected_output"]

    # 1. Send exact official judge input shape to POST /optimize-energy
    response = client.post("/optimize-energy", json=payload)
    assert response.status_code == 200, f"Failed on {case['id']}: {response.text}"

    data = response.json()

    # 2. Check canonical Section 10 top-level fields
    assert "scenario_id" in data
    assert data["scenario_id"] == payload["scenario_id"]
    assert "directive_interpretation" in data
    assert len(data["directive_interpretation"]) == len(payload["operator_notes"])
    assert "hourly_plan" in data
    assert len(data["hourly_plan"]) == 24
    assert "total_grid_kwh" in data
    assert "total_cost_bdt" in data
    assert "peak_grid_kwh" in data
    assert "plan_summary" in data

    # 3. Directive interpretation checks
    for idx, interp in enumerate(data["directive_interpretation"]):
        assert interp["note_index"] == idx
        assert "applies" in interp
        assert "directive_type" in interp
        assert interp["directive_type"] in [
            "solar_reduction",
            "minimum_battery_reserve",
            "no_charge_window",
            "no_discharge_window",
            "max_grid_window",
            "no_op",
        ]
        if interp["directive_type"] == "no_op":
            assert interp["applies"] is False
            assert interp["structured_adjustment"] is None
        else:
            assert interp["applies"] is True
            assert isinstance(interp["structured_adjustment"], dict)
            assert "hours" in interp["structured_adjustment"]
            hours = interp["structured_adjustment"]["hours"]
            assert hours == sorted(list(set(hours)))
            assert all(0 <= h <= 23 for h in hours)

    # 4. Hourly plan checks (Section 10.3)
    initial_energy = payload["battery"]["initial_energy_kwh"]
    capacity = payload["battery"]["capacity_kwh"]
    min_reserve = payload["battery"]["minimum_energy_kwh"]
    max_charge = payload["battery"]["max_charge_kwh_per_hour"]
    max_discharge = payload["battery"]["max_discharge_kwh_per_hour"]

    recalculated_cost = 0.0
    recalculated_grid_kwh = 0.0
    hourly_demands = {h["hour"]: h["demand_kwh"] for h in payload["hours"]}
    hourly_tariffs = {h["hour"]: h["tariff_bdt_per_kwh"] for h in payload["hours"]}

    prev_energy = initial_energy
    for h in data["hourly_plan"]:
        hour = h["hour"]
        assert 0 <= hour <= 23
        assert h["grid_kwh"] >= 0.0
        assert h["solar_used_kwh"] >= 0.0
        assert h["battery_action"] in ["charge", "discharge", "idle"]
        assert h["battery_kwh"] >= 0.0
        if h["battery_action"] == "idle":
            assert h["battery_kwh"] == 0.0
        elif h["battery_action"] == "charge":
            assert h["battery_kwh"] <= max_charge + 1e-4
            assert abs(h["battery_energy_after_kwh"] - (prev_energy + h["battery_kwh"])) < 0.05
        elif h["battery_action"] == "discharge":
            assert h["battery_kwh"] <= max_discharge + 1e-4
            assert abs(h["battery_energy_after_kwh"] - (prev_energy - h["battery_kwh"])) < 0.05

        assert min_reserve - 1e-4 <= h["battery_energy_after_kwh"] <= capacity + 1e-4
        prev_energy = h["battery_energy_after_kwh"]

        # Recalculate cost
        tariff = hourly_tariffs[hour]
        recalculated_cost += h["grid_kwh"] * tariff
        recalculated_grid_kwh += h["grid_kwh"]

    # 5. End-of-day battery neutrality (Section 09.6)
    final_energy = data["hourly_plan"][23]["battery_energy_after_kwh"]
    assert abs(final_energy - initial_energy) < 0.05

    # 6. Check reported totals match recalculated values (Section 11.3)
    assert abs(data["total_cost_bdt"] - recalculated_cost) < 0.05
    assert abs(data["total_grid_kwh"] - recalculated_grid_kwh) < 0.05

    # 7. Check peak_grid_kwh matches max
    expected_peak = max(h["grid_kwh"] for h in data["hourly_plan"])
    assert abs(data["peak_grid_kwh"] - expected_peak) < 0.05

    # 8. Check optimization cost matches organizer reference optimal cost
    expected_cost = expected_out["total_cost_bdt"]
    assert abs(data["total_cost_bdt"] - expected_cost) <= 0.05, (
        f"Cost mismatch on {case['id']}: got {data['total_cost_bdt']}, expected {expected_cost}"
    )
