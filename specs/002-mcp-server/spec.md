# Feature Specification: MCP Server Access

**Feature Branch**: `002-mcp-server`

**Created**: 2026-09-06

**Status**: Draft

**Input**: User description: "add a spec for the existing MCP server work so documentation matches implementation"

**Note**: This spec documents functionality that has already been implemented
(`src/mcp_server/`), written retroactively so the project's spec-kit artifacts
describe what exists rather than something new to be built. Requirements below
describe current, verifiable behavior.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate a calendar through an AI assistant (Priority: P1)

A user working inside an AI assistant or agent tool describes their event
preferences (location, dates, cost ceiling, event types, genres) in
conversation. The assistant generates a complete cultural-event calendar on
the user's behalf, without the user needing to open a terminal or run any
command.

**Why this priority**: This is the core value of the whole product — a
calendar the user can trust — made reachable from a conversational AI tool
instead of only a terminal. Without this, the feature has no purpose.

**Independent Test**: Can be fully tested by connecting any MCP-compatible
client, requesting a calendar for a given location and preference set, and
confirming a Markdown calendar is both returned to the client and written to
disk — matching what `calendar generate` with the same inputs would produce.

**Acceptance Scenarios**:

1. **Given** at least one usable event source is configured, **When** the
   assistant requests a calendar for a location with a set of preferences,
   **Then** a Markdown calendar reflecting those preferences is returned and
   saved to disk.
2. **Given** a generated calendar has zero matching events, **When** the
   request completes, **Then** the response clearly states no events matched
   rather than returning an empty or misleading result.

---

### User Story 2 - Manage trusted sources through an AI assistant (Priority: P2)

A user asks their AI assistant to view, add, or remove entries in their
trusted local event-source list, conversationally, instead of running
`sources list`/`add`/`remove` commands themselves.

**Why this priority**: Source management is a prerequisite for useful
calendar generation (Story 1) but is a secondary, lower-frequency action —
users typically curate their source list occasionally, not on every request.

**Independent Test**: Can be fully tested by adding a source through the
assistant, listing sources and confirming it appears, then removing it and
confirming the list reflects the removal — all without touching the CLI.

**Acceptance Scenarios**:

1. **Given** a valid name and URL, **When** the assistant adds a trusted
   source, **Then** it appears in a subsequent listing with the name, URL,
   and the date it was added.
2. **Given** a source URL that is already on the trusted list, **When** the
   assistant attempts to add it again, **Then** no duplicate entry is
   created.
3. **Given** a source URL currently on the trusted list, **When** the
   assistant removes it by URL, **Then** it no longer appears in a
   subsequent listing.

---

### User Story 3 - Receive actionable error feedback (Priority: P3)

When a request can't be completed — invalid input, no usable event sources,
an unreachable source, or a removal target that doesn't exist — the
assistant receives a specific, human-readable explanation it can relay to
the user, rather than a generic failure with no actionable detail.

**Why this priority**: Improves trust and usability once the core paths
(Stories 1–2) work, but the feature is still usable in the happy path
without it — this refines the failure experience rather than enabling new
capability.

**Independent Test**: Can be fully tested by deliberately triggering each
failure condition (e.g., a non-positive calendar length, a malformed source
URL, removing a URL that was never added) and confirming the returned error
names the specific problem.

**Acceptance Scenarios**:

1. **Given** an invalid input value (e.g., a negative calendar length, a
   malformed cost, a source URL missing a scheme), **When** the request is
   made, **Then** the response identifies which value was invalid and why.
2. **Given** no trusted sources are configured and no fallback search is
   available, **When** a calendar is requested, **Then** the response
   clearly states that no event sources are available, distinct from "zero
   events found."
3. **Given** a URL that is not on the trusted list, **When** its removal is
   requested, **Then** the response states that no matching source was
   found.

### Edge Cases

- What happens when a calendar request's preferences match zero events?
  The calendar is still generated and returned, stating that nothing
  matched (not treated as an error).
- What happens when every configured trusted source is unreachable and no
  fallback search is configured? The request fails with a specific
  "no sources available" explanation; no partial or fabricated calendar is
  produced.
- What happens when a source is added with a malformed URL (no scheme,
  not a URL at all)? The add is rejected with a validation explanation; no
  entry is created.
- What happens when the same source URL is added twice? The second request
  is a no-op — the existing entry is returned, not duplicated.
- What happens when a removal is requested for a URL that was never added?
  The request fails with a "not found" explanation rather than silently
  succeeding.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow an external AI assistant/agent tool to
  request generation of a cultural-event calendar using the same
  preferences supported by the existing calendar-generation flow (location,
  calendar length, cost ceiling, event types, genres, start-time window,
  output location, model override).
- **FR-002**: The system MUST allow an external AI assistant/agent tool to
  list the currently configured trusted event sources.
- **FR-003**: The system MUST allow an external AI assistant/agent tool to
  add a trusted event source by name and URL.
- **FR-004**: The system MUST allow an external AI assistant/agent tool to
  remove a trusted event source by URL.
- **FR-005**: The system MUST reuse the same preference, filtering,
  deduplication, and discovery rules as the existing calendar-generation
  flow, so results are consistent regardless of which interface (terminal
  or AI assistant) made the request.
- **FR-006**: When a request contains invalid input, the system MUST return
  an error that identifies the specific invalid value and why it was
  rejected.
- **FR-007**: When calendar generation cannot proceed because no event
  source is usable (none configured, all unreachable, and no fallback
  search available), the system MUST return an error distinct from "zero
  events found."
- **FR-008**: Removing a trusted source that is not on the list MUST return
  a "not found" error rather than silently succeeding.
- **FR-009**: Adding a trusted source whose URL already exists on the list
  MUST NOT create a duplicate entry.
- **FR-010**: The set of actions available to a connecting AI assistant/agent
  tool MUST be discoverable by that tool at connection time, without the
  tool needing prior hard-coded knowledge of what it can request.

### Key Entities

- **Trusted Event Source**: A user-curated entry the discovery process
  checks first; has a name, a URL, and the date it was added. Same entity
  already defined for the calendar-generation feature — this feature adds
  no new fields, only a second way to manage it.
- **Generated Calendar**: The Markdown output of a calendar-generation
  request. Same entity already defined for the calendar-generation feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can obtain a complete, saved calendar through an AI
  assistant without running any terminal command.
- **SC-002**: A user can add, list, and remove a trusted source through an
  AI assistant, with each change visible in the very next listing.
- **SC-003**: When a request fails, the assistant has enough detail in the
  error to explain the specific cause to the user in plain language,
  without the user needing to inspect logs or files.
- **SC-004**: Results produced through an AI assistant match results
  produced by the equivalent terminal command given the same inputs, with
  no observable difference in filtering or content.

## Assumptions

- The connecting AI assistant/agent tool is trusted to run with the same
  local file and network access already granted to the existing terminal
  tool (single-user, local-only — no new authentication or multi-tenancy is
  introduced by this feature).
- This feature reuses the existing trusted-source list and configuration;
  it does not introduce a separate or parallel configuration surface.
- Multi-user or concurrent access remains out of scope, consistent with the
  rest of the application.
- **Governance note**: the project constitution's Principle IV currently
  states "The CLI is the only externally-facing interface," which this
  already-implemented feature contradicts by adding a second one. This spec
  does not resolve that conflict — it documents behavior that already
  exists. Reconciling Principle IV (e.g., via `/speckit-constitution`) is a
  prerequisite for `/speckit-plan` on this feature, since the Constitution
  Check gate will otherwise report a violation.
