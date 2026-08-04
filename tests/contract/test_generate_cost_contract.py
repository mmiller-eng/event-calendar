from __future__ import annotations

from click.testing import CliRunner

from src.cli import cli
from tests.helpers import make_event


def test_negative_max_cost_exits_2(monkeypatch):
    monkeypatch.setattr("src.cli.generate.discover_events", lambda *a, **k: [])
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "generate",
            "--location",
            "Portland, OR",
            "--calendar-length-days",
            "7",
            "--max-cost=-5",
        ],
    )
    assert result.exit_code == 2


def test_valid_max_cost_exits_0(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "src.cli.generate.discover_events", lambda *a, **k: [make_event(cost="free")]
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
            "7",
            "--max-cost",
            "0",
            "--output",
            str(output_file),
        ],
    )
    assert result.exit_code == 0, result.output
