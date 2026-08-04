from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _llm_env(monkeypatch, tmp_path):
    monkeypatch.setenv("EVENT_CALENDAR_MODEL", "anthropic/claude-sonnet-5")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setenv(
        "EVENT_CALENDAR_TRUSTED_SOURCES", str(tmp_path / "trusted_sources.yaml")
    )
