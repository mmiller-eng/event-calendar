"""FastAPI app: exposes the event-calendar pipeline as a local HTTP API.

Wraps the same generation/sources pipeline used by `src/cli/` and
`src/mcp_server/` directly (no subprocess, no second implementation), so the
web frontend gets identical results and identical error categories.
"""

from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.services.discovery import DiscoveryUnavailableError

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


def main() -> None:
    uvicorn.run("src.web_api.app:app", host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
