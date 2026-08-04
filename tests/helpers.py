from __future__ import annotations

from datetime import date, time, timedelta
from decimal import Decimal
from typing import Literal

from src.models.event import CulturalEvent, SourceRef


def make_event(
    *,
    name: str = "Sample Event",
    days_from_today: int = 1,
    start_time: time | Literal["unknown"] = time(19, 0),
    venue: str = "Sample Venue",
    cost: Decimal | Literal["unknown", "free"] = Decimal("10"),
    event_type: str = "music",
    genre: str | None = "jazz",
    source_kind: Literal["trusted_source", "web_search"] = "trusted_source",
    source_identifier: str = "https://example.org/events",
) -> CulturalEvent:
    return CulturalEvent(
        name=name,
        date=date.today() + timedelta(days=days_from_today),
        start_time=start_time,
        venue=venue,
        cost=cost,
        event_type=event_type,
        genre=genre,
        source_ref=SourceRef(kind=source_kind, identifier=source_identifier),
    )
