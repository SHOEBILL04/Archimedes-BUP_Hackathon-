from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SAMPLE_VALID_PAYLOAD = {
    "demand_kwh": [
        35.0, 34.0, 33.0, 32.0, 31.0, 30.0, 32.0, 38.0,
        45.0, 52.0, 58.0, 62.0, 65.0, 68.0, 70.0, 72.0,
        75.0, 78.0, 74.0, 68.0, 60.0, 52.0, 45.0, 40.0,
    ],
    "base_solar_kwh": [
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.0, 8.0,
        15.0, 22.0, 30.0, 38.0, 42.0, 44.0, 40.0, 32.0,
        22.0, 12.0, 5.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    ],
    "tariff_bdt_per_kwh": [
        8.0, 8.0, 8.0, 8.0, 8.0, 8.0, 9.0, 9.0,
        10.0, 10.0, 11.0, 12.0, 12.0, 13.0, 13.0, 14.0,
        15.0, 15.0, 14.0, 12.0, 11.0, 10.0, 9.0, 9.0,
    ],
    "battery": {
        "capacity_kwh": 100.0,
        "initial_energy_kwh": 40.0,
        "minimum_energy_kwh": 10.0,
        "max_charge_kwh_per_hour": 25.0,
        "max_discharge_kwh_per_hour": 25.0,
    },
    "operator_notes": [
        "Reduce solar from 1 PM to 3 PM by 80%",
        "Do not charge the battery from 6 PM to 8 PM",
    ],
}


def test_root_health() -> None:
    """GET /health must return 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_api_v1_health() -> None:
    """GET /api/v1/health must return 200 OK."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"



def test_optimize_energy_placeholder_response() -> None:
    """POST /api/v1/optimize-energy should return 200 with placeholder response structure."""
    response = client.post("/api/v1/optimize-energy", json=SAMPLE_VALID_PAYLOAD)
    assert response.status_code == 200
    data = response.json()

    assert "directive_interpretation" in data
    assert len(data["directive_interpretation"]) == 2
    assert "schedule" in data
    assert len(data["schedule"]) == 24
    assert "total_grid_cost_bdt" in data
    assert "total_grid_kwh" in data
    assert "verification" in data
    assert data["verification"]["verified"] is True
    assert "status_message" in data
    assert "Optimal energy dispatch" in data["status_message"]


def test_invalid_array_length_rejected() -> None:
    """Request with array length != 24 must be rejected with 422 Unprocessable Entity."""
    invalid_payload = dict(SAMPLE_VALID_PAYLOAD)
    invalid_payload["demand_kwh"] = [10.0] * 12  # only 12 hours

    response = client.post("/api/v1/optimize-energy", json=invalid_payload)
    assert response.status_code == 422


def test_invalid_battery_relationship_rejected() -> None:
    """Initial battery energy lower than minimum reserve must be rejected."""
    invalid_payload = dict(SAMPLE_VALID_PAYLOAD)
    invalid_payload["battery"] = {
        "capacity_kwh": 100.0,
        "initial_energy_kwh": 5.0,  # less than minimum 10.0
        "minimum_energy_kwh": 10.0,
        "max_charge_kwh_per_hour": 25.0,
        "max_discharge_kwh_per_hour": 25.0,
    }

    response = client.post("/api/v1/optimize-energy", json=invalid_payload)
    assert response.status_code == 422
