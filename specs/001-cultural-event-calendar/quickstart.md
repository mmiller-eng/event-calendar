# Quickstart: Cultural Event Calendar Agent

Validates the feature end-to-end per the spec's Independent Test criteria (US1/US2/US3). Assumes the implementation described in `plan.md` / `contracts/cli-contract.md` exists.

## Prerequisites

```bash
pip install -e .            # installs the `calendar` CLI entry point + deps from research.md
export EVENT_CALENDAR_MODEL=anthropic/claude-sonnet-5   # or any litellm-supported provider/model
export ANTHROPIC_API_KEY=...                              # matching key for the chosen provider
export TAVILY_API_KEY=...                                 # optional but needed to exercise the web-search fallback
```

Alternatively, copy `.env.example` to `.env` and fill in the values there — it's
loaded automatically on startup (git-ignored, so secrets never get committed).

## Scenario 1 — Basic personalized calendar (US1)

```bash
calendar generate --location "Portland, OR" --calendar-length-days 14 --output ./out/basic.md
```

**Expected**: exit code 0; `./out/basic.md` exists; contains events dated within `[today, today+14]`, grouped by date; if the run's discovery genuinely finds nothing, the file still exists and states no events matched (FR-009) instead of being empty or missing.

## Scenario 2 — Free-only filter (US2)

```bash
calendar generate --location "Portland, OR" --calendar-length-days 14 --max-cost 0 --output ./out/free.md
```

**Expected**: every event listed shows cost `free`; no event with a nonzero known cost appears.

## Scenario 3 — Cost ceiling with unknown-price handling (US2)

```bash
calendar generate --location "Portland, OR" --calendar-length-days 14 --max-cost 30 --output ./out/under30.md
```

**Expected**: no listed event exceeds $30; any event whose price could not be determined is present but its cost field reads `unknown` (not silently dropped, not silently included as if free).

## Scenario 4 — Type + genre filter (US3)

```bash
calendar generate --location "Portland, OR" --calendar-length-days 14 --event-type music --genre jazz --output ./out/jazz.md
```

**Expected**: every listed event has `event_type = music` and `genre = jazz`.

## Scenario 5 — Multiple types, no genre restriction (US3)

```bash
calendar generate --location "Portland, OR" --calendar-length-days 14 --event-type music --event-type theater --output ./out/multi.md
```

**Expected**: both music and theater events appear; genre filter is not applied to theater events, and music events of any genre are included.

## Scenario 6 — Trusted source list management (FR-002a)

```bash
calendar sources add --name "Portland Arts Council" --url https://example-arts.org/events
calendar sources list
calendar sources remove --url https://example-arts.org/events
calendar sources list
```

**Expected**: first `list` shows the added entry; second `list` shows the explicit empty-list message. None of these commands require running `generate`.

## Regenerate without restart (SC-005)

Run any two of Scenarios 1–5 back to back in the same shell session without reinstalling or restarting anything — both must independently produce a correct, distinct output file. Confirms the CLI process model needs no persistent/interactive state between requests.
