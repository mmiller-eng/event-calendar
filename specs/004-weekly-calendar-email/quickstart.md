# Quickstart: Weekly Scheduled Calendar Email

Validation guide for this feature once implemented. Full environment
variable / behavior detail lives in
[contracts/scheduled-job-contract.md](./contracts/scheduled-job-contract.md);
field shapes live in [data-model.md](./data-model.md) — neither is
duplicated here.

## Prerequisites

- Same LLM/discovery environment as the CLI/MCP/web interfaces:
  `EVENT_CALENDAR_MODEL`, a provider API key, optionally `TAVILY_API_KEY`.
- A trusted-source list at the path `EVENT_CALENDAR_TRUSTED_SOURCES` points
  to (in the built image, this is the one baked in at build time).
- A reachable SMTP relay for testing — a local debugging SMTP server (e.g.
  `python -m aiosmtpd -n -l localhost:1025`, which just prints received mail
  to the console) is enough; no real mailbox is required to validate the
  logic.
- Docker, if validating the built container rather than running the module
  directly.

## Run it locally (without Docker)

```bash
export WEEKLY_RECIPE_LOCATION="Seattle, WA"
export WEEKLY_RECIPE_CALENDAR_LENGTH_DAYS=14
export WEEKLY_RECIPIENT_EMAIL="you@example.com"
export SMTP_HOST=localhost
export SMTP_PORT=1025
export SMTP_FROM_ADDRESS="calendar@example.com"

.venv/bin/calendar-weekly-email
```

## Run the built container

```bash
docker build -t event-calendar-weekly .
docker run --rm \
  -e WEEKLY_RECIPE_LOCATION="Seattle, WA" \
  -e WEEKLY_RECIPE_CALENDAR_LENGTH_DAYS=14 \
  -e WEEKLY_RECIPIENT_EMAIL="you@example.com" \
  -e SMTP_HOST=host.docker.internal -e SMTP_PORT=1025 \
  -e SMTP_FROM_ADDRESS="calendar@example.com" \
  -e EVENT_CALENDAR_MODEL="anthropic/claude-sonnet-5" \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  event-calendar-weekly
```

## Validate User Story 1 — automated weekly email (P1)

1. With at least one trusted source baked into the image (or
   `TAVILY_API_KEY` set), run the entrypoint as above.
2. **Expect**: the debugging SMTP server prints one received email, subject
   `Cultural Event Calendar: Seattle, WA (<N> events)`, body listing each
   event's date/time/venue/cost.
3. Re-run with a recipe unlikely to match anything.
   **Expect**: subject `... (no events found)`, body explicitly states no
   events matched — not an empty body.
4. Change `WEEKLY_RECIPIENT_EMAIL` and re-run.
   **Expect**: the email is addressed to the new recipient, not the
   previous one.

## Validate User Story 2 — failure notification (P2)

1. Point `EVENT_CALENDAR_TRUSTED_SOURCES` at an empty/nonexistent file and
   unset `TAVILY_API_KEY`, then run the entrypoint.
   **Expect**: one email still arrives, subject ending `— run failed`, body
   containing "No trusted sources configured and web search is
   unavailable." — the same message the CLI/MCP/web interfaces already
   produce for this condition.
2. Unset a required variable (e.g. `WEEKLY_RECIPE_LOCATION`) and run.
   **Expect**: one failure email still arrives, explaining what's missing —
   not a silent crash with no email at all.

## Validate User Story 3 — config-only recipe changes (P3)

1. Change `WEEKLY_RECIPE_LOCATION` (or `WEEKLY_RECIPE_CALENDAR_LENGTH_DAYS`)
   and re-run without touching any code.
   **Expect**: the next run's email reflects the new location/length —
   confirms the recipe is genuinely just configuration, not hardcoded.

## Automated equivalent

Once implemented, `tests/unit/test_email_delivery.py` and
`tests/integration/test_scheduled_job.py` are the automated version of the
scenarios above (mocked SMTP, mocked discovery) and should be run instead of
manual validation for routine checks:

```bash
.venv/bin/pytest tests/unit/test_email_delivery.py tests/integration/test_scheduled_job.py -v
```

## Deployment validation (out of scope for automated tests)

Once deployed: confirm the Cloud Run Job exists with a weekly Cloud
Scheduler trigger, confirm the LLM/SMTP secrets are wired through GCP Secret
Manager (never a plaintext env var in the deployment config), and manually
trigger one execution (`gcloud run jobs execute ...`) to confirm the
end-to-end path before relying on the schedule.
