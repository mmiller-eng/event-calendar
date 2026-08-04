"""Live web-search fallback client (Tavily) + LLM-based event extraction (FR-002)."""

from __future__ import annotations

from typing import Any

from tavily import TavilyClient

from src.llm.provider import LLMProvider
from src.models.event import CulturalEvent, SourceRef
from src.services.discovery._parsing import events_from_llm_payload


def search_events(
    query: str,
    provider: LLMProvider,
    *,
    tavily_api_key: str,
    tavily_client: Any | None = None,
    max_results: int = 5,
) -> list[CulturalEvent]:
    client = tavily_client or TavilyClient(api_key=tavily_api_key)
    response = client.search(query=query, max_results=max_results)
    results = response.get("results", []) if isinstance(response, dict) else []

    events: list[CulturalEvent] = []
    for result in results:
        content = result.get("content") or ""
        url = result.get("url") or query
        if not content:
            continue
        payload = provider.extract_events(content, source_description=url)
        source_ref = SourceRef(kind="web_search", identifier=url)
        events.extend(events_from_llm_payload(payload, source_ref=source_ref))
    return events
