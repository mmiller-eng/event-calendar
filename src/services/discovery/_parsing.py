"""Shared LLM-payload -> CulturalEvent parsing for discovery clients."""

from __future__ import annotations

from datetime import date, time
from decimal import Decimal, InvalidOperation

from pydantic import ValidationError

from src.models.event import CulturalEvent, SourceRef


def _parse_date(value: object) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def _parse_start_time(value: object) -> time | str:
    if value in (None, "unknown", ""):
        return "unknown"
    try:
        return time.fromisoformat(str(value))
    except ValueError:
        return "unknown"


def _parse_cost(value: object) -> Decimal | str:
    if value is None:
        return "unknown"
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("unknown", ""):
            return "unknown"
        if lowered == "free":
            return "free"
        try:
            return Decimal(lowered)
        except InvalidOperation:
            return "unknown"
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return "unknown"


def events_from_llm_payload(
    payload: list[dict], *, source_ref: SourceRef
) -> list[CulturalEvent]:
    """Never fabricate: entries missing a verifiable name/date/venue are dropped, not guessed."""
    events: list[CulturalEvent] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        event_date = _parse_date(item.get("date"))
        if event_date is None or not item.get("name") or not item.get("venue"):
            continue
        try:
            event = CulturalEvent(
                name=str(item["name"]),
                date=event_date,
                start_time=_parse_start_time(item.get("start_time")),
                venue=str(item["venue"]),
                cost=_parse_cost(item.get("cost")),
                event_type=str(item.get("event_type") or "unknown"),
                genre=item.get("genre"),
                source_ref=source_ref,
            )
        except ValidationError:
            continue
        events.append(event)
    return events
