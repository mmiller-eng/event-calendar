from __future__ import annotations

from datetime import datetime

from src.models.calendar import MarkdownCalendar
from src.models.preferences import UserPreferenceSet
from src.services.markdown import render_markdown
from tests.helpers import make_event


def _preferences(**overrides):
    defaults = dict(location="Portland, OR", calendar_length_days=14)
    defaults.update(overrides)
    return UserPreferenceSet(**defaults)


def test_render_groups_events_by_date():
    events = [
        make_event(name="A", days_from_today=1),
        make_event(name="B", days_from_today=3),
    ]
    calendar = MarkdownCalendar(
        preferences=_preferences(), generated_at=datetime.now(), events=events
    )
    output = render_markdown(calendar)
    assert output.count("## ") == 2
    assert "A" in output
    assert "B" in output


def test_render_zero_results_states_no_matches():
    calendar = MarkdownCalendar(
        preferences=_preferences(),
        generated_at=datetime.now(),
        events=[],
        most_restrictive_filter="cost",
    )
    output = render_markdown(calendar)
    assert "No events matched" in output
    assert "cost" in output


def test_render_shows_unknown_and_free_cost_distinctly():
    events = [
        make_event(name="Freebie", cost="free"),
        make_event(name="Mystery", cost="unknown"),
    ]
    calendar = MarkdownCalendar(
        preferences=_preferences(), generated_at=datetime.now(), events=events
    )
    output = render_markdown(calendar)
    assert "free" in output
    assert "unknown" in output
