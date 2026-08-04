"""TrustedSource: an entry in the user-maintained trusted local source list (FR-002a)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, HttpUrl


class TrustedSource(BaseModel):
    name: str
    url: HttpUrl
    added_at: date
