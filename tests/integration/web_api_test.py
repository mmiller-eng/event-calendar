"""Integration test for the full POST /api/calendar generate flow.

Exercises discovery (mocked) -> dedup -> filter -> render -> write-to-disk
through the real FastAPI app, the same way tests/integration/test_cost_ceiling.py
and test_generate_basic.py exercise the CLI. Written before the route exists
(T015) — expected to fail until it does.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient

from src.web_api.app import app
from tests.helpers import make_event


def test_full_generate_flow_filters_dedupes_and_writes_file(monkeypatch, tmp_path):
    # The web API has no output_path field (data-model.md) -- the route falls
    # back to the same "calendars/<date>.md" default the CLI/MCP server use,
    # so isolate cwd rather than pollute the real project's calendars/ dir.
    monkeypatch.chdir(tmp_path)

    events = [
        make_event(name="Cheap Show", venue="The Blue Note", cost=Decimal("20")),
        make_event(
            name="Cheap Show",
            venue="The Blue Note",
            cost=Decimal("20"),
            source_kind="web_search",
            source_identifier="https://search.example/result",
        ),
        make_event(name="Pricey Show", cost=Decimal("50")),
    ]
    monkeypatch.setattr("src.web_api.app.discover_events", lambda *a, **k: events)

    client = TestClient(app)
    response = client.post(
        "/api/calendar",
        json={"location": "Portland, OR", "calendar_length_days": 14, "max_cost": 30},
    )

    assert response.status_code == 200, response.text
    body = response.json()

    # Duplicate "Cheap Show" entries (same name/venue/date) merged into one,
    # and "Pricey Show" filtered out for exceeding max_cost.
    assert body["event_count"] == 1
    assert body["events"][0]["name"] == "Cheap Show"

    output_file = Path(body["output_path"])
    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "Cheap Show" in content
    assert "Pricey Show" not in content
