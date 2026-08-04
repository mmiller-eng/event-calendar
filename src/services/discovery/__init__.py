"""Discovery orchestrator: trusted sources first, web-search fallback second (FR-002)."""

from __future__ import annotations

import httpx

from src.config import Config
from src.llm.provider import LLMProvider
from src.models.event import CulturalEvent
from src.models.preferences import UserPreferenceSet
from src.services.discovery import trusted_source_store
from src.services.discovery.trusted_source_client import discover_from_trusted_source
from src.services.discovery.web_search_client import search_events


class DiscoveryUnavailableError(Exception):
    """No trusted sources configured and web search is unavailable — distinct from zero results."""


def discover_events(
    preferences: UserPreferenceSet,
    config: Config,
    provider: LLMProvider,
) -> list[CulturalEvent]:
    sources = trusted_source_store.load_sources(config.trusted_sources_path)

    events: list[CulturalEvent] = []
    trusted_source_errors = 0
    with httpx.Client(timeout=15.0, follow_redirects=True) as client:
        for source in sources:
            try:
                events.extend(discover_from_trusted_source(source, provider, client=client))
            except httpx.HTTPError:
                trusted_source_errors += 1

    web_search_failed = False
    if config.tavily_api_key:
        try:
            events.extend(
                search_events(
                    _build_search_query(preferences),
                    provider,
                    tavily_api_key=config.tavily_api_key,
                )
            )
        except Exception:
            web_search_failed = True

    trusted_reachable = bool(sources) and trusted_source_errors < len(sources)
    web_reachable = bool(config.tavily_api_key) and not web_search_failed
    if not trusted_reachable and not web_reachable:
        raise DiscoveryUnavailableError(
            "No trusted sources configured and web search is unavailable."
        )

    return events


def _build_search_query(preferences: UserPreferenceSet) -> str:
    parts = ["cultural events", "in", preferences.location]
    if preferences.event_types:
        parts.append("(" + " OR ".join(preferences.event_types) + ")")
    return " ".join(parts)
