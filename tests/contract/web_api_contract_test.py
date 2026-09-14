"""Contract tests for POST /api/calendar (contracts/web-contract.md).

Written before the route exists (T015) — expected to fail until it does.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.web_api.app import app
from tests.helpers import make_event


def test_generate_calendar_success_returns_200_and_calendar_response(monkeypatch):
    monkeypatch.setattr("src.web_api.app.discover_events", lambda *a, **k: [make_event()])
    client = TestClient(app)

    response = client.post(
        "/api/calendar",
        json={"location": "Portland, OR", "calendar_length_days": 7},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["event_count"] == 1
    assert len(body["events"]) == 1
    assert body["events"][0]["name"] == "Sample Event"
    assert body["output_path"]
    assert body["generated_at"]


def test_generate_calendar_zero_events_returns_200_with_event_count_zero(monkeypatch):
    monkeypatch.setattr("src.web_api.app.discover_events", lambda *a, **k: [])
    client = TestClient(app)

    response = client.post(
        "/api/calendar",
        json={"location": "Nowhere", "calendar_length_days": 7},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["event_count"] == 0
    assert body["events"] == []


def test_generate_calendar_invalid_body_returns_422():
    client = TestClient(app)

    response = client.post("/api/calendar", json={"location": "Portland, OR"})

    assert response.status_code == 422


def test_generate_calendar_no_sources_reachable_returns_503():
    client = TestClient(app)

    response = client.post(
        "/api/calendar",
        json={"location": "Portland, OR", "calendar_length_days": 7},
    )

    assert response.status_code == 503, response.text
    assert "No trusted sources configured" in response.json()["detail"]
