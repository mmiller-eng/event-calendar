# Implementation Plan: Web Frontend (React + Vite)

**Branch**: `003-react-vite-frontend` | **Date**: 2026-09-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-react-vite-frontend/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow. Unlike 001 and 002, this feature is **not yet built** — this plan proposes the design, it does not document shipped code.

## Summary

Add a browser-based third interface to the project: a React + Vite + React Router single-page app (`frontend/`) that lets a user generate a calendar and manage trusted sources without a terminal, backed by a new small local HTTP API (`src/web_api/`) that calls the existing `src/services`/`src/llm`/`src/config` pipeline in-process — the same code the CLI and MCP server already call. No business logic is duplicated: the backend is a thin HTTP-shaped sibling to `src/cli/` and `src/mcp_server/`, translating HTTP requests into the same calls the other two interfaces already make, and translating pipeline errors into the plain-language messages FR-009 requires.

## Technical Context

**Language/Version**: Python 3.11+ (backend, same runtime as the rest of the project) and TypeScript with Node.js 20+ (frontend — reasonable default for a new React/Vite app; see research.md #4).

**Primary Dependencies**: Backend — `fastapi` + `uvicorn` (new; async HTTP framework and ASGI server, chosen in research.md #1), reusing the existing `litellm`/`httpx`/`pydantic`/`pyyaml` pipeline unchanged. Frontend — `react`, `react-dom`, `react-router-dom`, `vite`, `typescript` (all new — this feature introduces the frontend ecosystem to the project for the first time).

**Storage**: Unchanged from 001/002 — `trusted_sources.yaml` and generated Markdown calendar files on disk. No database, no browser-side persistent storage of domain data.

**Testing**: Backend — `pytest` + `pytest-asyncio` (already configured in `pyproject.toml`), with FastAPI's `TestClient`/`httpx.ASGITransport` for contract tests, following the same `tests/contract/` and `tests/integration/` split already used by 001/002. Frontend — Vitest + React Testing Library (Vite-native default; research.md #5), covering component rendering and the API-client layer with a mocked backend.

**Target Platform**: Same local, single-user machine as the CLI and MCP server. The backend binds to `localhost` only (no external network exposure — matches Principle III); the frontend is served either by Vite's dev server (development) or as a static build the backend serves (production), so no separate hosting infrastructure is introduced.

**Project Type**: Web application (frontend + backend) grafted onto the existing single-project layout — the backend lives inside the existing `src/` tree as a sibling interface to `cli/` and `mcp_server/`, and only the frontend gets a new top-level directory, since it is a genuinely separate language/tooling ecosystem (research.md #2).

**Performance Goals**: Not performance-critical for the backend (same LLM/network-latency-bound expectation as 001's SC-001 and 002's Performance Goals). Frontend view transitions must complete in under 1 second per SC-002 (client-side routing, no full page reload).

**Constraints**: Must reuse 001/002's pipeline logic unchanged (Principle I, II, IV amendment) — the backend MUST NOT reimplement filtering, discovery, or dedup, and MUST NOT introduce a second LLM-access path. No authentication or multi-user support (Principle III, FR-011). `localhost`-only binding by default — no remote/network exposure. Single browser session at a time; no concurrency requirements beyond preventing a second concurrent generation request from the same session (edge case in spec.md).

**Scale/Scope**: Single user, single browser tab/session; same trusted-source-list scale as 001/002 (tens of entries).

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

Evaluated against Constitution v1.2.0 (amended 2026-09-07 specifically to admit this feature — see `.specify/memory/constitution.md` Sync Impact Report).

| Principle                                       | Status | Basis                                                                                                                                                                                                                                                                                                                               |
| ----------------------------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| I. No Fabrication                               | PASS   | The `src/web_api/` backend calls the unmodified `discover_events`/`filter_events`/`dedup_events` pipeline from 001 in-process; no new event-data path is introduced, so the `"unknown"`-sentinel and merge-not-duplicate rules still apply unchanged.                                                                               |
| II. Provider-Agnostic Model Access              | PASS   | No new LLM call path; `src/llm/provider.py`'s `LLMProvider`/`litellm` abstraction (and its `LLMRequestError` handling from 002) is reused as-is by the backend.                                                                                                                                                                     |
| III. Plain-Files, Single-User Simplicity        | PASS   | No database introduced; the backend reads/writes the same `trusted_sources.yaml` and Markdown files. No authentication, accounts, or multi-tenancy (FR-011); backend binds to `localhost` only.                                                                                                                                     |
| IV. Stable Interface Contracts (CLI, MCP & Web) | PASS   | This principle was amended specifically to recognize the web frontend as the third stable interface. `contracts/web-contract.md` (Phase 1 output) documents its routes, request/response shapes, and error behavior, the web-side equivalent of `contracts/cli-contract.md` and the (still-pending) `contracts/mcp-contract.md`.    |
| V. Test-Verified Filtering                      | PASS   | No new filter logic — the backend reuses 001's already-tested filtering/dedup/rendering code paths verbatim. This feature's own test-verification target (its HTTP routes + their error paths, and the frontend's rendering of them) is covered by new `tests/contract/web_api_contract_test.py` and frontend component/unit tests. |

**Post-Phase-1 re-check**: `contracts/web-contract.md`, `data-model.md`, and `quickstart.md` (generated below) were reviewed against the same table — no drift found; still PASS.

## Project Structure

### Documentation (this feature)

```text
specs/003-react-vite-frontend/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── web-contract.md
└── checklists/
    └── requirements.md  # /speckit-specify output
```

### Source Code (repository root)

```text
src/
├── web_api/
│   ├── __init__.py
│   ├── app.py            # FastAPI app instance + route handlers (calls services/llm/config directly)
│   └── schemas.py         # pydantic request/response models (GenerateRequest, SourceResponse, etc.)
├── llm/
│   └── provider.py        # unchanged — reused as-is (LLMRequestError from 002 already handles provider failures)
├── services/
│   └── discovery/
│       └── __init__.py    # unchanged — reused as-is
├── models/                 # unchanged — TrustedSource, CulturalEvent, MarkdownCalendar, UserPreferenceSet reused as-is
├── cli/                    # unchanged — this feature adds a third interface, does not modify the CLI
├── mcp_server/              # unchanged — this feature adds a third interface, does not modify the MCP server
└── config.py                # unchanged — same config surface used by all three interfaces

frontend/
├── package.json
├── vite.config.ts
├── index.html
├── src/
│   ├── main.tsx            # entrypoint, mounts <App/>
│   ├── App.tsx              # React Router route definitions (/ generate view, /sources manage view)
│   ├── pages/
│   │   ├── GenerateView.tsx
│   │   └── SourcesView.tsx
│   ├── api/
│   │   └── client.ts         # typed fetch wrapper for src/web_api endpoints (mirrors contracts/web-contract.md)
│   └── components/
└── tests/                     # Vitest + React Testing Library

tests/
├── contract/
│   └── web_api_contract_test.py   # asserts on routes, status codes, response shape — analogous to cli-contract tests
└── integration/
    └── web_api_test.py            # end-to-end backend test: real FastAPI app + mocked discovery/LLM inputs
```

**Structure Decision**: The backend stays inside the existing single-project `src/` tree as `web_api/`, a sibling to `cli/` and `mcp_server/` — all three are thin interfaces over the same `services`/`llm`/`config` core (Principle IV), and keeping the backend there avoids a second, duplicated copy of `models`/`services` under a separate `backend/` root. The frontend gets its own top-level `frontend/` directory because it is a genuinely separate language/tooling ecosystem (Node/TypeScript, its own `package.json` and dependency tree) that cannot live inside the Python `src/` tree — this is the one deliberate deviation from pure "Option 1: single project," scoped to exactly the frontend's own files.

## Complexity Tracking

_No Constitution Check violations — table not applicable._
