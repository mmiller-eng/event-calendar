"""`calendar generate` command: discovery -> filter -> dedup -> render -> write file."""

from __future__ import annotations

from datetime import datetime
from datetime import time as time_cls
from decimal import Decimal
from pathlib import Path

import click

from src.config import load_config
from src.llm.provider import LLMProvider, MissingConfigError
from src.models.calendar import MarkdownCalendar
from src.models.preferences import UserPreferenceSet
from src.services import dedup, filtering, markdown
from src.services.discovery import DiscoveryUnavailableError, discover_events


@click.command("generate")
@click.option("--location", required=True)
@click.option("--calendar-length-days", required=True, type=int)
@click.option("--max-cost", "max_cost", default=None, type=Decimal)
@click.option("--event-type", "event_types", multiple=True)
@click.option("--genre", "genres", multiple=True)
@click.option("--start-after", default=None)
@click.option("--start-before", default=None)
@click.option("--output", "output_path", default=None, type=click.Path(path_type=Path))
@click.option("--model", default=None)
@click.pass_context
def generate(
    ctx: click.Context,
    location: str,
    calendar_length_days: int,
    max_cost: Decimal | None,
    event_types: tuple[str, ...],
    genres: tuple[str, ...],
    start_after: str | None,
    start_before: str | None,
    output_path: Path | None,
    model: str | None,
) -> None:
    if calendar_length_days <= 0:
        click.echo("Error: --calendar-length-days must be a positive integer.", err=True)
        ctx.exit(2)

    start_time_window = _parse_start_time_window(ctx, start_after, start_before)

    try:
        preferences = UserPreferenceSet(
            location=location,
            calendar_length_days=calendar_length_days,
            max_cost=max_cost,
            event_types=list(event_types),
            genres=list(genres),
            start_time_window=start_time_window,
        )
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        ctx.exit(2)

    config = load_config(model_override=model)

    try:
        provider = LLMProvider(config)
    except MissingConfigError as exc:
        click.echo(f"Error: {exc}", err=True)
        ctx.exit(3)
        return

    try:
        candidates = discover_events(preferences, config, provider)
    except DiscoveryUnavailableError as exc:
        click.echo(f"Error: {exc}", err=True)
        ctx.exit(3)
        return

    deduped = dedup.dedup_events(candidates)
    matched = filtering.filter_events(deduped, preferences)

    restrictive_note = None
    if not matched:
        restrictive_note = filtering.most_restrictive_filter(deduped, preferences)

    calendar = MarkdownCalendar(
        preferences=preferences,
        generated_at=datetime.now(),
        events=matched,
        most_restrictive_filter=restrictive_note,
    )

    resolved_output = output_path or _default_output_path(calendar.generated_at)
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    resolved_output.write_text(markdown.render_markdown(calendar), encoding="utf-8")

    click.echo(str(resolved_output))


def _default_output_path(generated_at: datetime) -> Path:
    return Path("calendars") / f"{generated_at.date().isoformat()}.md"


def _parse_start_time_window(
    ctx: click.Context, start_after: str | None, start_before: str | None
) -> tuple[time_cls, time_cls] | None:
    if start_after is None and start_before is None:
        return None
    if start_after is None or start_before is None:
        click.echo(
            "Error: --start-after and --start-before must both be set together.", err=True
        )
        ctx.exit(2)
    try:
        return (time_cls.fromisoformat(start_after), time_cls.fromisoformat(start_before))
    except ValueError:
        click.echo("Error: --start-after/--start-before must be HH:MM.", err=True)
        ctx.exit(2)
        return None
