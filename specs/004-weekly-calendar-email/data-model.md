# Phase 1 Data Model: Scheduled Calendar Email

This feature introduces no changes to how events are discovered, filtered,
or rendered. It reuses `TrustedSource`, `CulturalEvent`, `MarkdownCalendar`,
and `UserPreferenceSet` exactly as defined in
[../001-cultural-event-calendar/data-model.md](../001-cultural-event-calendar/data-model.md).

What it adds are the shapes needed to get from environment variables to a
pipeline call, and from a pipeline result to an email.

## Recipe (new)

Built by `src/scheduled_job/recipe.py` from environment variables; converted
directly into a `UserPreferenceSet` (001's data-model.md) before calling the
pipeline — this is not a new set of preference fields, just where they come
from for this trigger.

| Field | Source env var | Type | Notes |
|---|---|---|---|
| `location` | `RECIPE_LOCATION` | `str` | Required |
| `calendar_length_days` | `RECIPE_CALENDAR_LENGTH_DAYS` | `int` | Required, > 0 |
| `max_cost` | `RECIPE_MAX_COST` | `Decimal \| None` | Optional; `0` = free only; unset = no ceiling |
| `event_types` | `RECIPE_EVENT_TYPES` | `list[str]` | Optional, comma-separated; unset = all types |
| `genres` | `RECIPE_GENRES` | `list[str]` | Optional, comma-separated; applies only to music |
| `start_time_window` | `RECIPE_START_AFTER` / `RECIPE_START_BEFORE` | `tuple[time, time] \| None` | Both-or-neither, `HH:MM`, same rule as the other three interfaces |

**Validation**: identical rules to `UserPreferenceSet` — `calendar_length_days`
must be positive; an incomplete start-window pair is rejected. Unlike the
CLI/MCP/web interfaces, there is no request/caller to return a 4xx-style
error to — a validation failure here is itself a run failure, handled by the
same failure-email path as a pipeline error (contracts/scheduled-job-contract.md).

## EmailDeliveryConfig (new)

Built by `src/scheduled_job/recipe.py` alongside `Recipe`; not part of
`UserPreferenceSet` — this configures *delivery*, not *generation*.

| Field | Source env var | Type | Notes |
|---|---|---|---|
| `recipient_email` | `RECIPIENT_EMAIL` | `str` | Required |
| `smtp_host` | `SMTP_HOST` | `str` | Required |
| `smtp_port` | `SMTP_PORT` | `int` | Required |
| `smtp_username` | `SMTP_USERNAME` | `str \| None` | Optional — some relays allow unauthenticated/IP-allowlisted sending |
| `smtp_password` | `SMTP_PASSWORD` | `str \| None` | Optional (paired with `smtp_username`); a secret, injected via GCP Secret Manager at deploy time, never logged |
| `from_address` | `SMTP_FROM_ADDRESS` | `str` | Required |

## RunOutcome (new, internal — not persisted)

The shape `src/scheduled_job/main.py` hands to `email_delivery.py` after a
run — spec.md's "Scheduled Run Notification" entity, made concrete. Exists
only in memory for the duration of one run; nothing about it is stored.

| Field | Type | Notes |
|---|---|---|
| `status` | `Literal["success", "failure"]` | |
| `events` | `list[CulturalEvent]` | Populated on success (possibly empty — the zero-events case is still `"success"`, per spec.md Acceptance Scenario US1.2) |
| `error_message` | `str \| None` | Populated on `"failure"` — the same plain-language `str(exc)` text the CLI/MCP/web interfaces already surface for `DiscoveryUnavailableError`/`MissingConfigError`, or a generic message for an unanticipated exception (research.md #5) |

`email_delivery.py` maps `RunOutcome` to a subject line and body per
`contracts/scheduled-job-contract.md`'s email content contract — one of
exactly three shapes: events found, zero events matched, or a failure
explanation.
