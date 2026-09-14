"""Contract tests for POST /api/calendar (contracts/web-contract.md)."""

from __future__ import annotations

import threading

from fastapi.testclient import TestClient

from src.web_api.app import app
from tests.helpers import make_event


def test_generate_calendar_success_returns_200_and_calendar_response(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
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


def test_generate_calendar_zero_events_returns_200_with_event_count_zero(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
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


def test_generate_calendar_concurrent_request_returns_409(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    first_request_started = threading.Event()
    release_first_request = threading.Event()

    def slow_discover(*args, **kwargs):
        first_request_started.set()
        release_first_request.wait(timeout=5)
        return [make_event()]

    monkeypatch.setattr("src.web_api.app.discover_events", slow_discover)
    client = TestClient(app)
    body = {"location": "Portland, OR", "calendar_length_days": 7}

    first_response: dict[str, object] = {}

    def run_first_request():
        response = client.post("/api/calendar", json=body)
        first_response["status_code"] = response.status_code

    first_thread = threading.Thread(target=run_first_request)
    first_thread.start()
    assert first_request_started.wait(timeout=5), "first request never started"

    second_response = client.post("/api/calendar", json=body)

    release_first_request.set()
    first_thread.join(timeout=5)

    assert second_response.status_code == 409
    assert "already in progress" in second_response.json()["detail"]
    assert first_response["status_code"] == 200

    # The lock is released after each request, including a 409 rejection --
    # a subsequent request must succeed, not be permanently locked out.
    monkeypatch.setattr("src.web_api.app.discover_events", lambda *a, **k: [make_event()])
    third_response = client.post("/api/calendar", json=body)
    assert third_response.status_code == 200
