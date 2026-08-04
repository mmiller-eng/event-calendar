"""CulturalEvent and SourceRef: a discovered event candidate, pre- and post-filtering."""

from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class SourceRef(BaseModel):
    kind: Literal["trusted_source", "web_search"]
    identifier: str


class CulturalEvent(BaseModel):
    name: str
    date: date
    start_time: time | Literal["unknown"]
    venue: str
    cost: Decimal | Literal["unknown"] | Literal["free"]
    event_type: str
    genre: str | Literal["unknown"] | None = None
    source_ref: SourceRef
