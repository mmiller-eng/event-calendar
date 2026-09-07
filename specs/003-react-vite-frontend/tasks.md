---
description: "Task list template for feature implementation"
---

# Tasks: Web Frontend (React + Vite)

**Input**: Design documents from `/specs/003-react-vite-frontend/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/web-contract.md, quickstart.md (all present)

**Tests**: Included — plan.md's Constitution Check commits this feature's own routes/views to Principle V test coverage, and quickstart.md's "Automated equivalent" section names `tests/contract/web_api_contract_test.py` and the frontend Vitest suite explicitly. Phase 6 adds Playwright (T036) as a true full-stack end-to-end layer on top of those mocked-backend suites.

**Organization**: Tasks are grouped by user story (spec.md: US1 generate & view, P1; US2 manage sources, P2; US3 navigate without losing context, P3) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are included in every description

## Path Conventions

Per plan.md's Structure Decision: backend lives inside the existing `src/` tree (`src/web_api/`), frontend gets a new top-level `frontend/` directory, tests split across `tests/contract/`, `tests/integration/` (backend, existing convention) and `frontend/tests/` (frontend, new).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization for both the new backend package and the new frontend project

- [x] T001 Create `src/web_api/__init__.py` and empty `src/web_api/app.py`, `src/web_api/schemas.py`
- [x] T002 Add `fastapi>=0.115` and `uvicorn>=0.30` to `pyproject.toml` `[project.dependencies]`, and add a `calendar-web = "src.web_api.app:main"` entry under `[project.scripts]` (research.md #1, #6)
- [x] T003 [P] Scaffold a Vite + React + TypeScript app in `frontend/` (`package.json`, `vite.config.ts`, `tsconfig.json`, `index.html`) with `react`, `react-dom`, `react-router-dom` as dependencies (research.md #2, #4)
- [ ] T004 [P] Configure Vitest + React Testing Library in `frontend/` (`vitest.config.ts` or a `test` block in `vite.config.ts`, plus `frontend/tests/setup.ts`) (research.md #5)
- [ ] T005 [P] Add an ESLint + Prettier config for `frontend/` and confirm the existing root `[tool.ruff]` config in `pyproject.toml` already covers `src/web_api/` (it should, via the existing `src*` package include)

**Checkpoint**: Both `src/web_api/` and `frontend/` exist as buildable, lintable, empty projects

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared backend schemas/app wiring and shared frontend routing/API-client scaffolding that every user story depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Implement `GenerateRequest`, `EventSummary`, `CalendarResponse`, and `SourceResponse` pydantic models in `src/web_api/schemas.py` (data-model.md)
- [ ] T007 Create the FastAPI app instance in `src/web_api/app.py`, with CORS middleware restricted to the frontend's own origin (dev-server origin in development; same-origin in production) — no wildcard (research.md #3)
- [ ] T008 Implement shared error handling in `src/web_api/app.py`: map `DiscoveryUnavailableError` → 503, invalid-URL/validation failures → 422, remove-not-found → 404, each with the plain-language message body defined in `contracts/web-contract.md` (depends on T006, T007)
- [ ] T009 [P] Create `frontend/src/api/client.ts`: a typed fetch wrapper exposing `generateCalendar(req: GenerateRequest)`, `listSources()`, `addSource(...)`, `removeSource(url)`, with TypeScript types mirroring `src/web_api/schemas.py` (data-model.md)
- [ ] T010 [P] Create `frontend/src/App.tsx` with `react-router-dom` routes for `/` and `/sources` (empty placeholder pages for now) plus a catch-all not-found route (contracts/web-contract.md frontend route table)
- [ ] T011 Create `frontend/src/main.tsx` entrypoint wrapping `<App/>` in `<BrowserRouter>` and mounting it

**Checkpoint**: Foundation ready — backend has a running, error-handling-aware FastAPI app with schemas; frontend has routing and an API client. User story implementation can now begin.

---

## Phase 3: User Story 1 - Generate and view a calendar in the browser (Priority: P1) 🎯 MVP

**Goal**: A user can submit generation preferences from the browser and see the resulting calendar rendered on the page.

**Independent Test**: Open the app, submit valid preferences, confirm a rendered calendar (or an explicit "no events matched" result) appears without leaving the page.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T012 [P] [US1] Contract test for `POST /api/calendar` (200 success, `event_count: 0` case, 422 invalid body, 503 no-sources-reachable) in `tests/contract/web_api_contract_test.py`
- [ ] T013 [P] [US1] Integration test for the full generate flow, with mocked discovery/LLM inputs, in `tests/integration/web_api_test.py`
- [ ] T014 [P] [US1] Component test for `GenerateView`'s loading, result, and "no events matched" states in `frontend/tests/GenerateView.test.tsx`

### Implementation for User Story 1

- [ ] T015 [US1] Implement `POST /api/calendar` in `src/web_api/app.py`: validate `GenerateRequest`, call the existing `discover_events`/`filter_events`/`dedup_events`/render pipeline in-process, write the Markdown file, return `CalendarResponse` (depends on T006–T008)
- [ ] T016 [US1] Add a per-session in-progress guard to `POST /api/calendar` that returns 409 if a generation request is already running for the same session (spec.md edge case; contracts/web-contract.md)
- [ ] T017 [P] [US1] Create `frontend/src/pages/GenerateView.tsx`: a form for `location`, `calendar_length_days`, `max_cost`, `event_types`, `genres`, `start_after`/`start_before`, `model`
- [ ] T018 [US1] Wire `GenerateView`'s submit handler to `client.ts`'s `generateCalendar`; render an in-progress indicator while pending, the returned `events` list (date/time/venue/cost) on success, and the explicit "no events matched" state when `event_count` is 0 (depends on T017, T009)
- [ ] T019 [US1] Render 422/503 error responses from `POST /api/calendar` as plain-language inline messages in `GenerateView.tsx`, not raw errors (FR-009)

**Checkpoint**: User Story 1 is fully functional and independently testable — a user can generate and view a calendar entirely in the browser.

---

## Phase 4: User Story 2 - Manage trusted sources in the browser (Priority: P2)

**Goal**: A user can view, add, and remove trusted event sources through web forms.

**Independent Test**: Open the source-management view, add a source, confirm it appears, remove it, confirm it disappears — independent of calendar generation.

### Tests for User Story 2

- [ ] T020 [P] [US2] Contract tests for `GET/POST/DELETE /api/sources` (list, add, duplicate-no-op, malformed-URL 422, remove success, remove-not-found 404) in `tests/contract/web_api_contract_test.py`
- [ ] T021 [P] [US2] Integration test for the add → list → remove source-management flow in `tests/integration/web_api_test.py`
- [ ] T022 [P] [US2] Component test for `SourcesView`'s list, add, remove, and validation-error states in `frontend/tests/SourcesView.test.tsx`

### Implementation for User Story 2

- [ ] T023 [US2] Implement `GET /api/sources` in `src/web_api/app.py`, returning `list[SourceResponse]` (empty list, not an error, when none configured) (depends on T006–T008)
- [ ] T024 [US2] Implement `POST /api/sources` in `src/web_api/app.py`: add a source, return the existing `SourceResponse` unchanged on a duplicate URL (FR-005), 422 on a malformed URL (FR-004)
- [ ] T025 [US2] Implement `DELETE /api/sources` in `src/web_api/app.py`: remove by `url` query param, 404 with a plain-language "not found" message if absent (FR-006)
- [ ] T026 [P] [US2] Create `frontend/src/pages/SourcesView.tsx`: source list display, add-source form, remove action per row
- [ ] T027 [US2] Wire `SourcesView` to `client.ts`'s `listSources`/`addSource`/`removeSource`; render inline validation and "not found" messages (depends on T026, T009)

**Checkpoint**: User Stories 1 AND 2 both work independently.

---

## Phase 5: User Story 3 - Move between views without losing context (Priority: P3)

**Goal**: A user can navigate between the generate view and the manage-sources view without a full page reload, and without losing the most recently generated calendar.

**Independent Test**: Generate a calendar, navigate to `/sources`, navigate back to `/`, confirm the calendar is still displayed and no full-page reload occurred.

### Tests for User Story 3

- [ ] T028 [P] [US3] Test verifying navigation between `/` and `/sources` preserves the last-generated calendar and triggers no full-page reload, in `frontend/tests/navigation.test.tsx`

### Implementation for User Story 3

- [ ] T029 [US3] Lift "most recently generated calendar" state from `GenerateView` up to `App.tsx` (or a small context) so it survives unmounting `GenerateView` during navigation (depends on T010, T018)
- [ ] T030 [US3] Add `<Link>`-based navigation between `/` and `/sources` in `App.tsx`/`GenerateView.tsx`/`SourcesView.tsx` (no `<a href>` full-reload links) (FR-007, SC-002)
- [ ] T031 [US3] Create `frontend/src/pages/NotFoundView.tsx` and wire it into `App.tsx`'s catch-all route (spec.md edge case)

**Checkpoint**: All three user stories are independently functional; the app behaves as one coherent SPA.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Production readiness and validation across all stories

- [ ] T032 Serve `frontend/dist/` as static files for any non-`/api` route from `src/web_api/app.py`, so `uvicorn src.web_api.app:app` alone serves both API and UI in production (research.md #6)
- [ ] T033 [P] Add a `frontend/src/pages/GenerateView.tsx` empty/first-visit state that guides the user to submit their first request (spec.md edge case)
- [ ] T034 [P] Update `README.md` with a "Web Frontend" section documenting `uvicorn src.web_api.app:app --reload` + `npm run dev`/`npm run build`, mirroring the existing "MCP Server" section's structure
- [ ] T035 Run `specs/003-react-vite-frontend/quickstart.md`'s manual validation scenarios end-to-end against a real (non-mocked) backend
- [ ] T036 [P] Add Playwright end-to-end tests automating quickstart.md's US1–US3 scenarios (generate a calendar, add/remove a source, navigate between views without a full reload) against a real running backend + built frontend, in `frontend/e2e/` (`generate.spec.ts`, `sources.spec.ts`, `navigation.spec.ts`) — complements the mocked Vitest component tests and mocked-backend contract/integration tests with one true full-stack check (depends on T015–T031 being complete)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3–5)**: All depend on Foundational phase completion
  - US1 has no dependency on US2 or US3
  - US2 has no dependency on US1 or US3
  - US3 depends on US1's `GenerateView` existing (T018) to have state to lift (T029), and on Foundational's routing (T010) — it is the one story that is not fully independent of another, by definition (it's about navigating _between_ views US1 and US2 create)
- **Polish (Phase 6)**: Depends on all three user stories being complete; T036 (Playwright) additionally needs a real backend + built frontend running together, so it should run after T032 (production static serving) as well

### Within Each User Story

- Tests written and failing before implementation
- Backend routes (T015, T023–T025) before the frontend views that call them (T018, T027) — though the frontend page structure itself (T017, T026) can be built in parallel with backend route work, since it depends only on `client.ts` (T009) and the schemas' shape (T006), not the routes' running implementation

### Parallel Opportunities

- T003, T004, T005 (Setup) can run in parallel — independent files
- T009, T010 (Foundational) can run in parallel — independent files, both only depend on T006
- T012, T013, T014 (US1 tests) can run in parallel
- T017 (US1 frontend page) can run in parallel with T015–T016 (US1 backend), since both only depend on Phase 2 completion
- T020, T021, T022 (US2 tests) can run in parallel
- T026 (US2 frontend page) can run in parallel with T023–T025 (US2 backend)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Contract test for POST /api/calendar in tests/contract/web_api_contract_test.py"
Task: "Integration test for generate flow in tests/integration/web_api_test.py"
Task: "Component test for GenerateView in frontend/tests/GenerateView.test.tsx"

# Backend and frontend page work can proceed in parallel once Phase 2 is done:
Task: "Implement POST /api/calendar in src/web_api/app.py"
Task: "Create frontend/src/pages/GenerateView.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run quickstart.md's US1 scenarios against the real app
5. Demo: a working generate-and-view flow, even without source management or SPA navigation polish

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. Add User Story 1 → validate independently → demo (MVP!)
3. Add User Story 2 → validate independently → demo
4. Add User Story 3 → validate independently → demo (full SPA feel)
5. Phase 6 polish → production-ready

---

## Notes

- [P] tasks touch different files with no unfinished dependency between them
- [Story] labels map every implementation task back to spec.md's user stories for traceability
- US3 is intentionally the one story with a soft dependency on US1 (per spec.md's own framing — navigation is a refinement on top of stories that already work as separate pages)
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently before continuing
