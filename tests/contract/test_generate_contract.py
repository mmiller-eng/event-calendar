from __future__ import annotations

from click.testing import CliRunner

from src.cli import cli
from tests.helpers import make_event


def test_missing_required_args_exits_2():
    runner = CliRunner()
    result = runner.invoke(cli, ["generate"])
    assert result.exit_code == 2


def test_non_positive_calendar_length_exits_2():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["generate", "--location", "Portland, OR", "--calendar-length-days", "0"],
    )
    assert result.exit_code == 2


def test_valid_args_exits_0_and_writes_file(monkeypatch, tmp_path):
    monkeypatch.setattr("src.cli.generate.discover_events", lambda *a, **k: [make_event()])
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
            "--output",
            str(output_file),
        ],
    )
    assert result.exit_code == 0, result.output
    assert output_file.exists()
    assert str(output_file) in result.output


def test_missing_model_config_exits_3(monkeypatch):
    monkeypatch.delenv("EVENT_CALENDAR_MODEL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["generate", "--location", "Portland, OR", "--calendar-length-days", "7"],
    )
    assert result.exit_code == 3
