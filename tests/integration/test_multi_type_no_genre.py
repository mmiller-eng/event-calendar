from __future__ import annotations

from click.testing import CliRunner

from src.cli import cli
from tests.helpers import make_event


def test_multiple_types_without_genre_includes_all_music_genres(monkeypatch, tmp_path):
    events = [
        make_event(name="Jazz Set", event_type="music", genre="jazz"),
        make_event(name="Rock Set", event_type="music", genre="rock"),
        make_event(name="Stage Play", event_type="theater", genre=None),
        make_event(name="Art Opening", event_type="art", genre=None),
    ]
    monkeypatch.setattr("src.cli.generate.discover_events", lambda *a, **k: events)

    runner = CliRunner()
    output_file = tmp_path / "multi.md"
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
            "--event-type",
            "theater",
            "--output",
            str(output_file),
        ],
    )

    assert result.exit_code == 0, result.output
    content = output_file.read_text(encoding="utf-8")
    assert "Jazz Set" in content
    assert "Rock Set" in content
    assert "Stage Play" in content
    assert "Art Opening" not in content
