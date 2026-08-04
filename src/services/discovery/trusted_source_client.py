"""Fetch a trusted-source page (httpx), extract text (BeautifulSoup), extract events (LLM)."""

from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from src.llm.provider import LLMProvider
from src.models.event import CulturalEvent, SourceRef
from src.models.trusted_source import TrustedSource
from src.services.discovery._parsing import events_from_llm_payload


def fetch_text(url: str, *, client: httpx.Client | None = None) -> str:
    owns_client = client is None
    active_client = client or httpx.Client(timeout=15.0, follow_redirects=True)
    try:
        response = active_client.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.get_text(separator="\n", strip=True)
    finally:
        if owns_client:
            active_client.close()


def discover_from_trusted_source(
    source: TrustedSource,
    provider: LLMProvider,
    *,
    client: httpx.Client | None = None,
) -> list[CulturalEvent]:
    text = fetch_text(str(source.url), client=client)
    payload = provider.extract_events(text, source_description=source.name)
    source_ref = SourceRef(kind="trusted_source", identifier=str(source.url))
    return events_from_llm_payload(payload, source_ref=source_ref)
