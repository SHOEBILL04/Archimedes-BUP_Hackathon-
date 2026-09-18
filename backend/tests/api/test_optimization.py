from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app

# Use in-memory SQLite database for testing isolation
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

Base.metadata.create_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

SAMPLE_VALID_PAYLOAD = {
    "demand_kwh": [
        35, 34, 33, 32, 31, 30, 32, 38,
        45, 52, 58, 62, 65, 68, 70, 72,
        75, 78, 74, 68, 60, 52, 45, 40
    ],
    "base_solar_kwh": [
        0, 0, 0, 0, 0, 0, 3, 8,
        15, 22, 30, 38, 42, 44, 40, 32,
        22, 12, 5, 0, 0, 0, 0, 0
    ],
    "tariff_bdt_per_kwh": [
        8, 8, 8, 8, 8, 8, 9, 9,
        10, 10, 11, 12, 12, 13, 13, 14,
        15, 15, 14, 12, 11, 10, 9, 9
    ],
    "battery": {
        "capacity_kwh": 100,
        "initial_energy_kwh": 40,
        "minimum_energy_kwh": 10,
        "max_charge_kwh_per_hour": 25,
        "max_discharge_kwh_per_hour": 25
    },
    "operator_notes": [
        "Reduce solar from 1 PM to 3 PM by 80%",
        "Do not charge the battery from 6 PM to 8 PM"
    ]
}


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
        "capacity_kwh": 100,
        "initial_energy_kwh": 5,   # below minimum 10
        "minimum_energy_kwh": 10,
        "max_charge_kwh_per_hour": 20,
        "max_discharge_kwh_per_hour": 20
    }

    response = client.post("/api/v1/optimize-energy", json=invalid_payload)
    assert response.status_code == 422
