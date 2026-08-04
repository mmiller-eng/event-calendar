# Phase 0 Research: Cultural Event Calendar Agent

All Technical Context items were resolvable from the spec's explicit constraints (single-user, plain-file storage, provider-agnostic model access) plus standard practice for small Python CLI agents. No items remain marked `NEEDS CLARIFICATION`.

## 1. Provider-agnostic LLM access

- **Decision**: Use `litellm` as a thin abstraction over the LLM call, with the concrete provider/model selected via config (env var `EVENT_CALENDAR_MODEL`, e.g. `anthropic/claude-sonnet-5` or `openai/gpt-5`) and the corresponding provider API key read from the environment.
- **Rationale**: The user explicitly wants to invoke models other than Claude. `litellm` presents one call signature across Anthropic, OpenAI, and other providers, so `src/llm/provider.py` stays a single small module instead of one adapter per vendor. It is widely used for exactly this "swap the model via config" use case in small agent projects.
- **Alternatives considered**:
  - *Hand-rolled per-provider adapters* — full control, but doubles maintenance for every provider added; rejected as unnecessary for a single-user tool.
  - *LangChain* — heavier dependency surface and more opinionated orchestration than this feature needs (no chains/agents graph required, just discrete LLM calls for extraction/normalization).
  - *Lock to Anthropic SDK only* — simplest, but directly contradicts the stated requirement to support other models.

## 2. Live web search fallback

- **Decision**: Use the Tavily search API as the live web-search fallback (FR-002), reached through a small `web_search_client.py` wrapper so the provider could be swapped later.
- **Rationale**: Tavily is purpose-built for agent/LLM workflows (returns clean, summarized results rather than raw SERPs), has a usable free tier for a single-user personal tool, and needs only an API key (no scraping/ToS gray area like scraping Google directly).
- **Alternatives considered**:
  - *SerpAPI / Google Custom Search* — viable, but returns raw search-engine results requiring more post-processing to get clean event data.
  - *Bing Web Search API* — being deprecated/migrated by Microsoft; avoided for a new project.
  - *Direct scraping of aggregator sites (e.g. Eventbrite, Ticketmaster)* — brittle, ToS risk, and duplicates what the trusted-source-list mechanism (FR-002a) already covers for known sources.

## 3. Trusted source page fetching & extraction

- **Decision**: Fetch trusted source pages with `httpx`, strip to readable text with `beautifulsoup4`, then pass the cleaned text to the LLM provider to extract structured `CulturalEvent` candidates (name, date, time, venue, cost, type, genre).
- **Rationale**: Trusted source pages are heterogeneous (no shared schema), so a general HTML→text→LLM-extraction pipeline is more robust than per-site scrapers, and keeps the trusted-source list (FR-002a) usable for arbitrary venue/org pages without custom code per source.
- **Alternatives considered**:
  - *Per-source structured scrapers (CSS selectors per venue)* — more accurate per site but breaks on markup changes and requires a scraper per trusted source, unworkable for a user-maintained, open-ended list.
  - *RSS/iCal feed parsing only* — many small venues don't publish feeds; would silently drop coverage the spec requires (FR-002).

## 4. Storage format

- **Decision**: Trusted source list as a single YAML file (`trusted_sources.yaml`, list of `{name, url}`); generated calendars as timestamped Markdown files in an output directory (e.g. `calendars/2026-08-02.md`).
- **Rationale**: Matches the "plain files" storage decision; YAML is easy for the user to hand-edit if they want to bypass the `sources add/remove` CLI commands (FR-002a), and Markdown output is the spec's required deliverable format (FR-004) with no further transformation needed.
- **Alternatives considered**:
  - *SQLite* — declined per explicit storage decision; unnecessary durability/query power for a list of tens of URLs.
  - *JSON for the source list* — equally valid; YAML chosen for human-editability (comments, less punctuation) since users are expected to hand-maintain this file.

## 5. CLI framework

- **Decision**: `click` for command/argument parsing (`calendar generate ...`, `calendar sources list|add|remove`).
- **Rationale**: Standard, well-documented, minimal boilerplate for a small multi-command CLI; built-in support for options, prompts, and exit-code conventions used by the contract tests.
- **Alternatives considered**: `argparse` (stdlib, no dependency, but noticeably more boilerplate for subcommands); `typer` (nice DX but adds a dependency on top of click that it already wraps).

## 6. Testing approach

- **Decision**: `pytest` with `respx` to mock `httpx` calls (trusted-source fetches, Tavily search) and a fake/stub LLM provider implementation for deterministic contract/integration tests; real provider calls are exercised only in manual/quickstart validation, not automated tests.
- **Rationale**: Keeps the test suite deterministic and free of API costs/network flakiness while still exercising the full discovery → filter → dedup → render pipeline.
- **Alternatives considered**: Recording/replaying real HTTP cassettes (`vcrpy`) — viable future addition, deferred as unnecessary complexity for v1.
