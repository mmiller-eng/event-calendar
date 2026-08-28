from __future__ import annotations

import sys

import pytest

from src.mcp_server.client import MCPClient


@pytest.fixture
def client(_llm_env):
    print("Starting server")
    return MCPClient(command=sys.executable, args=["-m", "src.mcp_server.server"])

@pytest.fixture(autouse=True)
def _llm_env(monkeypatch, tmp_path):
    monkeypatch.setenv("EVENT_CALENDAR_MODEL", "anthropic/claude-sonnet-5")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    # An empty string (not delenv) is required: src.config's load_dotenv(override=False)
    # only skips vars already present in os.environ, so a *deleted* var gets silently
    # refilled with the real .env value when the server subprocess re-imports src.config.
    monkeypatch.setenv("TAVILY_API_KEY", "")
    monkeypatch.setenv(
        "EVENT_CALENDAR_TRUSTED_SOURCES", str(tmp_path / "trusted_sources.yaml")
    )
