import json

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_optimize_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with open("sample_request.json", "r", encoding="utf-8") as f:
        payload = json.load(f)

    response = client.post("/optimize-energy", json=payload)

    # The test depends only on deterministic no_op fallback and LP behavior.
    assert response.status_code == 200

    body = response.json()
    assert len(body["directive_interpretation"]) == 2
    assert all(
        item["directive_type"] == "no_op"
        for item in body["directive_interpretation"]
    )
    assert len(body["schedule"]) == 24
    assert body["verification"]["verified"] is True
