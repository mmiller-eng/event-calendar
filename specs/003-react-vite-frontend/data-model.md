# Phase 1 Data Model: Web Frontend (React + Vite)

This feature introduces no new _persisted_ domain entities. It reuses
`TrustedSource`, `CulturalEvent`, `MarkdownCalendar`, and `UserPreferenceSet`
exactly as defined in
[../001-cultural-event-calendar/data-model.md](../001-cultural-event-calendar/data-model.md) —
the same entities the CLI and MCP server already operate on (per FR-008: "the
system MUST reuse the same filtering, deduplication, and discovery rules
already used by the CLI and MCP server").

What this feature adds are the HTTP request/response shapes
`src/web_api/schemas.py` needs to carry those entities across the
browser/backend boundary. These are transport models, not persisted records —
`trusted_sources.yaml` and the generated Markdown files remain the source of
truth, exactly as before.

## GenerateRequest (new)

The HTTP request body for triggering calendar generation — the web
equivalent of `UserPreferenceSet` plus the CLI's `--output`/`--model` flags.

| Field                  | Type            | Notes                                                                                   |
| ---------------------- | --------------- | --------------------------------------------------------------------------------------- |
| `location`             | `str`           | Required, matches CLI `--location`                                                      |
| `calendar_length_days` | `int`           | Required, > 0, matches CLI `--calendar-length-days`                                     |
| `max_cost`             | `float \| null` | Optional; `0` = free only; omitted = no ceiling                                         |
| `event_types`          | `list[str]`     | Optional, defaults to empty (all types)                                                 |
| `genres`               | `list[str]`     | Optional; applies only to music, per 001's rules                                        |
| `start_after`          | `str \| null`   | Optional, `HH:MM`                                                                       |
| `start_before`         | `str \| null`   | Optional, `HH:MM`                                                                       |
| `model`                | `str \| null`   | Optional; overrides `EVENT_CALENDAR_MODEL` for this request only, matches CLI `--model` |

**Validation**: identical rules to `UserPreferenceSet` (data-model.md, 001) —
`calendar_length_days` must be positive; an incomplete `start_after`/
`start_before` pair is rejected. Validation failures are returned as an
HTTP 422 with a message the frontend can display inline (see
`contracts/web-contract.md`).

## CalendarResponse (new)

The HTTP response body for a successful generation request.

| Field          | Type                 | Notes                                                                                                                              |
| -------------- | -------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `output_path`  | `str`                | Where the Markdown file was written on disk, matches CLI's printed path                                                            |
| `generated_at` | `str`                | ISO-format date string                                                                                                             |
| `events`       | `list[EventSummary]` | Structured event data for the frontend to render — see below                                                                       |
| `event_count`  | `int`                | `len(events)`; lets the frontend distinguish "zero events matched" from a loading/error state without special-casing an empty list |

### EventSummary (new, nested in CalendarResponse)

A flattened, browser-friendly projection of `CulturalEvent` (001's
data-model.md) — same fields, no new data.

| Field        | Type          | Notes                                                                                                                                                                  |
| ------------ | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`       | `str`         |                                                                                                                                                                        |
| `date`       | `str`         | ISO date                                                                                                                                                               |
| `start_time` | `str`         | `HH:MM`, or the literal string `"unknown"` per Principle I                                                                                                             |
| `venue`      | `str`         |                                                                                                                                                                        |
| `cost`       | `str`         | Rendered as-is (e.g. `"free"`, `"$25"`, or `"unknown"`) — kept as a display string, not a numeric type, so `"unknown"` never has to be smuggled through a number field |
| `event_type` | `str`         |                                                                                                                                                                        |
| `genre`      | `str \| null` | Only set for music events                                                                                                                                              |
| `source_url` | `str`         | Where the event was found, for user trust/verification                                                                                                                 |

**Why not just return the rendered Markdown as one string?** FR-002 requires
the frontend to _display_ the calendar, and SC-001 requires it to be readable
entirely in the browser — a structured `events` list lets the frontend render
a proper list/table (sortable, filterable-by-eye) instead of dumping raw
Markdown into the page. `output_path` is still included so the frontend can
tell the user where the equivalent file lives on disk, matching the CLI's own
output contract.

## SourceResponse (new)

The HTTP response body for `POST /sources` and `DELETE /sources` — reuses the
exact shape of `SourceResult`, the structured MCP tool result already defined
for `add_source`/`remove_source` in 002 (`specs/002-mcp-server/plan.md`'s
Project Structure references it; the model itself was never persisted to
`002`'s `data-model.md` before that feature's planning was paused — this spec
defines the canonical shape going forward).

| Field      | Type  | Notes                                                                   |
| ---------- | ----- | ----------------------------------------------------------------------- |
| `name`     | `str` | The affected source's name                                              |
| `url`      | `str` | Plain string (`TrustedSource.url: HttpUrl` converted to `str` for JSON) |
| `added_at` | `str` | ISO-format date string                                                  |

**Used by**: `POST /sources` (create-or-return-existing, per FR-005 — no
duplicate on re-add) and `DELETE /sources` (raises a 404 with a "not found"
message if the URL isn't on the list, per FR-006).

`GET /sources` returns `list[SourceResponse]` directly (no extra wrapper
object needed — see `contracts/web-contract.md`).

## Tool/route parameter shapes (reference only — not new entities)

Full endpoint-by-endpoint request/response contracts, status codes, and error
shapes belong in `contracts/web-contract.md`, not duplicated here. This file
only defines the shapes those contracts reference.
