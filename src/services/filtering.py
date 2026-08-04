"""Filtering rules (data-model.md) applied to produce the output set from candidates (FR-003)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from src.models.event import CulturalEvent
from src.models.preferences import UserPreferenceSet


def filter_events(
    events: list[CulturalEvent], preferences: UserPreferenceSet
) -> list[CulturalEvent]:
    today = date.today()
    window_end = today + timedelta(days=preferences.calendar_length_days)

    return [
        event
        for event in events
        if _in_date_range(event.date, today, window_end)
        and _type_allowed(event.event_type, preferences.event_types)
        and _genre_allowed(event.event_type, event.genre, preferences.genres)
        and _cost_allowed(event.cost, preferences.max_cost)
        and _start_time_allowed(event.start_time, preferences.start_time_window)
    ]


def _in_date_range(event_date: date, start: date, end: date) -> bool:
    return start <= event_date <= end


def _type_allowed(event_type: str, allowed_types: list[str]) -> bool:
    return not allowed_types or event_type in allowed_types


def _genre_allowed(event_type: str, genre: str | None, allowed_genres: list[str]) -> bool:
    if event_type != "music" or not allowed_genres:
        return True
    return genre in allowed_genres


def _cost_allowed(cost: Decimal | Literal["unknown", "free"], max_cost: Decimal | None) -> bool:
    if max_cost is None or cost == "unknown" or cost == "free":
        return True
    return cost <= max_cost


def _start_time_allowed(start_time, window) -> bool:
    if window is None:
        return True
    if start_time == "unknown":
        return False
    window_start, window_end = window
    return window_start <= start_time <= window_end


_FILTER_CHECKS = (
    ("date range", lambda e, p, today, end: not _in_date_range(e.date, today, end)),
    ("event type", lambda e, p, today, end: not _type_allowed(e.event_type, p.event_types)),
    (
        "genre",
        lambda e, p, today, end: not _genre_allowed(e.event_type, e.genre, p.genres),
    ),
    ("cost", lambda e, p, today, end: not _cost_allowed(e.cost, p.max_cost)),
    (
        "start time",
        lambda e, p, today, end: not _start_time_allowed(e.start_time, p.start_time_window),
    ),
)


def most_restrictive_filter(
    candidates: list[CulturalEvent], preferences: UserPreferenceSet
) -> str | None:
    """Best-effort note on which filter eliminated the most candidates (Edge Cases guidance)."""
    if not candidates:
        return None
    today = date.today()
    window_end = today + timedelta(days=preferences.calendar_length_days)

    counts = {
        label: sum(1 for event in candidates if check(event, preferences, today, window_end))
        for label, check in _FILTER_CHECKS
    }
    label, count = max(counts.items(), key=lambda kv: kv[1])
    return label if count > 0 else None
