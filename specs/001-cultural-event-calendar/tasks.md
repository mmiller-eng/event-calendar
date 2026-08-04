---

description: "Task list for feature implementation"
---

# Tasks: Cultural Event Calendar Agent

**Input**: Design documents from `/specs/001-cultural-event-calendar/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli-contract.md, quickstart.md

**Tests**: Included. `plan.md`/`research.md` already commit to a `tests/contract|integration|unit` layout and a mocked-HTTP/mocked-LLM testing approach, so test tasks are generated alongside implementation.

**Organization**: Tasks are grouped by user story (from spec.md: US1 = P1, US2 = P2, US3 = P3) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)

## Path Conventions

Single project (per plan.md Structure Decision): `src/`, `tests/` at repository root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project structure per plan.md: `src/models/`, `src/services/discovery/`, `src/llm/`, `src/cli/`, `tests/contract/`, `tests/integration/`, `tests/unit/`
- [X] T002 Initialize Python project (`pyproject.toml`) with dependencies from research.md: `litellm`, `httpx`, `beautifulsoup4`, `pydantic`, `click`, `pyyaml`, `tavily-python`, and dev dependencies `pytest`, `respx`
- [X] T003 [P] Configure linting/formatting (ruff) in `pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models, config, LLM access, and trusted-source storage that every user story's discovery/filtering/rendering pipeline depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 [P] Create `UserPreferenceSet` model (per data-model.md) in `src/models/preferences.py`
- [X] T005 [P] Create `CulturalEvent` and `SourceRef` models (per data-model.md, incl. `"unknown"` sentinel fields) in `src/models/event.py`
- [X] T006 [P] Create `TrustedSource` model in `src/models/trusted_source.py`
- [X] T007 [P] Create `MarkdownCalendar` model in `src/models/calendar.py`
- [X] T008 Implement config loading (`EVENT_CALENDAR_MODEL`, provider API key, `TAVILY_API_KEY`, trusted-source file path, output dir) in `src/config.py`
- [X] T009 Implement provider-agnostic LLM client wrapper (litellm, model selected via config) in `src/llm/provider.py` (depends on T008)
- [X] T010 Implement trusted-source list storage — load/save `trusted_sources.yaml` (depends on T006) in `src/services/discovery/trusted_source_store.py`
- [X] T011 Implement CLI entry point and `calendar` command group (click) in `src/cli/__init__.py`
- [X] T012 Implement `calendar sources list|add|remove` commands per contracts/cli-contract.md (exit codes 0/2/4) in `src/cli/sources.py` (depends on T006, T010, T011)

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - Generate a personalized event calendar (Priority: P1) 🎯 MVP

**Goal**: From a location and calendar length (with all other preferences optional), discover events via trusted sources then web-search fallback, and produce a single chronologically-ordered Markdown calendar — including an explicit message when zero events match.

**Independent Test**: Supply a location and a calendar length, run `calendar generate`, confirm a Markdown file is produced listing dated cultural events for that area within that span (or an explicit no-matches message).

### Tests for User Story 1

- [X] T013 [P] [US1] Contract test for `calendar generate` required/invalid args (exit codes 0/2) in `tests/contract/test_generate_contract.py`
- [X] T014 [P] [US1] Integration test: location + calendar-length only → Markdown grouped by date in `tests/integration/test_generate_basic.py`
- [X] T015 [P] [US1] Integration test: no optional preferences set → all event types/genres included in `tests/integration/test_generate_no_optional_prefs.py`
- [X] T016 [P] [US1] Integration test: zero matching events → explicit no-matches statement, valid non-empty file in `tests/integration/test_generate_zero_results.py`

### Implementation for User Story 1

