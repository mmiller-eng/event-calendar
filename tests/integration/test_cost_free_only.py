from __future__ import annotations

from decimal import Decimal

from click.testing import CliRunner

from src.cli import cli
from tests.helpers import make_event


def test_free_only_excludes_priced_events(monkeypatch, tmp_path):
    events = [
        make_event(name="Free Show", cost="free"),
        make_event(name="Paid Show", cost=Decimal("20")),
    ]
    monkeypatch.setattr("src.cli.generate.discover_events", lambda *a, **k: events)

    runner = CliRunner()
    output_file = tmp_path / "free.md"
    result = runner.invoke(
        cli,
        [
            "generate",
            "--location",
            "Portland, OR",
            "--calendar-length-days",
            "14",
            "--max-cost",
            "0",
            "--output",
            str(output_file),
        ],
    )

    assert result.exit_code == 0, result.output
    content = output_file.read_text(encoding="utf-8")
    assert "Free Show" in content
    assert "Paid Show" not in content
