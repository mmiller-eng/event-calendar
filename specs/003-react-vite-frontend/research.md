# Phase 0 Research: Web Frontend (React + Vite)

Unlike 001 and 002, this feature does not yet exist in the codebase — the
decisions below are proposed, not verified against shipped code. Each entry
still follows Decision/Rationale/Alternatives to resolve every open question
in the plan's Technical Context before Phase 1 design.

## 1. Backend framework: FastAPI + Uvicorn, not Flask or a raw ASGI app

**Decision**: Build `src/web_api/app.py` as a small FastAPI application, run
via `uvicorn`, bound to `localhost` only by default.

**Rationale**: The project already depends on `pydantic` (used throughout
`src/models/` and by the MCP server's tool schemas); FastAPI builds directly
on `pydantic` models for request/response validation, so `src/web_api/schemas.py`
can mirror `src/mcp_server/server.py`'s existing `SourceResult`-style pattern
almost exactly, keeping the two interfaces' code shape consistent. FastAPI
also generates an OpenAPI schema for free, which is useful as a live reference
for `contracts/web-contract.md` without hand-maintaining a second schema
format.

**Alternatives considered**: Flask (rejected — no built-in async support or
pydantic-based validation; would require a separate schema/validation layer
that FastAPI provides natively). A raw ASGI app with no framework (rejected —
reimplements routing/validation FastAPI already provides correctly, for no
benefit at this project's scale). Django (rejected outright — brings an ORM,
admin site, and multi-app/multi-tenant conventions that actively fight
Principle III's plain-files, single-user simplicity).

## 2. Repository layout: backend inside `src/`, frontend as a new top-level directory

**Decision**: `src/web_api/` lives inside the existing Python `src/` tree, as
a sibling to `src/cli/` and `src/mcp_server/`. The React app gets its own new
top-level `frontend/` directory, not nested under `src/`.

**Rationale**: The backend is pure Python and needs direct, in-process access
to `src/services`, `src/llm`, `src/config`, and `src/models` — putting it
inside `src/` keeps that access as ordinary same-package imports, exactly
like `mcp_server/server.py` already does, and avoids a second copy of the
domain models under a separate `backend/` root (which the plan template's
"Option 2: Web application" structure would otherwise suggest). The frontend
is a genuinely different ecosystem — its own `package.json`, `node_modules`,
and TypeScript build — so it cannot usefully live inside `src/`; a top-level
`frontend/` directory is the natural boundary.

**Alternatives considered**: Full "Option 2" split (separate `backend/` and
`frontend/` top-level directories, with `backend/` re-exporting or duplicating
`src/models`/`src/services`) — rejected, since this project already has a
single `src/` package that both the CLI and MCP server import from directly;
introducing a second Python package boundary just for the web backend would
either duplicate code or require an awkward cross-package import, solving a
problem this project doesn't have.

## 3. Frontend-backend communication: JSON over HTTP, no auth, CORS locked to the dev/prod origin

**Decision**: The frontend calls `src/web_api/` over plain JSON HTTP requests
(`fetch`, wrapped in `frontend/src/api/client.ts`). No authentication token or
session cookie is used (matches FR-011 and Principle III). FastAPI's CORS
middleware is configured to allow only the specific origin the frontend is
served from (the Vite dev server's origin in development; the backend's own
origin in production, once it serves the built static assets — see #6 below),
not a wildcard.

**Rationale**: A single local user on a single machine doesn't need session
management; adding auth would violate Principle III's explicit no-auth stance
without a corresponding requirement in spec.md. Restricting CORS to a known
origin (rather than `*`) costs nothing here and avoids leaving an open
`Access-Control-Allow-Origin: *` on a service that also accepts state-changing
requests (`POST`/`DELETE` on sources), even though it's local-only.

**Alternatives considered**: A wildcard CORS origin (rejected — no reason to
be looser than necessary, even for a local tool). Cookie/session-based auth
"for future-proofing" (rejected — Principle III explicitly disclaims
multi-tenancy/auth "unless a future amendment changes this principle"; adding
it speculatively is exactly the kind of complexity the principle warns
against).

## 4. Frontend language: TypeScript, not plain JavaScript

**Decision**: The React app is written in TypeScript, with types for API
requests/responses generated or hand-mirrored from `src/web_api/schemas.py`.

**Rationale**: The user's request named React, React Router, and Vite but not
a language; TypeScript is the de facto default for a new Vite+React project
today and gives the frontend the same kind of contract enforcement the Python
side already gets from `pydantic` — a mismatch between what the backend
returns and what the frontend expects becomes a compile-time type error
instead of a runtime bug, which matters for FR-008's "results are consistent"
guarantee reaching all the way to the browser.

**Alternatives considered**: Plain JavaScript (rejected — no reasonable
default requirement pushes toward it over TypeScript, and it gives up
compile-time contract checking for no benefit).

## 5. Frontend testing: Vitest + React Testing Library

**Decision**: Frontend tests use Vitest (Vite's native test runner) and React
Testing Library, colocated under `frontend/tests/` or alongside components.

**Rationale**: Vitest shares Vite's config and transform pipeline, so it
needs no separate build setup; React Testing Library is the standard choice
for testing what a user sees/does rather than component internals, matching
this project's existing preference (per Principle V) for behavior-level tests
over implementation-detail tests.

**Alternatives considered**: Jest (rejected — works, but requires a separate
transform/config pipeline from Vite's, adding maintenance surface with no
benefit over Vitest for a Vite project). No frontend tests at all (rejected —
Principle V's spirit, "every user-facing filter/behavior MUST have at least
one automated test," reasonably extends to this feature's own two views, even
though Principle V's literal text is scoped to filtering logic).

## 6. Production serving: backend serves the built static frontend

**Decision**: `npm run build` produces static assets in `frontend/dist/`;
`src/web_api/app.py` serves them as static files for any non-API route, so a
user can run one process (`uvicorn src.web_api.app:app`) and get both the API
and the UI, matching the CLI/MCP server's "one process, one command" shape
(`calendar`, `calendar-mcp`, and now e.g. `calendar-web`).

**Rationale**: Running a separate static file host (e.g. `nginx`) for a
single-user local tool would introduce operational complexity Principle III
explicitly warns against ("single-user simplicity"). Development still uses
Vite's dev server (with its fast HMR) proxying API calls to the backend
(research.md #3's CORS origin is exactly this dev-server origin); only the
production path is collapsed into one process.

**Alternatives considered**: A permanently separate frontend dev/prod server
process (rejected — two long-running processes to start/manage for a
single-user tool, when one is sufficient). A static-export-only frontend with
no backend serving it (rejected — still needs _some_ process to serve static
files in production; reusing the backend process is strictly simpler than
introducing a second one).
