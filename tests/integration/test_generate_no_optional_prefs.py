from __future__ import annotations

from click.testing import CliRunner

from src.cli import cli
from tests.helpers import make_event


def test_no_optional_preferences_includes_all_types(monkeypatch, tmp_path):
    events = [
        make_event(name="Jazz Night", event_type="music", genre="jazz"),
        make_event(name="Play Night", event_type="theater", genre=None),
    ]
    monkeypatch.setattr("src.cli.generate.discover_events", lambda *a, **k: events)

    runner = CliRunner()
    output_file = tmp_path / "all.md"
    result = runner.invoke(
        cli,
        [
            "generate",
            "--location",
            "Portland, OR",
            "--calendar-length-days",
            "14",
            "--output",
            str(output_file),
        ],
    )

    assert result.exit_code == 0, result.output
    content = output_file.read_text(encoding="utf-8")
    assert "Jazz Night" in content
    assert "Play Night" in content
