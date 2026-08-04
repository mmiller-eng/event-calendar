# Implementation Plan: Cultural Event Calendar Agent

**Branch**: `001-cultural-event-calendar` | **Date**: 2026-08-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-cultural-event-calendar/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

A standalone, model-agnostic CLI agent that takes a user's cultural-event preferences (location, cost ceiling, event type(s), music genre(s), calendar length, preferred start-time window), discovers candidate events by first checking a user-maintained trusted local source list and then falling back to live web search, filters/dedupes/normalizes the results, and writes a single chronologically-ordered Markdown calendar file. The agent's LLM calls are routed through a provider-agnostic abstraction so the user can run it against Claude, OpenAI, or other supported models rather than being locked to one vendor.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `litellm` (provider-agnostic LLM calls — Anthropic, OpenAI, and others behind one interface), `httpx` (fetching trusted-source pages), `beautifulsoup4` (HTML → text extraction from source pages), `pydantic` (data models/validation), `click` (CLI), Tavily search API client (live web-search fallback), `pyyaml` (config + trusted-source list storage)

**Storage**: Plain files — trusted source list as a YAML/JSON file on disk, generated calendars as Markdown files on disk. No database.

**Testing**: `pytest`, with `pytest-httpx`/`respx` for mocking HTTP calls to source pages, search API, and LLM provider

**Target Platform**: Cross-platform CLI (developed/run on Windows; must also run on macOS/Linux since it's a plain Python script with no OS-specific dependencies)

**Project Type**: Single project — CLI tool

**Performance Goals**: Not performance-critical; bounded by SC-001 (<2 minutes of active user interaction per run). Network/LLM latency dominates; no throughput targets.

**Constraints**: Must support switching the LLM provider/model via configuration (env var or config file) without code changes, per user requirement to invoke models other than Claude; must not fabricate event data — every field the agent cannot verify is marked "unknown"; single-user, local-only, no auth/multi-tenancy.

**Scale/Scope**: Single user; trusted source list on the order of tens of entries; calendar windows up to ~1 month; one calendar-generation request at a time (no concurrency requirements).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is still the unfilled template — no project-specific principles have been ratified yet. There is nothing enforceable to check against, so this gate is treated as **PASS (no-op)**. Recommendation: run `/speckit-constitution` to establish real principles (e.g., no-fabrication of event data, provider-agnostic LLM access) before this feature reaches implementation, since both are already implicit requirements in the spec (FR-008) and Technical Context above.

## Project Structure

### Documentation (this feature)

```text
specs/001-cultural-event-calendar/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
├── contracts/             # Phase 1 output (/speckit-plan command)
└── tasks.md               # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
├── models/            # Pydantic models: UserPreferenceSet, CulturalEvent, TrustedSource, MarkdownCalendar
├── services/
│   ├── discovery/      # trusted_source_client.py (fetch+extract), web_search_client.py (Tavily fallback)
│   ├── filtering.py    # applies location/cost/type/genre/start-time/date-range filters
│   ├── dedup.py         # merges duplicate listings of the same real-world event
│   └── markdown.py      # renders MarkdownCalendar -> .md file
├── llm/
│   └── provider.py      # litellm-based provider-agnostic LLM client (model selected via config)
├── cli/
│   ├── generate.py      # `calendar generate` command
│   └── sources.py        # `calendar sources list|add|remove` commands
└── config.py             # loads provider/model + API key config, trusted-source file path

tests/
├── contract/              # CLI command contracts (see contracts/)
├── integration/           # end-to-end: preferences in -> Markdown calendar out, using mocked discovery/LLM
└── unit/                  # filtering, dedup, markdown rendering, provider selection
```

**Structure Decision**: Option 1 (single project). This is a single local CLI tool with no frontend/backend split and no mobile target, so the standard `src/` + `tests/` layout applies directly. `llm/` is broken out from `services/` because provider-agnostic model access is a first-class constraint (not just an implementation detail of one service).

## Complexity Tracking

*No Constitution Check violations — table not applicable.*
