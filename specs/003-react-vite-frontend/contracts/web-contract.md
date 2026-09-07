# Web Contract: Cultural Event Calendar — Web API

This is the third of the project's externally-facing interfaces (Principle
IV, v1.2.0), alongside `contracts/cli-contract.md` (001) and the still-pending
`contracts/mcp-contract.md` (002). Contract tests live in
`tests/contract/web_api_contract_test.py` and assert on route shape, status
codes, and response schema — not on live network/LLM results (mocked, same
convention as the CLI's contract tests per 001's research.md #6).

All routes are served by `src/web_api/app.py`, bound to `localhost` only. No
authentication. CORS restricted to the frontend's own origin (research.md
#3).

## `POST /api/calendar`

Runs a single calendar-generation request (mirrors `calendar generate`;
US1, FR-001, FR-002, FR-008, FR-010).

**Request body**: `GenerateRequest` (data-model.md).

**Behavior**:

1. Validate the body; a missing/non-positive `calendar_length_days`, or an
   incomplete `start_after`/`start_before` pair, is rejected before any
   discovery call is made.
2. Discover candidates: trusted sources first, then live web search fallback
   (same as FR-002 in 001/002).
3. Filter, dedupe, render — identical pipeline to 001/002.
4. Write the Markdown file to disk (same default path convention as the CLI)
   and return `CalendarResponse` (data-model.md) describing it.

**Status codes**:

| Code | Meaning                                                                                                                                                                                                                        |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 200  | Calendar generated and written — including the zero-matching-events case (`event_count: 0`, not an error, per FR-002's Acceptance Scenario 3)                                                                                  |
| 422  | Invalid/missing required fields in the request body                                                                                                                                                                            |
| 503  | All discovery sources unreachable (no trusted sources configured AND web search call failed) — distinct from "zero results found"; body carries the same plain-language message the CLI/MCP already produce for this condition |
| 409  | A generation request is already in progress for this session (edge case in spec.md)                                                                                                                                            |

## `GET /api/sources`

Lists trusted sources (mirrors `calendar sources list`; US2, FR-003).

**Response**: `200` with `list[SourceResponse]` (data-model.md) — an empty
list (not an error) when no sources are configured, matching FR-002a's CLI
behavior.

## `POST /api/sources`

Adds a trusted source (mirrors `calendar sources add`; US2, FR-004, FR-005).

**Request body**: `{"name": str, "url": str}`.

**Status codes**:

| Code | Meaning                                                                                                                        |
| ---- | ------------------------------------------------------------------------------------------------------------------------------ |
| 200  | Source added — returns `SourceResponse`                                                                                        |
| 200  | URL already existed — returns the existing `SourceResponse` unchanged, per FR-005 (no duplicate created; this is not an error) |
| 422  | Missing/malformed `url`                                                                                                        |

## `DELETE /api/sources`

Removes a trusted source by URL (mirrors `calendar sources remove`; US2,
FR-006).

**Request**: `url` as a query parameter (`DELETE /api/sources?url=...`).

**Status codes**:

| Code | Meaning                                                                                               |
| ---- | ----------------------------------------------------------------------------------------------------- |
| 200  | Removed — returns the removed entry's `SourceResponse`                                                |
| 404  | `url` was not on the trusted-source list — body carries a plain-language "not found" message (FR-006) |
| 422  | Missing `url` query parameter                                                                         |

## Config (not a route, but part of the contract surface)

Same environment-variable contract as 001/002 —
`EVENT_CALENDAR_MODEL`/provider API key/`TAVILY_API_KEY` — the backend reads
these via the existing `src/config.py`, unchanged. No new configuration
surface is introduced for the web interface (plan.md's Constraints).

## Frontend routes (client-side, not HTTP — documented here for completeness)

| Route          | View                      | Notes                                                                                        |
| -------------- | ------------------------- | -------------------------------------------------------------------------------------------- |
| `/`            | Generate view (US1)       | Default route; shows the most recently generated calendar in this session, if any (US3, AC2) |
| `/sources`     | Manage-sources view (US2) |                                                                                              |
| any other path | Not-found view            | Plain "page not found" state, per spec.md's Edge Cases — not a blank page                    |

Navigation between `/` and `/sources` MUST NOT trigger a full page reload
(FR-007, SC-002).
