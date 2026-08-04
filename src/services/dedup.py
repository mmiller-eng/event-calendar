"""Duplicate-event merge (dedup key + trusted-source-wins tie-break, per data-model.md, FR-007)."""

from __future__ import annotations

import re

from src.models.event import CulturalEvent

_BACKFILL_FIELDS = ("start_time", "cost", "genre")


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _dedup_key(event: CulturalEvent) -> tuple[str, object, str]:
    return (_normalize(event.name), event.date, _normalize(event.venue))


def _is_known(value: object) -> bool:
    return value != "unknown"


def _merge(primary: CulturalEvent, secondary: CulturalEvent) -> CulturalEvent:
    """Keep `primary`'s fields, backfilling any "unknown" value with a known `secondary` one."""
    updates = {}
    for field in _BACKFILL_FIELDS:
        primary_value = getattr(primary, field)
        secondary_value = getattr(secondary, field)
        if not _is_known(primary_value) and _is_known(secondary_value):
            updates[field] = secondary_value
    return primary.model_copy(update=updates) if updates else primary


def dedup_events(events: list[CulturalEvent]) -> list[CulturalEvent]:
    """Merge duplicate listings of the same real-world event into a single entry."""
    merged: dict[tuple[str, object, str], CulturalEvent] = {}
    for event in events:
        key = _dedup_key(event)
        existing = merged.get(key)
        if existing is None:
            merged[key] = event
            continue
        if existing.source_ref.kind == "trusted_source":
            primary, secondary = existing, event
        elif event.source_ref.kind == "trusted_source":
            primary, secondary = event, existing
        else:
            primary, secondary = existing, event
        merged[key] = _merge(primary, secondary)
    return list(merged.values())
