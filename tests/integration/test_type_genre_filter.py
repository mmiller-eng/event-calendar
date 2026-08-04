from __future__ import annotations

from click.testing import CliRunner

from src.cli import cli
from tests.helpers import make_event


def test_music_and_genre_filter_matches_only_jazz(monkeypatch, tmp_path):
    events = [
        make_event(name="Jazz Set", event_type="music", genre="jazz"),
        make_event(name="Rock Set", event_type="music", genre="rock"),
        make_event(name="Stage Play", event_type="theater", genre=None),
    ]
    monkeypatch.setattr("src.cli.generate.discover_events", lambda *a, **k: events)

    runner = CliRunner()
    output_file = tmp_path / "jazz.md"
    result = runner.invoke(
        cli,
        [
            "generate",
            "--location",
            "Portland, OR",
            "--calendar-length-days",
            "14",
            "--event-type",
            "music",
            "--genre",
            "jazz",
            "--output",
            str(output_file),
        ],
    )

    assert result.exit_code == 0, result.output
    content = output_file.read_text(encoding="utf-8")
    assert "Jazz Set" in content
    assert "Rock Set" not in content
    assert "Stage Play" not in content
