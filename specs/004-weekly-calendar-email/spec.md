# Feature Specification: Weekly Scheduled Calendar Email

**Feature Branch**: `004-weekly-calendar-email`

**Created**: 2026-09-14

**Status**: Draft

**Input**: User description: "I would like to run the calendar generate command on a weekly basis (cron job) using an existing set of trusted resources and specific set of flags for example a calendar length of 14 day, location of Seattle WA. The action would run in a docker container deployed to GCP Cloud Run. The generated calendar would be sent to an configurable email address"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Receive a weekly calendar by email automatically (Priority: P1)

An operator configures a location, calendar length, and recipient email address once. From then on, every week, without anyone manually running anything, a freshly generated cultural event calendar for that location arrives by email.

**Why this priority**: This is the entire value of the feature over the existing CLI, MCP, and web interfaces — all three require a person to manually trigger each run. Automated, unattended delivery is what makes this a distinct feature rather than "the CLI, but scheduled."

**Independent Test**: Configure the recipe (location, calendar length, recipient) once, trigger a single scheduled run, and confirm an email arrives at the configured address containing a calendar matching what `calendar generate` would produce for the same preferences and source data.

**Acceptance Scenarios**:

1. **Given** a configured location, calendar length, and recipient email, **When** the weekly schedule fires, **Then** an email is sent to the configured address containing the generated calendar's events (date, time, venue, cost).
2. **Given** the scheduled run produces zero matching events, **When** the email is sent, **Then** it clearly states no events were found rather than arriving empty, malformed, or not arriving at all.
3. **Given** the recipient email address is changed by the operator, **When** the next scheduled run fires, **Then** the email goes to the new address, not the old one.

---

### User Story 2 - Get notified when a scheduled run fails (Priority: P2)

An operator is told, by email, when a scheduled run couldn't produce a calendar — instead of just noticing an empty inbox weeks later and not knowing whether the job is broken or there were genuinely no events.

**Why this priority**: Reliability and trust. A silent failure is worse for an unattended scheduled job than for a manual CLI run, because there's no one watching in real time to notice the run didn't work.

**Independent Test**: Force a failure condition (e.g., no trusted sources reachable and no fallback available), trigger a scheduled run, and confirm a notification email is still sent explaining the failure in plain language.

**Acceptance Scenarios**:

1. **Given** no trusted sources are reachable and web search is unavailable, **When** the scheduled run fires, **Then** an email is still sent to the configured address explaining that the run failed and why.
2. **Given** the run fails for a reason unrelated to source availability (e.g., misconfiguration), **When** the scheduled run fires, **Then** a failure notification is sent rather than the job failing with no visible output at all.

---

### User Story 3 - Update the weekly recipe without a code change (Priority: P3)

An operator changes the configured location, calendar length, or recipient email through deployment configuration, not by editing and redeploying application code.

**Why this priority**: Operational convenience. Once automated delivery (US1) and failure visibility (US2) work, being able to adjust the recipe without a code change is valuable but not blocking initial value.

**Independent Test**: Change the configured recipient address or location via the deployment's configuration, redeploy/restart the scheduled job, and confirm the next run uses the new values.

**Acceptance Scenarios**:

1. **Given** the operator changes the configured location via deployment configuration, **When** the job is redeployed, **Then** the next scheduled run generates a calendar for the new location.
2. **Given** the operator changes the configured recipient email, **When** the job is redeployed, **Then** the next scheduled run's email goes to the new recipient.

---

### Edge Cases

