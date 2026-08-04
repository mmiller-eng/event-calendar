"""MarkdownCalendar: the generated output document."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, computed_field

from src.models.event import CulturalEvent
from src.models.preferences import UserPreferenceSet


class MarkdownCalendar(BaseModel):
    preferences: UserPreferenceSet
    generated_at: datetime
    events: list[CulturalEvent]
    most_restrictive_filter: str | None = None

    @computed_field
    @property
    def is_empty(self) -> bool:
        return len(self.events) == 0
