from __future__ import annotations

from decimal import Decimal

from click.testing import CliRunner

from src.cli import cli
from tests.helpers import make_event


def test_cost_ceiling_flags_unknown_and_excludes_over_budget(monkeypatch, tmp_path):
    events = [
        make_event(name="Cheap Show", cost=Decimal("20")),
        make_event(name="Pricey Show", cost=Decimal("50")),
        make_event(name="Mystery Show", cost="unknown"),
    ]
    monkeypatch.setattr("src.cli.generate.discover_events", lambda *a, **k: events)

    runner = CliRunner()
    output_file = tmp_path / "under30.md"
    result = runner.invoke(
        cli,
        [
            "generate",
            "--location",
            "Portland, OR",
            "--calendar-length-days",
            "14",
            "--max-cost",
            "30",
            "--output",
            str(output_file),
        ],
    )

    assert result.exit_code == 0, result.output
    content = output_file.read_text(encoding="utf-8")
    assert "Cheap Show" in content
    assert "Pricey Show" not in content
    assert "Mystery Show" in content
    assert "unknown" in content
