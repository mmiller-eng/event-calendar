# Feature Specification: Web Frontend (React + Vite)

**Feature Branch**: `003-react-vite-frontend`

**Created**: 2026-09-07

**Status**: Draft

**Input**: User description: "Add add react, react router, vite frontend to the project"

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Generate and view a calendar in the browser (Priority: P1)

A user opens the web app, enters their preferences (location, calendar length, cost ceiling, event types, genres, time window), triggers generation, and sees the resulting calendar rendered in the browser — without opening a terminal or the generated Markdown file manually.

**Why this priority**: This is the core value the CLI and MCP server already provide; a frontend that can't do this isn't a usable alternative to either. It is the smallest slice that makes the web app worth opening at all.

**Independent Test**: Can be fully tested by opening the web app, submitting a generation request with a valid location and calendar length, and confirming the rendered calendar appears in the browser and matches what the CLI would produce for the same inputs.

**Acceptance Scenarios**:

1. **Given** the web app is open and at least one trusted source is configured, **When** the user submits valid preferences, **Then** a calendar is generated and displayed in the browser with each event's date, time, venue, and cost readable without leaving the page.
2. **Given** a generation request is in progress, **When** the user is waiting on results, **Then** the app shows a clear in-progress indicator rather than an unresponsive or blank screen.
3. **Given** valid preferences that match zero events, **When** the user submits the request, **Then** the app displays an explicit "no events matched" result rather than an empty or broken view.

---

### User Story 2 - Manage trusted sources in the browser (Priority: P2)

A user views, adds, and removes trusted event sources through web forms, instead of using CLI commands or an MCP-capable AI assistant.

**Why this priority**: Source management is required to get useful results out of User Story 1, but a user can get started with zero or a couple of sources already configured (e.g., from prior CLI/MCP use), so this is valuable but not blocking for a first look at the app.

**Independent Test**: Can be fully tested by opening the source-management view, adding a new source with a name and URL, confirming it appears in the list, then removing it and confirming it disappears — independent of any calendar generation.

**Acceptance Scenarios**:

1. **Given** the source-management view is open, **When** the user submits a new source's name and a valid URL, **Then** the source appears in the displayed list.
2. **Given** the source-management view is open, **When** the user submits a URL that is already in the list, **Then** the app shows the existing entry and does not create a duplicate.
3. **Given** an existing source in the list, **When** the user removes it, **Then** it no longer appears in the list.

---

### User Story 3 - Move between views without losing context (Priority: P3)

A user switches between the "generate a calendar" view and the "manage sources" view (and, once a calendar exists, a view of past results) using in-app navigation, without a full page reload each time.

**Why this priority**: This is a usability refinement on top of Stories 1 and 2 — both already work as single, separately-loadable pages without it. Client-side navigation makes the app feel responsive but isn't required for the core value to exist.

**Independent Test**: Can be fully tested by generating a calendar, navigating to the source-management view, then navigating back, and confirming the previously generated calendar is still visible without re-submitting the request.

**Acceptance Scenarios**:

1. **Given** the user is on the generate view, **When** they select the "manage sources" navigation link, **Then** the manage-sources view appears without a full-page browser reload.
2. **Given** the user has just generated a calendar, **When** they navigate away and then back to the generate view, **Then** the most recently generated calendar is still displayed.

---

### Edge Cases