- [X] T017 [P] [US1] Implement trusted-source page fetch (httpx) + text extraction (BeautifulSoup) + LLM-based event extraction in `src/services/discovery/trusted_source_client.py` (depends on T009, T010)
- [X] T018 [P] [US1] Implement live web-search fallback client (Tavily) + LLM-based event extraction in `src/services/discovery/web_search_client.py` (depends on T009)
- [X] T019 [US1] Implement discovery orchestrator: trusted sources first, web search fallback second, per FR-002 in `src/services/discovery/__init__.py` (depends on T017, T018)
- [X] T020 [P] [US1] Implement date-range filtering and "no restriction when unset" semantics for type/genre in `src/services/filtering.py` (depends on T004, T005)
- [X] T021 [P] [US1] Implement duplicate-event merge (dedup key + trusted-source-wins tie-break, per data-model.md) in `src/services/dedup.py` (depends on T005)
- [X] T022 [P] [US1] Implement Markdown rendering, incl. explicit zero-results statement (FR-009) in `src/services/markdown.py` (depends on T007)
- [X] T023 [US1] Implement `calendar generate` command: wire discovery → filter → dedup → render → write file, print resolved path (per contracts/cli-contract.md) in `src/cli/generate.py` (depends on T019, T020, T021, T022, T008, T011)
- [X] T024 [US1] Add "most restrictive filter" best-effort note for the zero-results case to `src/services/filtering.py` (depends on T020)

**Checkpoint**: User Story 1 fully functional and independently testable (`calendar generate --location ... --calendar-length-days ...`)

---

## Phase 4: User Story 2 - Filter events by cost (Priority: P2)

**Goal**: Let the user cap price (including free-only) so the calendar excludes events above that cap, while flagging unknown-priced events instead of silently dropping or including them.

**Independent Test**: Set a maximum price (or free-only) and confirm every event in the resulting calendar is at or below that price, with unknown-priced events clearly flagged.

### Tests for User Story 2

- [X] T025 [P] [US2] Contract test for `--max-cost` flag parsing/validation in `tests/contract/test_generate_cost_contract.py`
- [X] T026 [P] [US2] Integration test: `--max-cost 0` → only free events in `tests/integration/test_cost_free_only.py`
- [X] T027 [P] [US2] Integration test: `--max-cost 30` → no event exceeds $30, unknown-cost events present and flagged in `tests/integration/test_cost_ceiling.py`

### Implementation for User Story 2

- [X] T028 [P] [US2] Add cost filtering rule to `src/services/filtering.py` — enforce ceiling, always include `"unknown"` cost (depends on T020)
- [X] T029 [P] [US2] Add `--max-cost` CLI flag (parse, validate `>= 0`) to `src/cli/generate.py` (depends on T023)
- [X] T030 [P] [US2] Render cost field distinctly as amount / `free` / `unknown` in `src/services/markdown.py` (depends on T022)

**Checkpoint**: User Stories 1 AND 2 both work independently

---

## Phase 5: User Story 3 - Filter by event type and music genre (Priority: P3)

**Goal**: Narrow results to selected event type(s) and, for music, genre(s), without affecting non-music events.

**Independent Test**: Request a single event type and genre and confirm every listed event matches both; request multiple types with no genre restriction and confirm genre filtering only applies to music events.

### Tests for User Story 3

- [X] T031 [P] [US3] Contract test for `--event-type`/`--genre` (repeatable) flags in `tests/contract/test_generate_type_genre_contract.py`
- [X] T032 [P] [US3] Integration test: `--event-type music --genre jazz` → only jazz music events in `tests/integration/test_type_genre_filter.py`
- [X] T033 [P] [US3] Integration test: `--event-type music --event-type theater` (no genre) → both types included, genre filter not applied to theater in `tests/integration/test_multi_type_no_genre.py`

### Implementation for User Story 3

- [X] T034 [US3] Add multi-value event-type filtering to `src/services/filtering.py` (depends on T020)
- [X] T035 [US3] Add genre filtering scoped to `event_type == "music"` to `src/services/filtering.py` (depends on T034)
- [X] T036 [P] [US3] Add repeatable `--event-type`/`--genre` CLI flags to `src/cli/generate.py` (depends on T023)

