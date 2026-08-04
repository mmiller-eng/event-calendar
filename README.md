# event-calendar

A standalone, model-agnostic CLI agent that turns your cultural-event preferences
(location, cost ceiling, event type(s), music genre(s), calendar length, preferred
start-time window) into a single Markdown calendar of matching events. It checks a
user-maintained trusted local source list first, then falls back to live web search.

## Install

```bash
pip install -e ".[dev]"
```

## Configuration

Environment variables can be set directly, or placed in a `.env` file in the
project directory (copy `.env.example` to `.env` and fill it in). `.env` is
git-ignored and is loaded automatically on startup; variables already set in
your shell take precedence over `.env`.

| Variable | Required | Purpose |
|---|---|---|
| `EVENT_CALENDAR_MODEL` | yes, unless `--model` is passed | `provider/model` string passed to `litellm` (e.g. `anthropic/claude-sonnet-5`) |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / etc. | yes | API key matching the selected provider, per `litellm` convention |
| `TAVILY_API_KEY` | no | Enables the live web-search fallback; without it, discovery relies on the trusted-source list only |
| `EVENT_CALENDAR_TRUSTED_SOURCES` | no | Path to the trusted-source list file (default: `trusted_sources.yaml`) |
| `EVENT_CALENDAR_OUTPUT_DIR` | no | Default output directory for generated calendars (default: `calendars/`) |

## Usage

Generate a calendar:

```bash
calendar generate --location "Portland, OR" --calendar-length-days 14
```

Common flags: `--max-cost`, `--event-type` (repeatable), `--genre` (repeatable),
`--start-after`/`--start-before` (HH:MM), `--output`, `--model`.

Manage the trusted source list:

```bash
calendar sources add --name "Portland Arts Council" --url https://example-arts.org/events
calendar sources list
calendar sources remove --url https://example-arts.org/events
```

See `specs/001-cultural-event-calendar/quickstart.md` for full end-to-end scenarios.

## Tests

```bash
pytest
```
