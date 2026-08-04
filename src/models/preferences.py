"""UserPreferenceSet: inputs for a single calendar-generation request (FR-001)."""

from __future__ import annotations

from datetime import time
from decimal import Decimal

from pydantic import BaseModel, field_validator


class UserPreferenceSet(BaseModel):
    location: str
    calendar_length_days: int
    max_cost: Decimal | None = None
    event_types: list[str] = []
    genres: list[str] = []
    start_time_window: tuple[time, time] | None = None

    @field_validator("calendar_length_days")
    @classmethod
    def _calendar_length_must_be_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("calendar_length_days must be a positive integer")
        return value

    @field_validator("max_cost")
    @classmethod
    def _max_cost_must_be_non_negative(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value < 0:
            raise ValueError("max_cost must be >= 0")
        return value
