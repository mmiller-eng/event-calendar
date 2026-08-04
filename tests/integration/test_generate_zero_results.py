from __future__ import annotations

from click.testing import CliRunner

from src.cli import cli


def test_zero_matching_events_produces_explicit_message(monkeypatch, tmp_path):
    monkeypatch.setattr("src.cli.generate.discover_events", lambda *a, **k: [])

    runner = CliRunner()
    output_file = tmp_path / "empty.md"
    result = runner.invoke(
        cli,
        [
            "generate",
            "--location",
            "Nowhere",
            "--calendar-length-days",
            "7",
            "--output",
            str(output_file),
        ],
    )

    assert result.exit_code == 0, result.output
    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "No events matched" in content
    assert content.strip() != ""