- What happens when generation is triggered while no trusted sources are configured and web search is unavailable? The app must show the same "no sources available" condition the CLI and MCP server already surface, in plain language.
- What happens when the user submits the add-source form with a malformed URL? The app must show a validation message and must not add the entry.
- What happens when the user navigates directly to a manage-sources or generate URL that doesn't correspond to any known view? The app must show a clear "not found" state rather than a blank page.
- What happens when the user triggers a second generation request while one is already in progress? The app must prevent a second concurrent request from the same session rather than silently starting both.
- What happens on first-ever visit, before any calendar has been generated? The app must show an empty/starting state that guides the user to the generate view, not a blank screen.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: The web app MUST let a user specify the same generation preferences the CLI and MCP server already accept (location, calendar length, cost ceiling, event type(s), genre(s), start-time window) and submit them to trigger calendar generation.
- **FR-002**: The web app MUST display the generated calendar's contents (event date, time, venue, cost) directly in the browser.
- **FR-003**: The web app MUST let a user view the current list of trusted sources (name, URL, date added).
- **FR-004**: The web app MUST let a user add a trusted source by name and URL, and MUST reject a malformed URL with an inline, human-readable message instead of adding it.
- **FR-005**: The web app MUST NOT create a duplicate entry when a user submits a URL that is already on the trusted-source list, and MUST indicate that the existing entry was reused.
- **FR-006**: The web app MUST let a user remove an existing trusted source, and MUST show a clear message if the target URL is not on the list.
- **FR-007**: The web app MUST let a user move between the generate view and the manage-sources view without a full page reload.
- **FR-008**: The system MUST reuse the same filtering, deduplication, and discovery rules already used by the CLI and MCP server, so a given set of preferences produces the same results regardless of which interface made the request.
- **FR-009**: The web app MUST surface the same categories of error already defined for the CLI/MCP interfaces (no sources reachable, invalid source URL, duplicate source, remove-target not found) as plain-language, in-browser messages rather than raw errors or a blank screen.
- **FR-010**: The web app MUST indicate to the user when a generation request is in progress, since results depend on live network/LLM calls that are not instantaneous.
- **FR-011**: The web app MUST NOT require a login or account for a single local user to use it, consistent with the project's existing single-user, no-authentication model.

### Key Entities

- **Trusted Event Source**, **Cultural Event**, **Generated Calendar**, **User Preference Set**: reused exactly as already defined for the CLI and MCP server ([001-cultural-event-calendar/data-model.md](../001-cultural-event-calendar/data-model.md)); this feature introduces no new domain entities, only a browser-based way to view and submit them.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: A user can generate a calendar and read its results entirely within the browser, without opening a terminal or a file browser.
- **SC-002**: Moving between the generate view and the manage-sources view completes in under 1 second, with no full-page reload.
- **SC-003**: A user with no prior CLI experience can successfully add and then remove a trusted source on their first attempt using only the web forms.
- **SC-004**: Every error condition already defined for the CLI and MCP interfaces (no sources reachable, invalid URL, duplicate source, remove-target not found) produces a readable, plain-language message in the browser in 100% of cases — never a blank page or an unhandled error screen.

## Assumptions

- **Requested stack**: The user explicitly requested React, React Router, and Vite as the frontend technology; this spec describes the outcomes that stack must deliver, not the specific implementation.
- **Scope of parity**: This spec assumes the web app should cover the same two capabilities already exposed by the CLI and MCP server — generating a calendar and managing trusted sources — as a browser-based third interface, rather than a narrower read-only dashboard. If only a read-only view was intended, FR-004 through FR-007 would not apply.
- **Single user, no auth**: Matches the project's existing single-user, local-only model (Principle III) — this spec assumes no login, accounts, or multi-user access are introduced.
- **A backend is required**: A browser cannot call the existing Python pipeline directly; some backend/API layer to bridge the web app to the existing `services`/`llm`/`config` code is assumed to be necessary, but its design is an implementation detail out of scope for this spec.
- **Governance note**: The project constitution's Principle IV currently states the CLI and the MCP server are "the only externally-facing interfaces" and that "introducing any further externally-facing interface beyond these two requires a prior amendment to this principle." A browser-based frontend (and whatever backend it needs) is a third externally-facing interface, and Principle IV's own rationale text states "without a UI, these two interfaces are the product's entire external surface" — directly contradicted by this feature. This does not block writing this spec, but a constitution amendment (e.g., via `/speckit-constitution`) is a prerequisite before `/speckit-plan` can pass its Constitution Check gate for this feature.
