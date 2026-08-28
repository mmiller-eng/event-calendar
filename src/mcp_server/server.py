"""MCP server: exposes the event-calendar pipeline as tools over stdio.

Wraps the same generation/sources pipeline used by `src/cli/generate.py` and
`src/cli/sources.py` directly (no subprocess), so MCP clients get structured
errors instead of parsed CLI output.
"""

from __future__ import annotations

from datetime import datetime
from datetime import time as time_cls
from decimal import Decimal, InvalidOperation
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field, ValidationError

from src.config import load_config
from src.llm.provider import LLMProvider, MissingConfigError
from src.models.calendar import MarkdownCalendar
from src.models.preferences import UserPreferenceSet
from src.services import dedup, filtering, markdown
from src.services.discovery import DiscoveryUnavailableError, discover_events, trusted_source_store

mcp = MCPServer("EventCalendar", log_level="ERROR")


class SourceResult(BaseModel):
    name: str
    url: str
    added_at: str


@mcp.tool(
    name="generate_calendar",
    description=(
        "Generate a Markdown calendar of cultural events for a location, applying the "
        "given preference filters, write it to disk, and return the Markdown content."
    ),
)
def generate_calendar(
    location: str = Field(description="Location to search for events, e.g. 'Seattle, WA'"),
    calendar_length_days: int = Field(
        description="Number of days ahead to include, must be a positive integer"
    ),
    max_cost: str | None = Field(
        default=None,
        description="Maximum ticket cost as a decimal string, e.g. '25.00'; omit for no cap",
    ),
    event_types: list[str] | None = Field(
        default=None,
        description="Event types to include, e.g. ['music', 'theater']; omit for all types",
    ),
    genres: list[str] | None = Field(
        default=None, description="Music genres to include, e.g. ['jazz']; omit for all genres"
    ),
    start_after: str | None = Field(
        default=None, description="Earliest start time as HH:MM; must be paired with start_before"
    ),
    start_before: str | None = Field(
        default=None, description="Latest start time as HH:MM; must be paired with start_after"
    ),
    output_path: str | None = Field(
        default=None,
        description="File path to write the calendar to; defaults to calendars/<date>.md",
    ),
    model: str | None = Field(
        default=None, description="LLM model override, e.g. 'anthropic/claude-sonnet-5'"
    ),
) -> str:
    if calendar_length_days <= 0:
        raise ToolError("calendar_length_days must be a positive integer.")

    start_time_window = _parse_start_time_window(start_after, start_before)

    try:
        parsed_max_cost = Decimal(max_cost) if max_cost is not None else None
    except InvalidOperation as exc:
        raise ToolError(f"max_cost must be a decimal number: {exc}") from exc

    preferences = UserPreferenceSet(
        location=location,
        calendar_length_days=calendar_length_days,
        max_cost=parsed_max_cost,
        event_types=list(event_types or []),
        genres=list(genres or []),
        start_time_window=start_time_window,
    )

    config = load_config(model_override=model)

    try:
        provider = LLMProvider(config)
    except MissingConfigError as exc:
        raise ToolError(str(exc)) from exc

    try:
        candidates = discover_events(preferences, config, provider)
    except DiscoveryUnavailableError as exc:
        raise ToolError(str(exc)) from exc

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

    rendered = markdown.render_markdown(calendar)

    resolved_output = (
        Path(output_path) if output_path else _default_output_path(calendar.generated_at)
    )
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    resolved_output.write_text(rendered, encoding="utf-8")

    return rendered


@mcp.tool(name="list_sources", description="List the configured trusted event sources.")
def list_sources() -> list[dict]:
    config = load_config()
    entries = trusted_source_store.load_sources(config.trusted_sources_path)
    return [{"name": e.name, "url": e.url, "added_at": e.added_at.isoformat()} for e in entries]


@mcp.tool(name="add_source", description="Add a trusted event source by name and URL.")
def add_source(
    name: str = Field(description="Human-readable name for the source"),
    url: str = Field(description="URL of the trusted source"),
) -> SourceResult:
    config = load_config()
    try:
        source, _ = trusted_source_store.add_source(
            config.trusted_sources_path, name=name, url=url
        )
    except ValidationError as exc:
        raise ToolError(f"Invalid url: {exc}") from exc
    return SourceResult(
        name=source.name, url=str(source.url), added_at=source.added_at.isoformat()
    )


@mcp.tool(name="remove_source", description="Remove a trusted event source by URL.")
def remove_source(
    url: str = Field(description="URL of the trusted source to remove"),
) -> SourceResult:
    config = load_config()
    entries = trusted_source_store.load_sources(config.trusted_sources_path)
    match = next((entry for entry in entries if str(entry.url) == url), None)
    if match is None:
        raise ToolError(f"No trusted source found for url: {url}")
    trusted_source_store.remove_source(config.trusted_sources_path, url=url)
    return SourceResult(name=match.name, url=str(match.url), added_at=match.added_at.isoformat())


def _default_output_path(generated_at: datetime) -> Path:
    return Path("calendars") / f"{generated_at.date().isoformat()}.md"


def _parse_start_time_window(
    start_after: str | None, start_before: str | None
) -> tuple[time_cls, time_cls] | None:
    if start_after is None and start_before is None:
        return None
    if start_after is None or start_before is None:
        raise ToolError("start_after and start_before must both be set together.")
    try:
        return (time_cls.fromisoformat(start_after), time_cls.fromisoformat(start_before))
    except ValueError as exc:
        raise ToolError("start_after/start_before must be HH:MM.") from exc


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
