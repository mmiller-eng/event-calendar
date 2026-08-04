from __future__ import annotations

from click.testing import CliRunner

from src.cli import cli
from tests.helpers import make_event


def test_repeatable_event_type_and_genre_flags(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "src.cli.generate.discover_events",
        lambda *a, **k: [make_event(event_type="music", genre="jazz")],
    )
    runner = CliRunner()
    output_file = tmp_path / "out.md"
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
            "--genre",
            "jazz",
            "--output",
            str(output_file),
        ],
    )
    assert result.exit_code == 0, result.output
