# CLI Contract: Cultural Event Calendar Agent

This is the only externally-facing interface (single-user local CLI, no API/UI). Contract tests in `tests/contract/` assert on argument parsing, exit codes, and output shape — not on live network/LLM results (those are mocked, per research.md #6).

## `calendar generate`

Runs a single calendar-generation request (US1, US2, US3; FR-001 through FR-009).

```text
calendar generate
  --location TEXT             (required)
  --calendar-length-days INT  (required, > 0)
  --max-cost DECIMAL          (optional; 0 = free only; omitted = no ceiling)
  --event-type TEXT           (optional, repeatable; omitted = all types)
  --genre TEXT                (optional, repeatable; applies only to music)
  --start-after TIME          (optional; HH:MM)
  --start-before TIME         (optional; HH:MM)
  --output PATH                (optional; default: ./calendars/<generated-at date>.md)
  --model TEXT                 (optional; overrides EVENT_CALENDAR_MODEL env var for this run)
```

**Preconditions**: `trusted_sources.yaml` exists (may be empty list — command must not fail if absent, per Assumptions: "list may start small or empty").

**Behavior**:
1. Load `UserPreferenceSet` from flags; reject with exit code 2 and a usage message if `--calendar-length-days` is missing/non-positive.
2. Discover candidates: trusted sources first, then live web search fallback (FR-002).
3. Filter (data-model.md filtering rules), dedupe (FR-007), render `MarkdownCalendar`.
4. Write to `--output` path (create parent dirs as needed). Print the resolved output path to stdout.

**Exit codes**:
| Code | Meaning |
|---|---|
| 0 | Markdown file written successfully — including the zero-matching-events case (FR-009: file still written, with the explicit "no events matched" statement as content, not an error) |
| 2 | Invalid/missing required arguments |
| 3 | All discovery sources unreachable (no trusted sources configured AND web search call failed) — distinct from "zero results found" |

**Output contract**: file at the resolved path is well-formed Markdown (FR-004) satisfying data-model.md's `MarkdownCalendar` rendering rule. SC-003 requires date/time/venue/cost to be readable from this file alone.

## `calendar sources list`

```text
calendar sources list
```

Prints each `TrustedSource` (`name`, `url`, `added_at`) as one line. Prints a explicit "no trusted sources configured" message (not a blank output) when the list is empty. Exit code 0 always (empty list is not an error, per FR-002a).

## `calendar sources add`

```text
calendar sources add --name TEXT --url URL
```

Appends a `TrustedSource` to `trusted_sources.yaml`. Exit code 0 on success, 2 on invalid/missing `--url`, 4 if `--url` already exists in the list (duplicate — no-op, reports existing entry).

## `calendar sources remove`

```text
calendar sources remove --url URL
```

Removes the entry matching `--url`. Exit code 0 on success (including if already absent — idempotent remove), 2 on missing `--url` flag.

## Config (not a subcommand, but part of the contract surface)

- `EVENT_CALENDAR_MODEL` env var — `provider/model` string passed to `litellm` (e.g. `anthropic/claude-sonnet-5`). Required unless `--model` is passed to `generate`.
- Provider API key — standard env var for whichever provider is selected (e.g. `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`), per `litellm` convention. Missing key surfaces as exit code 3 (discovery/extraction cannot run) with a message naming the missing variable.
- `TAVILY_API_KEY` env var — required for the web-search fallback step; if absent, discovery falls back to trusted-sources-only and the run proceeds (does not hard-fail), since FR-002 only requires web search as a *fallback*, not a hard dependency.
