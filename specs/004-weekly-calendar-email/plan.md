# Implementation Plan: Scheduled Calendar Email

**Branch**: `004-weekly-calendar-email` | **Date**: 2026-09-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-weekly-calendar-email/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow. This feature is **not yet built** — this plan proposes the design, it does not document shipped code.

## Summary

Add a fourth, non-interactive trigger for the existing calendar-generation pipeline: a small `src/scheduled_job/` module, packaged as a Docker container and deployed as a **GCP Cloud Run Job**, that Cloud Scheduler runs once a week. On each run it calls the same `discover_events`/`filter_events`/`dedup_events`/`render_markdown` pipeline the CLI, MCP server, and web API already call in-process — using a preconfigured recipe (location, calendar length, and any optional filters) read from environment variables — then emails the rendered result (or a plain-language failure explanation) to a configurable recipient over SMTP. Per spec.md's FR-009, this deliberately does **not** become a new interactive, user-operated interface: no HTTP server, no new CLI flags, no MCP tools — just a batch entrypoint Cloud Scheduler triggers and an email as the only externally-visible output.

## Technical Context

**Language/Version**: Python 3.11+ (same runtime as the rest of the project).

**Primary Dependencies**: None new for the core logic — email is sent via the standard library (`smtplib`, `email.message`), and the module reuses the existing `litellm`/`httpx`/`pydantic`/`pyyaml`/`tavily-python`-backed pipeline (`src/services`, `src/llm/provider.py`, `src/config.py`) directly, the same way `src/mcp_server/server.py` and `src/web_api/app.py` already do. New deployment-only tooling: a `Dockerfile` (python:3.11-slim base) — not a Python dependency.

**Storage**: `trusted_sources.yaml` is baked into the container image at build time (spec.md Assumption — a stateless, reproducible scheduled job, not a live-mutable file). The generated Markdown file is written to the container's local, ephemeral filesystem purely as an intermediate step — Cloud Run Jobs containers are torn down after each run, so the email is the *only* durable output; nothing is meant to persist after the run the way the CLI's/MCP's/web's output files do on a long-lived machine.

