# `mcp dev` vs bare `npx @modelcontextprotocol/inspector@latest`

Running `mcp dev src/mcp_server/server.py` and running `npx @modelcontextprotocol/inspector@latest` on its own can show different results for the same tools. There are two real, confirmed differences (from reading `mcp`'s CLI source at `.venv/lib/python3.12/site-packages/mcp/cli/cli.py:220-282`):

## 1. How the server gets launched and configured

`mcp dev src/mcp_server/server.py` doesn't just open the Inspector — it builds:

```
uv run --with mcp[cli]==<pinned> mcp run <your file>
```

and launches that as the argument to `npx @modelcontextprotocol/inspector`, explicitly forwarding your *entire current shell environment* (`env=dict(os.environ.items())`, line 280). Run from the project directory, `uv run` also picks up this repo's own `pyproject.toml`/`uv.lock`, so it's effectively your `.venv`'s dependencies plus your live shell env vars (`ANTHROPIC_API_KEY`, `EVENT_CALENDAR_TRUSTED_SOURCES`, etc. — whatever's actually exported in your terminal).

Bare `npx @modelcontextprotocol/inspector@latest`, by contrast, starts with **no server attached at all** — you have to manually type a command/args into the UI (e.g. `.venv/bin/python` / `-m src.mcp_server.server`) and manually add any env vars in its separate "Environment Variables" panel, which does **not** auto-inherit your shell. If that panel is empty or the command/interpreter you typed differs from what `mcp dev` uses, you're talking to a differently-configured server — e.g. missing `EVENT_CALENDAR_TRUSTED_SOURCES` means `list_sources` reads a different (or default) `trusted_sources.yaml` than the one `mcp dev` resolves.

## 2. Possibly different Inspector app versions

`mcp dev` runs `npx @modelcontextprotocol/inspector` unpinned (whatever npx already has cached/resolved locally), while explicitly running `@latest` forces npm to resolve the newest published version. Those can be genuinely different versions of the Inspector web app — worth checking the version shown in each UI's footer, especially given past npx/nvm cache issues (see npm/cli#4828).

## Fastest way to isolate which one it is

In the bare `@latest` Inspector, set Command/Args to match exactly what `.mcp.json` uses:

- Command: `.venv/bin/python`
- Args: `-m src.mcp_server.server`

and paste in the same env vars your shell has set. If results then match `mcp dev`, the discrepancy was configuration, not version.
