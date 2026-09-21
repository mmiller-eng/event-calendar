---
description: "Task list template for feature implementation"
---

# Tasks: Scheduled Calendar Email

**Input**: Design documents from `/specs/004-weekly-calendar-email/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/scheduled-job-contract.md, quickstart.md (all present)

**Tests**: Included — plan.md's Constitution Check commits this feature's own recipe/email logic to Principle V test coverage, and quickstart.md's "Automated equivalent" section names `tests/unit/test_email_delivery.py` and `tests/integration/test_scheduled_job.py` explicitly.

**Organization**: Tasks are grouped by user story (spec.md: US1 automated email, P1; US2 failure notification, P2; US3 config-only recipe updates, P3) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are included in every description

## Path Conventions

Per plan.md's Structure Decision: a new sibling package `src/scheduled_job/` (alongside `cli/`, `mcp_server/`, `web_api/`), a root `Dockerfile`, tests under `tests/unit/` and `tests/integration/` (existing convention).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization for the new package and its container packaging

- [x] T001 Create `src/scheduled_job/__init__.py` and empty `src/scheduled_job/main.py`, `src/scheduled_job/recipe.py`, `src/scheduled_job/email_delivery.py`
- [x] T002 Add a `calendar-scheduled-job = "src.scheduled_job.main:main"` entry under `[project.scripts]` in `pyproject.toml` — no new Python dependencies needed, email delivery uses the standard library (research.md #3)
- [x] T003 [P] Create a `Dockerfile` at the repo root: `python:3.11-slim` base, installs the project, `ENTRYPOINT ["python", "-m", "src.scheduled_job.main"]`, no exposed port (research.md #2; contracts/scheduled-job-contract.md)
- [x] T004 [P] Confirm the existing root `[tool.ruff]` config in `pyproject.toml` already covers `src/scheduled_job/` (it should, via the existing `src*` package include)

**Checkpoint**: `src/scheduled_job/` exists as an empty, lintable package; the container builds (even though its entrypoint does nothing yet)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Env-var parsing, email formatting/sending, and the entrypoint's error-handling skeleton that every user story depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 [P] Implement `Recipe` and `EmailDeliveryConfig` construction from environment variables in `src/scheduled_job/recipe.py`, including validation (positive `calendar_length_days`, complete `RECIPE_START_AFTER`/`RECIPE_START_BEFORE` pair) — a validation failure is treated as a run failure, not raised to a caller (data-model.md; contracts/scheduled-job-contract.md step 1)
- [ ] T006 [P] Implement `RunOutcome` → subject/body mapping (the three email shapes: events found, zero events, failure) and SMTP sending via `smtplib`/`email.message.EmailMessage` in `src/scheduled_job/email_delivery.py` (data-model.md `RunOutcome`; contracts/scheduled-job-contract.md's Email content contract)
- [ ] T007 Implement `src/scheduled_job/main.py`'s entrypoint: build the recipe/config via T005 (catching its validation failures), wrap the pipeline call in `try`/`except` for `DiscoveryUnavailableError`/`MissingConfigError`, always call `email_delivery.send(...)` (T006) exactly once, exit `0`/non-zero per contracts/scheduled-job-contract.md step 6; includes `main()`/`if __name__ == "__main__"` for the `calendar-scheduled-job` console script (depends on T005, T006) — the actual pipeline call itself is wired in T010 (US1)

**Checkpoint**: Foundation ready — recipe parsing, email formatting/sending, and the entrypoint's error-handling shape all exist; the pipeline call itself is still a stub. User story implementation can now begin.

---

## Phase 3: User Story 1 - Receive a calendar by email automatically (Priority: P1) 🎯 MVP

**Goal**: A real scheduled run generates a calendar and emails it to the configured recipient.

**Independent Test**: Configure the recipe (location, calendar length, recipient) once, trigger a single run, and confirm an email arrives at the configured address containing a calendar matching what `calendar generate` would produce for the same preferences and source data.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T008 [P] [US1] Unit tests for `email_delivery.py`'s success and zero-events email content (subject/body shapes) in `tests/unit/test_email_delivery.py`
- [ ] T009 [P] [US1] Integration test for a full successful scheduled run (mocked `discover_events`, mocked SMTP) in `tests/integration/test_scheduled_job.py`, asserting exactly one email is sent with the expected subject/body

### Implementation for User Story 1

- [ ] T010 [US1] Wire `main.py`'s success path: call the real pipeline (`discover_events` → `dedup.dedup_events` → `filtering.filter_events` → `render_markdown`) in-process (research.md #1), build `RunOutcome(status="success", events=matched)`, hand it to `email_delivery.send` (depends on T005–T007)
- [ ] T011 [US1] Confirm the zero-matched-events case routes through the same success path with the "no events found" subject/body (FR-005) — `RunOutcome` with an empty `events` list, not a separate branch

**Checkpoint**: User Story 1 is fully functional and independently testable — a real scheduled run sends a success email with events, or an explicit "no events found" message.

---

## Phase 4: User Story 2 - Get notified when a scheduled run fails (Priority: P2)

**Goal**: Every run — success or failure — ends in exactly one email; nothing fails silently.

**Independent Test**: Force a failure condition (no trusted sources reachable, no web-search fallback), trigger a run, and confirm a notification email is still sent explaining the failure in plain language.

### Tests for User Story 2

- [ ] T012 [P] [US2] Unit test for `email_delivery.py`'s failure email content in `tests/unit/test_email_delivery.py`
- [ ] T013 [P] [US2] Integration test for a failed scheduled run (no sources reachable) in `tests/integration/test_scheduled_job.py`, asserting exactly one failure email is sent containing the plain-language `DiscoveryUnavailableError` message

### Implementation for User Story 2

- [ ] T014 [US2] Wire `main.py`'s failure path: catch `DiscoveryUnavailableError`, `MissingConfigError`, and T005's recipe-validation failures; build `RunOutcome(status="failure", error_message=str(exc))`; send via `email_delivery.send` (depends on T007)
- [ ] T015 [US2] Add a bare `except Exception` catch-all around the pipeline call in `main.py` so a genuinely unanticipated error still produces a failure email rather than a silent crash (research.md #5; FR-006/SC-002)

**Checkpoint**: User Stories 1 AND 2 both work — every run ends in exactly one email, success or failure.

---

## Phase 5: User Story 3 - Update the recipe without a code change (Priority: P3)

**Goal**: An operator can change the location, calendar length, or recipient purely through deployment configuration.

**Independent Test**: Change the configured recipient address or location via environment variables (no code change), re-run, and confirm the new values take effect.

### Tests for User Story 3

- [ ] T016 [P] [US3] Integration test confirming a changed `RECIPE_LOCATION`/`RECIPIENT_EMAIL` (env vars only, no code change) changes the next run's generated location/recipient, in `tests/integration/test_scheduled_job.py`

### Implementation for User Story 3

- [ ] T017 [US3] Add a short "Changing the recipe" note to `quickstart.md`'s Deployment validation section, and a comment at the top of `src/scheduled_job/recipe.py`, both stating explicitly which values are safe to change via redeploy-with-new-env-vars alone (no rebuild of application logic needed) — this story's behavior is otherwise already satisfied by T005's design (recipe is read fresh from the environment on every run, never cached or hardcoded); T016's test is what actually proves it

**Checkpoint**: All three user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Deployment readiness and documentation

- [ ] T018 [P] Add a "Scheduled Calendar Email" section to the root `README.md` documenting local run (`calendar-scheduled-job`), Docker build/run, and the required environment variables — mirroring the existing "MCP Server"/"Web Frontend" sections' structure
- [ ] T019 [P] Add a `.dockerignore` at the repo root (excludes `.venv/`, `frontend/node_modules/`, `calendars/`, `.git/`, `specs/`, test caches) to keep the built image lean
- [ ] T020 [P] Add `deploy/README.md`: a one-time `gcloud` bootstrap runbook covering the Artifact Registry repository, the Cloud Run Job itself, its weekly Cloud Scheduler trigger, the Secret Manager secrets for the LLM provider key and SMTP credentials, and the Workload Identity Federation pool/provider + service account T022's workflow authenticates as (research.md #7) — a runbook run once (or whenever the infrastructure itself changes), not committed infrastructure-as-code
- [ ] T021 Run `specs/004-weekly-calendar-email/quickstart.md`'s manual validation scenarios end-to-end against a real local SMTP debug server
- [ ] T022 [P] Add `.github/workflows/deploy-scheduled-job.yml`: on push to `main` touching `src/scheduled_job/`, `src/services/`, `src/llm/`, `src/models/`, `src/config.py`, or `Dockerfile` (plus a manual `workflow_dispatch` trigger), authenticate to GCP via Workload Identity Federation (`google-github-actions/auth`), build and push the image to Artifact Registry, then `gcloud run jobs update` the existing Cloud Run Job with the new image (research.md #7; contracts/scheduled-job-contract.md) — scoped to this feature only, does not build or deploy `frontend/`, `src/web_api/`, or anything else in the repo

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3–5)**: All depend on Foundational phase completion
  - US1 has no dependency on US2 or US3
  - US2 depends on `main.py`'s skeleton (T007) existing, same as US1, but its own try/except branches (T014–T015) are additive to US1's success path (T010) rather than requiring US1's implementation tasks to be done first
  - US3 has no new implementation dependency on US1/US2 — its test (T016) exercises the same entrypoint either story already wired, so in practice it's easiest to validate last
- **Polish (Phase 6)**: Depends on all three user stories being complete. T022's *workflow file* can be written in parallel with T020's runbook (different files), but the workflow can only succeed *at runtime* once T020's one-time bootstrap (the Artifact Registry repo, the Cloud Run Job, and the WIF pool/service account it authenticates as) has actually been run once against the real GCP project — that ordering is an operational step, not a file-writing dependency.

### Within Each User Story

- Tests written and failing before implementation
- `recipe.py`/`email_delivery.py` (Foundational) before anything in `main.py` that calls them
- Story complete before moving to next priority

### Parallel Opportunities

- T003, T004 (Setup) can run in parallel — independent files
- T005, T006 (Foundational) can run in parallel — independent files, neither depends on the other
- T008, T009 (US1 tests) can run in parallel
- T012, T013 (US2 tests) can run in parallel
- T018, T019, T020, T022 (Polish) can run in parallel — independent files

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit tests for email_delivery.py's success/zero-events content in tests/unit/test_email_delivery.py"
Task: "Integration test for a successful scheduled run in tests/integration/test_scheduled_job.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run quickstart.md's US1 scenarios against a real SMTP debug server
5. Demo: a working weekly-email flow, even without failure notification or documented config-only updates

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. Add User Story 1 → validate independently → demo (MVP!)
3. Add User Story 2 → validate independently → demo (reliability)
4. Add User Story 3 → validate independently → demo (operability)
5. Phase 6 polish → deployment-ready

---

## Notes

- [P] tasks touch different files with no unfinished dependency between them
- [Story] labels map every implementation task back to spec.md's user stories for traceability
- US3 is intentionally the lightest implementation phase — its behavior falls out of T005's design; its value is proven by a test, not new code
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently before continuing
