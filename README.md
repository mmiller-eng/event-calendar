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

## MCP Server

The same pipeline is also exposed as an [MCP](https://modelcontextprotocol.io) server
over stdio, so any MCP client (Claude Code, Claude Desktop, the MCP Inspector) can call
it directly rather than shelling out to the CLI.

Run it directly:

```bash
calendar-mcp
# equivalent to: python -m src.mcp_server.server
```

Or register it for Claude Code via `.mcp.json` (already present in this repo):

```json
{
  "mcpServers": {
    "event-calendar": {
      "command": "/path/to/event-calendar/.venv/bin/python",
      "args": ["-m", "src.mcp_server.server"],
      "cwd": "/path/to/event-calendar"
    }
  }
}
```

Inspect it interactively with the [MCP Inspector](https://github.com/modelcontextprotocol/inspector):

```bash
mcp dev src/mcp_server/server.py
```

### Tools

| Tool | Description |
|---|---|
| `generate_calendar` | Generate a Markdown calendar for a location, applying preference filters; writes it to disk and returns the Markdown content. Same parameters as `calendar generate` (`location`, `calendar_length_days`, `max_cost`, `event_types`, `genres`, `start_after`/`start_before`, `output_path`, `model`). |
| `list_sources` | List the configured trusted event sources. |
| `add_source` | Add a trusted event source by `name` and `url`. |
| `remove_source` | Remove a trusted event source by `url`. |

Errors (invalid input, no sources available, LLM/provider failures) surface to the
client as MCP tool errors with a descriptive message, rather than raw exceptions.

## Tests

```bash
pytest
```
