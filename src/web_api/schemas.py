"""Request/response models for the web API (data-model.md)."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator


class GenerateRequest(BaseModel):
    """POST /api/calendar request body — the web equivalent of UserPreferenceSet."""

    location: str = Field(description="Location to search for events, e.g. 'Seattle, WA'")
    calendar_length_days: int = Field(gt=0, description="Number of days ahead to include")
    max_cost: float | None = Field(default=None, description="0 = free only; omitted = no ceiling")
    event_types: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list, description="Applies only to music events")
    start_after: str | None = Field(default=None, description="HH:MM")
    start_before: str | None = Field(default=None, description="HH:MM")
    model: str | None = Field(
        default=None, description="Overrides EVENT_CALENDAR_MODEL for this request only"
    )

    @field_validator("max_cost")
    @classmethod
    def _max_cost_must_be_non_negative(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("max_cost must be >= 0")
        return value

    @model_validator(mode="after")
    def _start_window_must_be_complete(self) -> GenerateRequest:
        if bool(self.start_after) != bool(self.start_before):
            raise ValueError("start_after and start_before must both be set, or both omitted")
        return self


class EventSummary(BaseModel):
    """A flattened, browser-friendly projection of CulturalEvent."""

    name: str
    date: str
    start_time: str
    venue: str
    cost: str
    event_type: str
    genre: str | None = None
    source_url: str


class CalendarResponse(BaseModel):
    """POST /api/calendar response body."""

    output_path: str
    generated_at: str
    events: list[EventSummary]
    event_count: int


class SourceResponse(BaseModel):
    """Response body for POST/DELETE /api/sources; list item for GET /api/sources."""

    name: str
    url: str
    added_at: str