**Testing**: `pytest` (already configured). `tests/unit/test_email_delivery.py` for email-formatting logic with a mocked SMTP connection (no live email sent, matching Principle V's deterministic-test spirit). `tests/integration/test_scheduled_job.py` for the full run (mocked `discover_events`, mocked SMTP) — success, zero-events, and failure-notification cases.

**Target Platform**: A Docker container (python:3.11-slim) with no listening port, run to completion by **Cloud Run Jobs** (not a Cloud Run *Service* — this workload never needs to accept an inbound request; see research.md #2), triggered on a weekly cron schedule by Cloud Scheduler.

**Project Type**: Single project — a fourth thin entrypoint package, `src/scheduled_job/`, alongside `cli/`, `mcp_server/`, and `web_api/`, sharing the same `services`/`llm`/`config` core. Unlike those three, it is not a Principle-IV "externally-facing interface" (no interactive external caller — see Constitution Check below and spec.md's governance note); it is packaged and deployed differently (a container image + a Cloud Run Job + a Cloud Scheduler trigger) rather than exposed as a stdio process, an HTTP server, or a console script a person runs directly.

**Performance Goals**: Not performance-critical — bounded by the same LLM/network-latency expectation as the other three interfaces. Must complete within whatever timeout the deployment configures for the Cloud Run Job execution (a deployment-configuration detail, not a code concern).

**Constraints**: Must reuse the existing pipeline unchanged (Principle I, II) — no forked filtering/discovery/dedup logic, no second LLM-access path. Must not introduce a new interactive interface (FR-009, Principle IV) — no HTTP server, no new CLI flags, no MCP tools; configuration is env-var-only. Must not silently fail — every run ends in exactly one email, success or failure (FR-006, SC-002). Single recipe, single recipient (spec.md Assumption) — no per-run overrides, no multi-recipient fan-out. Deployment (build, push, update the Cloud Run Job's image) is automated via **GitHub Actions**, authenticating to GCP with Workload Identity Federation rather than a long-lived service-account key (research.md #7) — this covers only 004's own container; it does not deploy 003's web frontend/backend or anything else in the repo.

**Scale/Scope**: One scheduled run per week, one recipient, one recipe. Same trusted-source-list scale as the other three interfaces (tens of entries), fixed at image-build time.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluated against Constitution v1.2.0.

| Principle | Status | Basis |
|---|---|---|
| I. No Fabrication | PASS | `src/scheduled_job/` calls the unmodified `discover_events`/`filter_events`/`dedup_events` pipeline in-process; no new event-data path, so the `"unknown"`-sentinel and merge-not-duplicate rules still apply unchanged. |
| II. Provider-Agnostic Model Access | PASS | No new LLM call path; `src/llm/provider.py`'s `LLMProvider`/`litellm` abstraction is reused as-is. Email delivery uses stdlib SMTP against a configurable host, not a vendor-specific SDK — consistent with the project's existing provider-agnostic ethos, even though Principle II's text is LLM-specific. |
| III. Plain-Files, Single-User Simplicity | PASS | No database; `trusted_sources.yaml` remains a plain file (baked into the image). No authentication or multi-tenancy — a single recipient configured via environment/secret. |
| IV. Stable Interface Contracts (CLI, MCP & Web) | PASS | This feature deliberately does **not** introduce a fourth interactive interface (FR-009): no HTTP server, no new CLI flags, no MCP tools. It calls the shared pipeline in-process the same way the MCP server and web API already do, and is triggered only by Cloud Scheduler, not by any external caller with an evolving contract. Its own deployment-configuration surface (expected environment variables, entrypoint behavior, email content) is documented in `contracts/scheduled-job-contract.md`, in the same spirit as the other three contract files, without requiring a principle amendment — there is no "someone calls this and gets a response" surface for the principle to govern. |
| V. Test-Verified Filtering | PASS | No new filter logic — reuses 001's already-tested filtering/dedup/rendering code paths verbatim. This feature's own test-verification target (recipe construction, email formatting, success/zero-events/failure delivery) is covered by new `tests/unit/test_email_delivery.py` and `tests/integration/test_scheduled_job.py`. |

**Post-Phase-1 re-check**: `contracts/scheduled-job-contract.md`, `data-model.md`, and `quickstart.md` (generated below) were reviewed against the same table — no drift found; still PASS. In particular, `data-model.md` introduces no fields beyond a preconfigured recipe and a notification outcome, and `contracts/scheduled-job-contract.md` confirms the entrypoint has no request/response surface, reinforcing the Principle IV basis above.

## Project Structure

### Documentation (this feature)

```text
specs/004-weekly-calendar-email/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── scheduled-job-contract.md
└── checklists/
    └── requirements.md  # /speckit-specify output
```

### Source Code (repository root)

```text
src/
├── scheduled_job/
│   ├── __init__.py
│   ├── main.py            # entrypoint: reads recipe env vars, runs the pipeline, sends the email
│   ├── recipe.py           # env vars -> UserPreferenceSet + recipient/SMTP config
│   └── email_delivery.py    # renders + sends the success/failure email over SMTP
├── llm/
│   └── provider.py          # unchanged — reused as-is
├── services/
│   └── discovery/
│       └── __init__.py      # unchanged — reused as-is
├── models/                   # unchanged — TrustedSource, CulturalEvent, MarkdownCalendar, UserPreferenceSet reused as-is
├── cli/                      # unchanged — this feature adds a new trigger, does not modify the CLI
├── mcp_server/                # unchanged
├── web_api/                   # unchanged
└── config.py                  # unchanged — same pipeline-wide config surface reused; new recipe/email/SMTP env vars are read directly in src/scheduled_job/, not added here (matches web_api/app.py's existing precedent for interface-specific config)

Dockerfile                     # container image for the Cloud Run Job (python:3.11-slim base, no listening port)

.github/
└── workflows/
    └── deploy-scheduled-job.yml  # build + push + update the Cloud Run Job on relevant changes (research.md #7)

deploy/
└── README.md                     # one-time gcloud bootstrap: Artifact Registry repo, the Cloud Run Job itself,
                                   # its Cloud Scheduler trigger, Secret Manager secrets, and the WIF pool/provider
                                   # + service account the workflow above authenticates as

tests/
├── unit/
│   └── test_email_delivery.py      # email formatting (success/zero-events/failure), mocked SMTP
└── integration/
    └── test_scheduled_job.py       # full run: mocked discover_events + mocked SMTP; success, zero-events, failure cases
```

**Structure Decision**: `src/scheduled_job/` joins `cli/`, `mcp_server/`, and `web_api/` as a fourth sibling package inside the existing `src/` tree, for the same reason those three are siblings rather than separate packages: direct, same-package access to `services`/`llm`/`config`/`models`. Unlike those three, it is not counted as a Principle-IV "externally-facing interface" (see Constitution Check) — it has no interactive external caller, so it is deployed differently (a `Dockerfile` + Cloud Run Job + Cloud Scheduler trigger, documented at the repository root and in `contracts/scheduled-job-contract.md`) rather than exposed as a console script a person runs directly, even though its code lives in the same place. The `.github/workflows/deploy-scheduled-job.yml` / `deploy/README.md` split mirrors that same one-time-setup-vs-ongoing-automation boundary: `deploy/README.md` is a manual runbook run once (or whenever the *infrastructure itself* changes — a new secret, a renamed job), while the workflow handles every *code* change to this feature going forward. This workflow is scoped to 004 only; it does not build or deploy `frontend/`, `src/web_api/`, or anything else in the repo.

## Complexity Tracking

*No Constitution Check violations — table not applicable.*
