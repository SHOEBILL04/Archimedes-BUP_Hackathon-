from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_health_returns_200() -> None:
    """GET /health should return 200 OK with status: ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_v1_health_returns_200() -> None:
    """GET /api/v1/health should return 200 OK with status: ok."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
