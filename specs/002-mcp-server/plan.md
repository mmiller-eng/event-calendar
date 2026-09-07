# Implementation Plan: MCP Server Access

**Branch**: `002-mcp-server` | **Date**: 2026-09-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-mcp-server/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow. This feature was already implemented (`src/mcp_server/`) before this plan was written — the plan documents the shipped design rather than proposing a new one, per the spec's own framing.

## Summary

Expose the existing calendar-generation and trusted-source-management pipeline as an [MCP](https://modelcontextprotocol.io) server over stdio (`src/mcp_server/server.py`), so any MCP-compatible client (Claude Code, Claude Desktop, the MCP Inspector) can call `generate_calendar`, `list_sources`, `add_source`, and `remove_source` directly — without shelling out to the CLI or parsing its text output. Each tool calls the same `src/services`/`src/llm`/`src/config` code the CLI already uses, in-process, so results are identical regardless of interface (FR-005). Anticipated failures (invalid input, no usable sources, a removal target that doesn't exist) are raised as `mcp.server.mcpserver.exceptions.ToolError` so their message reaches the calling client (FR-006–FR-008) instead of being swallowed by the SDK's generic crash handling.

## Technical Context

**Language/Version**: Python 3.11+ (same runtime as the rest of the project)

**Primary Dependencies**: `mcp[cli]>=1.8.0` (official MCP Python SDK — `mcp.server.mcpserver.MCPServer`, stdio transport), `pydantic` (tool parameter schemas via `Field`, structured tool-output models). No new business-logic dependencies — this feature calls the existing `litellm`/`httpx`/`beautifulsoup4`/`pyyaml`/`tavily-python`-backed pipeline (`src/services`, `src/llm/provider.py`, `src/config.py`) directly.

**Storage**: Unchanged from 001 — `trusted_sources.yaml` and generated Markdown calendar files on disk. No new storage introduced.

**Testing**: `pytest` + `pytest-asyncio` (`asyncio_mode = "auto"`, `tool.pytest.ini_options` in `pyproject.toml`). Integration tests (`tests/integration/mcp_client_test.py`) spin up the real server as a subprocess over stdio via a small reusable client (`src/mcp_server/client.py`, `MCPClient`) and drive it exactly as an external MCP client would — no mocked transport.

**Target Platform**: Same as the CLI — cross-platform; the server is a Python subprocess launched over stdio, so it runs anywhere an MCP client can spawn `python -m src.mcp_server.server` (or the `calendar-mcp` console-script entry point).

**Project Type**: Single project — this is an additional thin interface (`src/mcp_server/`) inside the existing CLI project, not a separate service or repo.

**Performance Goals**: Not performance-critical; bounded by the same expectation as 001's SC-001 (LLM/network latency dominates). stdio round-trip overhead is negligible in comparison.

**Constraints**: Must reuse 001's pipeline logic unchanged (no second implementation of filtering/dedup/discovery) — Principle IV now requires this interface to carry its own stable contract (tool names, parameters, error behavior), documented in `contracts/mcp-contract.md`, analogous to `contracts/cli-contract.md`. Must not introduce a second configuration surface (spec Assumptions) — same env vars, same `trusted_sources.yaml`. Single MCP client connection at a time; no concurrency requirements (matches 001's Scale/Scope).

**Scale/Scope**: Single user, single local MCP client connection; same trusted-source-list scale as 001 (tens of entries).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluated against Constitution v1.1.0 (amended 2026-09-06 specifically to unblock this feature — see `.specify/memory/constitution.md` Sync Impact Report).

| Principle | Status | Basis |
|---|---|---|
| I. No Fabrication | PASS | `generate_calendar` calls the unmodified `discover_events`/`filter_events`/`dedup_events` pipeline from 001; no new event-data path is introduced, so the `"unknown"`-sentinel and merge-not-duplicate rules still apply unchanged. |
| II. Provider-Agnostic Model Access | PASS | No new LLM call path; `src/llm/provider.py`'s `LLMProvider`/`litellm` abstraction is reused as-is. The one addition (`LLMRequestError`, research.md #5) wraps provider exceptions for error-handling purposes only — it does not add a second model-access path. |
| III. Plain-Files, Single-User Simplicity | PASS | No new storage; same `trusted_sources.yaml` + Markdown files; no auth/multi-tenancy added (spec Assumptions). |
| IV. Stable Interface Contracts (CLI & MCP) | PASS | This principle was amended specifically to recognize the MCP server as the second stable interface. `contracts/mcp-contract.md` (Phase 1 output) documents its tool names, parameters, and error-response behavior, the MCP-side equivalent of `contracts/cli-contract.md`. |
| V. Test-Verified Filtering | PASS | No new filter logic — `generate_calendar` reuses 001's already-tested filtering/dedup/rendering code paths verbatim. This feature's own test-verification target (its 4 tools + their error paths) is covered by `tests/integration/mcp_client_test.py` (9 tests, all passing against the live stdio server). |

**Post-Phase-1 re-check**: `contracts/mcp-contract.md` and `data-model.md` (generated below) were reviewed against the same table — no drift found; still PASS.

## Project Structure

### Documentation (this feature)

```text
specs/002-mcp-server/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
├── contracts/             # Phase 1 output (/speckit-plan command)
│   └── mcp-contract.md
└── checklists/
    └── requirements.md    # /speckit-specify output
```

### Source Code (repository root)

```text
src/
├── mcp_server/
│   ├── __init__.py
│   ├── server.py        # MCPServer instance + 4 @mcp.tool functions; main() runs stdio transport
│   └── client.py         # MCPClient: reusable stdio client (connect/session/cleanup), used by tests
├── llm/
│   └── provider.py       # unchanged interface; LLMRequestError added for provider-failure handling
├── services/
│   └── discovery/
│       └── __init__.py   # unchanged interface; now also catches LLMRequestError per-source
├── models/                # unchanged — TrustedSource, CulturalEvent, MarkdownCalendar, UserPreferenceSet reused as-is
├── cli/                   # unchanged — this feature adds a second interface, does not modify the CLI
└── config.py              # unchanged — same config surface used by both interfaces

tests/
├── conftest.py            # shared `client` fixture (constructs MCPClient) + `_llm_env` fixture (isolated env per test)
└── integration/
    └── mcp_client_test.py # 9 tests: tool discovery, all 4 tools' happy paths, and 4 distinct error conditions
```

**Structure Decision**: Option 1 (single project), same as 001 — this feature adds one new package (`src/mcp_server/`) and its tests inside the existing `src/`/`tests/` layout; no new project or service boundary. `mcp_server/` is broken out at the same level as `cli/` because both are externally-facing interfaces over the same `services`/`llm`/`config` core (Principle IV), not a component of either.

## Complexity Tracking

*No Constitution Check violations — table not applicable.*
