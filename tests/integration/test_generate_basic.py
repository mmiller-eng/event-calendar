from __future__ import annotations

from click.testing import CliRunner

from src.cli import cli
from tests.helpers import make_event


def test_basic_generation_groups_by_date(monkeypatch, tmp_path):
    events = [
        make_event(name="Event A", days_from_today=2),
        make_event(name="Event B", days_from_today=5),
    ]
    monkeypatch.setattr("src.cli.generate.discover_events", lambda *a, **k: events)

    runner = CliRunner()
    output_file = tmp_path / "basic.md"
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
    assert "Event A" in content
    assert "Event B" in content
    assert content.index("Event A") < content.index("Event B")
    assert content.count("## ") == 2
