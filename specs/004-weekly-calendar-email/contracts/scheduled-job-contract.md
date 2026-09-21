# Scheduled Job Contract: Weekly Calendar Email

Unlike `contracts/cli-contract.md`, `mcp-contract.md`, or `web-contract.md`,
this is not a contract for an interface a person or client calls — per this
feature's Constitution Check, it deliberately has no such surface. This
document instead fixes the **deployment-configuration contract**: what
environment variables the container expects, what the entrypoint does, and
what the resulting email looks like. A change to any of these MUST update
this file in the same change, the same discipline Principle IV applies to
the other three contracts.

## Entrypoint

`python -m src.scheduled_job.main` (the container's `ENTRYPOINT`; also
installed as the `calendar-weekly-email` console script for local testing,
matching `calendar`/`calendar-mcp`/`calendar-web`'s convention).

Takes no command-line arguments and reads no stdin — all configuration is
environment variables (data-model.md's `WeeklyRecipe` and
`EmailDeliveryConfig`).

## Required environment variables

| Variable | Required | Notes |
|---|---|---|
| `WEEKLY_RECIPE_LOCATION` | Yes | |
| `WEEKLY_RECIPE_CALENDAR_LENGTH_DAYS` | Yes | Must be a positive integer |
| `WEEKLY_RECIPIENT_EMAIL` | Yes | |
| `SMTP_HOST` | Yes | |
| `SMTP_PORT` | Yes | |
| `SMTP_FROM_ADDRESS` | Yes | |
| `EVENT_CALENDAR_MODEL` | Yes | Same variable the CLI/MCP/web already require |
| A provider API key (e.g. `ANTHROPIC_API_KEY`) | Yes | Same convention as the other three interfaces |
| `WEEKLY_RECIPE_MAX_COST` | No | |
| `WEEKLY_RECIPE_EVENT_TYPES` | No | Comma-separated |
| `WEEKLY_RECIPE_GENRES` | No | Comma-separated |
| `WEEKLY_RECIPE_START_AFTER` / `WEEKLY_RECIPE_START_BEFORE` | No | Both-or-neither, `HH:MM` |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | No | Both-or-neither in practice; required by most real SMTP relays |
| `TAVILY_API_KEY` | No | Same fallback-only semantics as the other three interfaces |
| `EVENT_CALENDAR_TRUSTED_SOURCES` | No | Defaults the same way as the other interfaces; in the deployed image this points at the trusted-source list baked in at build time (spec.md Assumption) |

## Behavior

1. Build `WeeklyRecipe` and `EmailDeliveryConfig` from the environment
   (data-model.md). A missing required variable or an invalid recipe
   (non-positive `WEEKLY_RECIPE_CALENDAR_LENGTH_DAYS`, an incomplete
   start-window pair) is treated as a run failure — go directly to step 4
   with a validation-error message; no pipeline call is attempted.
2. Run the pipeline: `discover_events` → `dedup.dedup_events` →
   `filtering.filter_events` → `render_markdown`, exactly as the CLI/MCP/web
   interfaces already do (research.md #1).
3. On success (including zero matched events), build the success email.
4. On any failure — validation, `DiscoveryUnavailableError`,
   `MissingConfigError`, or any other unanticipated exception
   (research.md #5) — build the failure email instead.
5. Send exactly one email (step 3's or step 4's) via SMTP to
   `WEEKLY_RECIPIENT_EMAIL`. Sending itself failing (e.g. bad SMTP
   credentials) is logged and raises — there is no second delivery channel
   to fall back to; this is a genuine unrecoverable run failure, surfaced
   through the process exit code below since no email could be sent to
   explain it.
6. Exit `0` if an email was sent (success or failure notification both
   count as a "working" run for Cloud Run's own history), non-zero if no
   email could be sent at all (step 5's own failure).

## Email content contract

**Subject line**, one of exactly three forms:
- `Cultural Event Calendar: <location> (<N> events)` — success, events found
- `Cultural Event Calendar: <location> (no events found)` — success, zero
  events matched
- `Cultural Event Calendar: <location> — run failed` — failure

**Body**:
- Success: each event's name, date, time, venue, and cost, in the same
  human-readable form `render_markdown` already produces for the CLI/MCP/web
  interfaces (FR-002/SC-003 — results must match a manual run for the same
  preferences).
- Zero events: an explicit "no events matched" statement, never an empty
  body (FR-005).
- Failure: the plain-language exception message (e.g.
  `DiscoveryUnavailableError`'s "No trusted sources configured and web
  search is unavailable."), never a raw stack trace (FR-006).

## Config not covered here

`EVENT_CALENDAR_MODEL`, the provider API key, `TAVILY_API_KEY`, and
`EVENT_CALENDAR_TRUSTED_SOURCES` follow exactly the same contract already
defined in `../001-cultural-event-calendar/contracts/cli-contract.md`'s
Config section — not duplicated here.
