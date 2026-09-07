# Phase 0 Research: MCP Server Access

No `[NEEDS CLARIFICATION]` markers were left in the spec's Technical Context —
this feature was already built, so research below documents the decisions
actually made (verified against the shipped code and, where noted, against
direct reproduction during development) rather than proposing new ones.

## 1. Transport & framework: MCP Python SDK, stdio, `MCPServer`

**Decision**: Use the official MCP Python SDK (`mcp[cli]>=1.8.0`), exposing
tools via `mcp.server.mcpserver.MCPServer` and `@mcp.tool(...)` decorators,
with parameters declared as `pydantic.Field(...)` defaults on the function
signature. Run over stdio transport (`mcp.run(transport="stdio")`).

**Rationale**: The official SDK is the standard, supported way to expose
Python functions as MCP tools; parameter descriptions/schemas live directly
on the function signature, so the tool contract can't drift from its
implementation. stdio transport requires no network exposure or auth setup,
matching Principle III (local-only, single-user simplicity) — any MCP
client that can spawn a local subprocess can use it.

**Alternatives considered**: A hand-rolled JSON-RPC server (rejected —
reimplements a protocol the SDK already provides correctly, ongoing
maintenance cost for no benefit). HTTP/SSE transport (rejected — introduces
a network-facing surface and authentication concerns not needed for a
local single-user tool, in tension with Principle III).

## 2. Pipeline reuse: in-process calls, not CLI subprocess wrapping

**Decision**: Each tool function calls the existing pipeline
(`src/services/discovery`, `filtering`, `dedup`, `markdown`,
`src/llm/provider.py`, `src/config.py`) directly, in-process — not by
shelling out to the `calendar` CLI and parsing its text output.

**Rationale**: Produces native structured errors and typed return values
instead of a fragile text parse of human-oriented CLI output; keeps exactly
one implementation of business logic behind two thin interfaces, which is
what makes FR-005 ("results are consistent regardless of which interface
made the request") true without extra reconciliation work.

**Alternatives considered**: Subprocess-wrapping the CLI (rejected — CLI
stdout is a human-readable contract, not a structured data contract;
parsing it back into structured tool results would be fragile and would
lose the CLI's own exit-code semantics).

## 3. Structured output shapes: real models, not bare `dict`

**Decision**: `add_source`/`remove_source` return a `SourceResult` pydantic
model (`name`, `url`, `added_at`); `list_sources` returns `list[dict]` and
relies on the SDK's automatic `{"result": [...]}` wrapping.

**Rationale**: Verified directly against the SDK's
`func_metadata._create_output_model`: a `BaseModel` subclass is used
directly for `output_schema`/`structured_content`; a parameterized generic
like `list[dict]` is auto-wrapped in a synthesized `{"result": ...}` model;
but a *bare, unparameterized* `dict` return type produces no output schema
at all — `structured_content` comes back `None`, forcing every caller to
fall back to parsing `result.content[0].text`. Using `SourceResult` gives
callers typed structured content for free.

**Alternatives considered**: Leaving `add_source`/`remove_source` typed as
plain `dict` (rejected — reproduced directly: `structured_content` is
`None`, so clients must parse text instead of reading structured fields).
Returning `list[dict]` even for single-entity results (rejected — wrong
shape, forces an unnecessary `["result"]` unwrap for what is conceptually
one object).

## 4. Error surfacing: `ToolError` for every anticipated failure

**Decision**: Every anticipated validation/business failure (invalid
source URL, non-positive `calendar_length_days`, malformed `max_cost`,
an incomplete `start_after`/`start_before` pair, no discovery sources
available, removing a URL not on the trusted list) is raised as
`mcp.server.mcpserver.exceptions.ToolError`, not a bare `ValueError` or
other built-in exception.

**Rationale**: Verified directly by reading `Tool.run()`
(`mcp/server/mcpserver/tools/base.py`): the SDK forwards an exception's
message to the calling client only when it is a
`ToolError`/`ResourceError`/`MCPError`; anything else is treated as an
unexpected "crash" and replaced with a generic
`UnexpectedToolError(f"Error executing tool {name}")` with no detail —
confirmed by reproduction (a plain `ValueError` for an invalid URL produced
exactly that generic message client-side, with the real "Invalid url: ..."
text visible only in the server-side traceback). Using `ToolError`
consistently is what makes FR-006/FR-007/FR-008 (specific, actionable
error messages) actually true for an MCP client, not just true internally.

**Alternatives considered**: Letting exceptions propagate unchanged
(rejected — reproduced above, fails FR-006/007/008 outright). Catching
failures and returning an error description as a normal successful result
(rejected — loses the `is_error` signal MCP clients rely on to distinguish
success from failure).

## 5. LLM-provider failures: `LLMRequestError`, treated as a per-source failure

**Decision**: `LLMProvider.extract_events` (`src/llm/provider.py`) catches
`openai.APIError` (the shared base of `litellm`'s auth/rate-limit/bad-request/
connection/timeout exceptions) and re-raises it as a new `LLMRequestError`.
`discover_events` (`src/services/discovery/__init__.py`) now catches
`(httpx.HTTPError, LLMRequestError)` in its per-trusted-source loop, where
it previously caught only `httpx.HTTPError`.

**Rationale**: Verified directly — an invalid/unauthorized API key
produces `litellm.exceptions.AuthenticationError` (an `openai.APIError`
subclass), which is not an `httpx.HTTPError` and was previously uncaught,
crashing the whole request as an unhandled exception (compounding with
finding #4 above into an opaque `UnexpectedToolError`). Treating an
LLM-provider failure the same as an unreachable source lets the existing
"no sources reachable" aggregation (FR-007) fire correctly — the source is
simply unusable, same as if its page couldn't be fetched.

**Alternatives considered**: Catching provider exceptions ad hoc at each
call site (trusted-source path and web-search path separately) (rejected —
duplicated handling that a future third discovery path could easily forget;
a single boundary in `LLMProvider` cannot be bypassed).

## 6. MCP subprocess environment: captured at connect time, not construction time

**Decision**: `MCPClient.connect()` (`src/mcp_server/client.py`) reads
`os.environ` at connect time (`dict(os.environ)` as the default when no
explicit `env` is passed to `__init__`), rather than the test fixture
capturing a static `env=os.environ.copy()` once when the client object is
constructed.

**Rationale**: The MCP SDK's default `StdioServerParameters` environment
only inherits a small safe allowlist of variables unless `env=` is passed
explicitly — without *some* explicit env forwarding, a test's
`monkeypatch.setenv(...)` never reaches the server subprocess at all. This
was caught directly during development: a manual diagnostic script's env
override didn't reach the subprocess, and the resulting `add_source` call
wrote into the real, git-tracked `trusted_sources.yaml` instead of a test
fixture path (reverted via `git checkout --`). Reading the environment at
connect time (rather than freezing it at construction time) additionally
lets a test override an env var inside its own body — right up until
`async with client:` — and have that reach the subprocess, which a
constructor-time snapshot cannot do.

**Alternatives considered**: A static `env=os.environ.copy()` captured at
`MCPClient.__init__` time (rejected — verified directly: an override set
after construction, e.g. inside the test function body, never reaches the
subprocess because the dict was already frozen before the test ran).
