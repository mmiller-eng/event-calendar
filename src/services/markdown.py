"""Render a MarkdownCalendar -> Markdown text (FR-004, FR-005, FR-009)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from src.models.calendar import MarkdownCalendar
from src.models.event import CulturalEvent


def render_markdown(calendar: MarkdownCalendar) -> str:
    lines = [
        "# Cultural Event Calendar",
        "",
        f"_Generated: {calendar.generated_at.isoformat()}_",
        "",
        f"_Location: {calendar.preferences.location} — "
        f"{calendar.preferences.calendar_length_days} day(s)_",
        "",
    ]

    if calendar.is_empty:
        lines.append("No events matched your preferences.")
        if calendar.most_restrictive_filter:
            lines.append("")
            lines.append(
                f"The most restrictive filter was: **{calendar.most_restrictive_filter}**."
            )
        return "\n".join(lines) + "\n"

    events_by_date: dict[date, list[CulturalEvent]] = {}
    for event in sorted(calendar.events, key=_sort_key):
        events_by_date.setdefault(event.date, []).append(event)

    for event_date in sorted(events_by_date):
        lines.append(f"## {event_date.isoformat()}")
        lines.append("")
        for event in events_by_date[event_date]:
            lines.append(f"- {_render_event(event)}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _sort_key(event: CulturalEvent):
    start = event.start_time
    time_rank = (1, "") if start == "unknown" else (0, start)
    return (event.date, time_rank)


def _render_cost(cost: Decimal | Literal["unknown", "free"]) -> str:
    if cost == "free":
        return "free"
    if cost == "unknown":
        return "unknown"
    return f"${cost}"


def _render_event(event: CulturalEvent) -> str:
    start = (
        "unknown" if event.start_time == "unknown" else event.start_time.strftime("%H:%M")
    )
    parts = [
        f"**{event.name}**",
        start,
        event.venue,
        _render_cost(event.cost),
        event.event_type,
    ]
    if event.event_type == "music" and event.genre:
        parts.append(f"genre: {event.genre}")
    return " — ".join(parts)
