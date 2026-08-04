from __future__ import annotations

from decimal import Decimal

from src.services.dedup import dedup_events
from tests.helpers import make_event


def test_duplicate_events_from_different_sources_merge():
    trusted = make_event(
        name="Jazz Night", venue="The Blue Note", cost="unknown", source_kind="trusted_source"
    )
    web = make_event(
        name="Jazz Night",
        venue="The Blue Note",
        cost=Decimal("15"),
        source_kind="web_search",
        source_identifier="https://search.example/result",
    ).model_copy(update={"date": trusted.date})

    result = dedup_events([trusted, web])

    assert len(result) == 1
    merged = result[0]
    assert merged.cost == Decimal("15")
    assert merged.source_ref.kind == "trusted_source"


def test_distinct_events_are_not_merged():
    events = [make_event(name="Show A"), make_event(name="Show B")]
    result = dedup_events(events)
    assert len(result) == 2


def test_name_and_venue_normalization_merges_case_and_whitespace_variants():
    e1 = make_event(name="Jazz  Night", venue="The Blue Note")
    e2 = make_event(name="jazz night", venue="the blue note").model_copy(
        update={"date": e1.date}
    )
    result = dedup_events([e1, e2])
    assert len(result) == 1


def test_known_value_is_not_overwritten_by_unknown():
    known = make_event(name="Jazz Night", venue="The Blue Note", cost=Decimal("15"))
    unknown = make_event(name="Jazz Night", venue="The Blue Note", cost="unknown").model_copy(
        update={"date": known.date}
    )
    result = dedup_events([known, unknown])
    assert len(result) == 1
    assert result[0].cost == Decimal("15")
