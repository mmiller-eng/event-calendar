"""FastAPI app: exposes the event-calendar pipeline as a local HTTP API.

Wraps the same generation/sources pipeline used by `src/cli/` and
`src/mcp_server/` directly (no subprocess, no second implementation), so the
web frontend gets identical results and identical error categories.
"""

from __future__ import annotations

import os
import threading
from datetime import datetime
from datetime import time as time_cls
from decimal import Decimal

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.config import Config, load_config
from src.llm.provider import LLMProvider, MissingConfigError
from src.models.calendar import MarkdownCalendar
from src.models.preferences import UserPreferenceSet
from src.services import dedup, filtering
from src.services.discovery import DiscoveryUnavailableError, discover_events
from src.services.markdown import _render_cost, render_markdown
from src.utils import default_output_path
from src.web_api.schemas import CalendarResponse, EventSummary, GenerateRequest

# The Vite dev server's default origin; overridable for a non-default port.
# Production requests are same-origin (this app serves the built frontend
# itself — research.md #6) and never need this allowance.
_DEV_ORIGIN = os.environ.get("EVENT_CALENDAR_WEB_ORIGIN", "http://localhost:5173")

app = FastAPI(title="Event Calendar Web API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[_DEV_ORIGIN],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


class SourceNotFoundError(Exception):
    """Raised by a route handler when a remove-target URL isn't on the trusted-source list."""


# Single-user, single-session tool (Principle III, plan.md Scale/Scope) — a plain
# lock is enough to reject a second concurrent generation request (spec.md edge
# case). Sync route handlers run in FastAPI's threadpool, so this must be a real
# lock, not a bare boolean flag (check-then-set would race between threads).
_generation_lock = threading.Lock()


@app.exception_handler(DiscoveryUnavailableError)
async def _discovery_unavailable_handler(
    request: Request, exc: DiscoveryUnavailableError
) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(ValidationError)
async def _validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    message = "; ".join(err["msg"] for err in exc.errors())
    return JSONResponse(status_code=422, content={"detail": message})


@app.exception_handler(SourceNotFoundError)
async def _source_not_found_handler(request: Request, exc: SourceNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


def _parse_start_time_window(
    start_after: str | None, start_before: str | None
) -> tuple[time_cls, time_cls] | None:
    # GenerateRequest already guarantees both-or-neither are set.
    if start_after is None or start_before is None:
        return None
    try:
        return (time_cls.fromisoformat(start_after), time_cls.fromisoformat(start_before))
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail="start_after/start_before must be HH:MM."
        ) from exc


@app.post("/api/calendar")
def generate_calendar(req: GenerateRequest) -> CalendarResponse:
    if not _generation_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409, detail="A generation request is already in progress."
        )
    try:
        preferences = UserPreferenceSet(
            location=req.location,
            calendar_length_days=req.calendar_length_days,
            max_cost=Decimal(str(req.max_cost)) if req.max_cost is not None else None,
            event_types=req.event_types,
            genres=req.genres,
            start_time_window=_parse_start_time_window(req.start_after, req.start_before),
        )

        config: Config = load_config(model_override=req.model)

        try:
            provider = LLMProvider(config)
        except MissingConfigError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        candidates = discover_events(preferences, config, provider)

        deduped = dedup.dedup_events(candidates)
        matched = filtering.filter_events(deduped, preferences)

        calendar = MarkdownCalendar(
            preferences=preferences,
            generated_at=datetime.now(),
            events=matched,
        )

        output_path = default_output_path(config, calendar.generated_at)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(render_markdown(calendar), encoding="utf-8")

        events = [
            EventSummary(
                name=event.name,
                date=event.date.isoformat(),
                start_time=(
                    "unknown"
                    if event.start_time == "unknown"
                    else event.start_time.strftime("%H:%M")
                ),
                venue=event.venue,
                cost=_render_cost(event.cost),
                event_type=event.event_type,
                genre=None if event.genre in (None, "unknown") else event.genre,
                source_url=event.source_ref.identifier,
            )
            for event in matched
        ]

        return CalendarResponse(
            output_path=str(output_path),
            generated_at=calendar.generated_at.isoformat(),
            events=events,
            event_count=len(events),
        )
    finally:
        _generation_lock.release()


def main() -> None:
    uvicorn.run("src.web_api.app:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