**Checkpoint**: All three user stories independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Hardening and validation across all stories

- [X] T037 [P] Unit tests for dedup key normalization and tie-break rules in `tests/unit/test_dedup.py`
- [X] T038 [P] Unit tests for Markdown rendering (date grouping, unknown/free cost, zero-results) in `tests/unit/test_markdown.py`
- [X] T039 [P] Unit tests for LLM provider/model-string selection in `tests/unit/test_provider.py`
- [X] T040 [P] Usage documentation (install, env vars, example commands) in `README.md`
- [X] T041 Add missing-API-key handling (exit code 3, names the missing env var) to `src/cli/generate.py`
- [ ] T042 Run all `quickstart.md` scenarios end-to-end against a real (or sandboxed) provider + search key and confirm expected outcomes — **not run**: requires live `EVENT_CALENDAR_MODEL`/provider API key/`TAVILY_API_KEY` credentials not available in this environment; all scenarios are covered by mocked contract/integration tests instead

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational only
- **User Story 2 (Phase 4)**: Depends on Foundational; extends US1's `filtering.py`/`generate.py`/`markdown.py`, so start after Phase 3's T020/T022/T023 exist
- **User Story 3 (Phase 5)**: Depends on Foundational; extends the same `filtering.py`/`generate.py`, so start after Phase 3's T020/T023 exist
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### Within Each User Story

- Tests written first, before implementation tasks in that phase
- Models (Foundational) before services
- Services (discovery/filter/dedup/render) before the `generate` CLI wiring task
- Story complete and independently testable before moving to the next priority

### Parallel Opportunities

- T003 (Setup) can run alongside T001/T002 prep once the directories exist
- T004–T007 (Foundational models) are all `[P]` — different files, no dependency between them
- T013–T016 (US1 tests) are all `[P]`
- T017/T018 (US1 discovery clients) are `[P]` — different files
- T020/T021/T022 (US1 filter/dedup/render) are `[P]` — different files, all depend only on Foundational models
- T025–T027 (US2 tests) are all `[P]`
- T028/T029/T030 (US2 filter/CLI-flag/render) are `[P]` — different files
- T031–T033 (US3 tests) are all `[P]`
- T037–T040 (Polish) are all `[P]`

---

## Parallel Example: User Story 1

```bash
# Tests for User Story 1 together:
Task: "Contract test for calendar generate required/invalid args in tests/contract/test_generate_contract.py"
Task: "Integration test: location + calendar-length only in tests/integration/test_generate_basic.py"
Task: "Integration test: no optional preferences set in tests/integration/test_generate_no_optional_prefs.py"
Task: "Integration test: zero matching events in tests/integration/test_generate_zero_results.py"

# Discovery clients for User Story 1 together:
Task: "Trusted-source fetch+extract client in src/services/discovery/trusted_source_client.py"
Task: "Web-search fallback client in src/services/discovery/web_search_client.py"

# Filter/dedup/render for User Story 1 together:
Task: "Date-range + type/genre-unset filtering in src/services/filtering.py"
Task: "Duplicate-event merge in src/services/dedup.py"
Task: "Markdown rendering in src/services/markdown.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (includes trusted-source list management, since discovery depends on it)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run Scenario 1 (and 6) from `quickstart.md` independently
5. This is a usable MVP — `calendar generate --location ... --calendar-length-days ...` produces a real calendar

### Incremental Delivery

1. Setup + Foundational → foundation ready (models, config, LLM provider, trusted-source storage/CLI)
2. Add User Story 1 → validate via quickstart Scenarios 1 & 6 → MVP
3. Add User Story 2 → validate via quickstart Scenarios 2 & 3
4. Add User Story 3 → validate via quickstart Scenarios 4 & 5
5. Polish → run full quickstart suite, harden error handling

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US2 and US3 both extend files first created in US1 (`filtering.py`, `generate.py`, `markdown.py`) rather than creating new ones — this is intentional (filters compose) and is called out explicitly in each task's dependency note
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