- What happens when a scheduled run takes unusually long (e.g., slow LLM or network responses) — does it still complete, or can it be cut off mid-run?
- What happens if two scheduled runs somehow overlap (e.g., last week's run is still finishing when the next one fires)?
- What happens if the configured recipient email address is invalid or malformed?
- What happens if a trusted source packaged with the deployment goes stale (page no longer exists) — does the run still complete using the remaining reachable sources, the same way the CLI/MCP/web interfaces already tolerate partial source failures?
- What happens on the very first scheduled run, before the operator has had a chance to confirm the configuration is correct?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST generate a calendar automatically on a recurring weekly schedule, without a person manually triggering each run.
- **FR-002**: The system MUST use a preconfigured set of generation preferences (at minimum location and calendar length, matching the same preferences the CLI/MCP server/web frontend already accept) for every scheduled run.
- **FR-003**: The system MUST reuse the same trusted-source list and the same discovery, filtering, and deduplication rules already used by the other interfaces, so a scheduled run's results are consistent with what a manual run would produce for the same preferences and source data.
- **FR-004**: The system MUST deliver the generated calendar's contents by email to a configurable recipient address after each successful run.
- **FR-005**: The system MUST clearly state in the email when zero events matched, rather than sending an empty or misleading email.
- **FR-006**: The system MUST send a notification email explaining the failure when a scheduled run cannot complete (e.g., no sources reachable), rather than failing with no visible output.
- **FR-007**: The recipient email address MUST be changeable through configuration, without modifying the generation logic itself.
- **FR-008**: The system MUST run as a reproducible, self-contained deployable unit capable of running unattended on a schedule, rather than depending on a person's own machine being on and available.
- **FR-009**: The system MUST NOT expose any interactive, user-operated entry point of its own beyond the existing CLI capability it invokes — it automates and schedules that existing capability rather than introducing a new interface for a person to operate directly.

### Key Entities

- **Weekly Generation Recipe** (new): the preconfigured preferences for a scheduled run — location, calendar length, and any of the same optional filters (cost ceiling, event types, genres, start-time window) already defined by the reused User Preference Set ([001-cultural-event-calendar/data-model.md](../001-cultural-event-calendar/data-model.md)). Not a new set of fields, just a preconfigured instance of the existing ones.
- **Trusted Event Source**, **Cultural Event**, **Generated Calendar**: reused exactly as already defined in 001 — this feature introduces no changes to how events are discovered, filtered, or rendered.
- **Scheduled Run Notification** (new, conceptual): the outcome of one scheduled run as delivered by email — either the generated calendar's content or a plain-language failure explanation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator who configures location, calendar length, and recipient email once receives a new calendar by email every week without taking any further action.
- **SC-002**: 100% of scheduled runs result in an email arriving at the configured address — either the generated calendar or a failure explanation — never silence.
- **SC-003**: A scheduled run's results match what running the CLI manually with the same preferences against the same source data would produce.
- **SC-004**: Changing the recipient email or the location requires only a configuration change, not a code change to the generation logic.

## Assumptions

- **Deployment target taken as given**: the user specified a Docker container deployed to GCP Cloud Run, triggered weekly (cron-style). This spec describes the outcome (automated weekly email delivery) the deployment must achieve, not a prescription of Cloud Run/Docker mechanics beyond what was explicitly requested — the specific deployment/scheduling mechanics belong in a future implementation plan, not here.
- **Trusted-source provisioning**: the trusted-source list used by scheduled runs is packaged with the deployment (fixed at deploy time), consistent with a reproducible, unattended scheduled job (FR-008). Updating the list means updating the deployment, not editing a live file at runtime. A live-mutable, cloud-stored list is a possible future enhancement, not assumed here.
- **Preference recipe scope**: the "14 days, Seattle WA" example in the request is treated as illustrative of one configurable recipe (location and calendar length, plus any of the optional filters already supported by the other interfaces), not a literal hardcoded pair — reusing 001's existing preference fields rather than defining new ones.
- **Email content format**: the calendar's contents are delivered readably within the email itself; whether that's the rendered Markdown, an HTML rendering, or an attachment is an implementation detail for planning, not this spec.
- **Single recipient, single schedule**: this spec assumes one weekly job with one configured recipient and one recipe. Supporting multiple simultaneous schedules or recipients is out of scope unless requested as a future feature.
- **Governance note**: this feature is understood to automate and schedule the *existing* CLI interface's generation capability (already a stable contract per Principle IV) rather than introduce a new interactive, user-operated interface — the weekly trigger and email delivery are operational/delivery mechanisms wrapped around that existing contract, not a fourth interface a person directly operates. FR-009 encodes this reading directly as a requirement. If planning determines this reading doesn't hold — for example, if email delivery needs to become a capability exposed through the CLI/MCP/web contracts themselves, or the scheduled runner needs its own operator-facing controls — that may require a `/speckit-constitution` amendment to Principle IV before `/speckit-plan` can pass its Constitution Check gate for this feature, the same pattern 002-mcp-server and 003-react-vite-frontend followed.
