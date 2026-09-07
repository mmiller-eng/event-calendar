# Quickstart: Web Frontend (React + Vite)

Validation guide for this feature once implemented. Full endpoint/route
detail lives in [contracts/web-contract.md](./contracts/web-contract.md);
request/response shapes live in [data-model.md](./data-model.md) — neither is
duplicated here.

## Prerequisites

- Same environment as the CLI/MCP server: `EVENT_CALENDAR_MODEL`, a provider
  API key, and (optionally) `TAVILY_API_KEY` set per
  `specs/001-cultural-event-calendar/contracts/cli-contract.md`'s Config
  section.
- Python deps installed (`uv sync` or equivalent) including the new
  `fastapi`/`uvicorn`.
- Node.js 20+ and frontend deps installed (`cd frontend && npm install`).

## Run it

1. **Backend**: `uvicorn src.web_api.app:app --reload` — serves the API on
   `localhost` (default port per FastAPI/uvicorn convention, e.g. `:8000`).
2. **Frontend (development)**: `cd frontend && npm run dev` — starts the Vite
   dev server, proxying `/api/*` requests to the backend (research.md #3, #6).
3. Open the printed Vite dev server URL in a browser.

**Production**: `cd frontend && npm run build`, then run only the backend
(`uvicorn src.web_api.app:app`) — it serves the built static assets for any
non-`/api` route (research.md #6). One process, one command, matching
`calendar`/`calendar-mcp`'s shape.

## Validate User Story 1 — generate and view a calendar (P1)

1. With at least one trusted source configured (or `TAVILY_API_KEY` set),
   open the app's default `/` route.
2. Submit a location and calendar length.
3. **Expect**: an in-progress indicator appears, then the generated calendar
   renders in the browser — each event's date, time, venue, and cost visible
   without leaving the page (SC-001).
4. Submit preferences unlikely to match anything (e.g. an implausible max
   cost).
   **Expect**: an explicit "no events matched" result, not a blank or broken
   view (spec.md Acceptance Scenario 3).

## Validate User Story 2 — manage trusted sources (P2)

1. Navigate to `/sources`.
2. Add a source with a valid name and URL.
   **Expect**: it appears in the displayed list.
3. Re-submit the same URL.
   **Expect**: no duplicate is created; the existing entry is shown (FR-005).
4. Submit a malformed URL.
   **Expect**: an inline validation message; nothing is added (FR-004).
5. Remove the source added in step 2.
   **Expect**: it disappears from the list.
6. Attempt to remove a URL not on the list (e.g. by retrying step 5).
   **Expect**: a clear "not found" message (FR-006).

## Validate User Story 3 — navigation without losing context (P3)

1. Generate a calendar (as in US1).
2. Navigate to `/sources`, then back to `/`.
   **Expect**: no full-page reload occurs (network tab shows only the API
   calls, no HTML document re-fetch), and the previously generated calendar
   is still displayed (SC-002, spec.md Acceptance Scenario 2).

## Validate edge cases

- Trigger generation with no trusted sources and `TAVILY_API_KEY` unset.
  **Expect**: HTTP 503 from `POST /api/calendar`, surfaced in the browser as
  the same plain-language "no sources available" message the CLI and MCP
  server already produce.
- Navigate directly to an unknown path (e.g. `/nonexistent`).
  **Expect**: a "not found" view, not a blank page.
- Submit a second generation request while one is already in progress (e.g.
  by clicking submit twice quickly).
  **Expect**: the second request is prevented client-side, or rejected with
  409 if it reaches the backend — never two concurrent generations from one
  session.

## Automated equivalent

Once implemented, `tests/contract/web_api_contract_test.py` and the frontend
Vitest suite (`frontend/tests/`) are the automated version of the scenarios
above and should be run instead of manual validation for routine checks:

```bash
.venv/bin/pytest tests/contract/web_api_contract_test.py -v
cd frontend && npm test
```
