# Phase 0 Research: Scheduled Calendar Email

This feature does not yet exist in the codebase — the decisions below are
proposed, not verified against shipped code, resolving every open question
left in the plan's Technical Context.

## 1. Pipeline invocation: in-process calls, not CLI subprocess wrapping

**Decision**: `src/scheduled_job/main.py` calls `discover_events`,
`dedup.dedup_events`, `filtering.filter_events`, and `render_markdown`
directly, in-process — the same functions `src/mcp_server/server.py` and
`src/web_api/app.py` already call directly, not the CLI's own `generate()`
Click command, and not a subprocess invocation of the `calendar` executable.

**Rationale**: This is the third time this exact orchestration sequence is
needed by a new trigger (after the MCP server and the web API), and both of
those precedents already rejected subprocess-wrapping the CLI for the same
reason: CLI stdout is a human-readable contract, not a structured one, and
parsing it back would be fragile. Calling the core services directly gives
this feature the same typed errors (`DiscoveryUnavailableError`,
`MissingConfigError`) the other two already use, which the failure-email
path (spec.md US2) needs to produce a specific, plain-language message per
failure kind — a generic "the CLI exited non-zero" would not.

**Alternatives considered**: Subprocess-invoking `calendar generate` from
inside the container (rejected — same reasoning as 002/003's research: loses
structured error information, and the human-oriented stdout would have to be
re-parsed to build the failure email). Importing and calling
`src/cli/generate.py`'s Click command function directly (rejected — it's
wired to Click's argument-parsing/echo machinery, not designed to be called
as a plain function; the shared code it depends on is the same
`services`/`llm`/`config` layer this feature can call directly instead).

## 2. GCP primitive: Cloud Run Jobs, not a Cloud Run Service

**Decision**: Package the container as a **Cloud Run Job**, triggered on a
weekly cron schedule by Cloud Scheduler calling the Cloud Run Jobs "run"
API. The container runs to completion and exits; it never starts an HTTP
server or listens on a port.

**Rationale**: The user's own description — "run the calendar generate
command on a weekly basis (cron job)" — is exactly what Cloud Run Jobs is
built for: a run-to-completion batch workload on a schedule, as opposed to
Cloud Run's other mode (a *Service*), which is built for request-serving
workloads that stay up to accept inbound HTTP traffic. Choosing Jobs also
directly supports FR-009/Principle IV (Constitution Check): a Service would
need *some* HTTP endpoint for Cloud Scheduler to call, which is exactly the
kind of new network-facing, externally-callable surface this feature is
meant to avoid. A Job has no such surface — Cloud Scheduler triggers an
*execution*, not a *request*.

**Alternatives considered**: Cloud Run Service with an HTTP endpoint that
Cloud Scheduler's HTTP target hits weekly (rejected — requires running an
HTTP server inside the container purely to receive one trigger call a week,
which is unnecessary complexity and, per the Constitution Check above, edges
toward being a new interactive interface). A GKE CronJob or Compute Engine
instance with a system cron entry (rejected — both require managing a
cluster or a persistent VM for a workload that runs for a few minutes once a
week; Cloud Run Jobs is serverless and matches the "single-user simplicity"
ethos already used to justify FastAPI+Uvicorn over a heavier framework in
003).

## 3. Email delivery: stdlib SMTP, not a vendor SDK

**Decision**: Send email using Python's standard library (`smtplib` +
`email.message.EmailMessage`), configured via environment variables (SMTP
host, port, username, password, from-address) rather than a third-party
email API SDK (SendGrid, Mailgun, AWS SES, etc.) or the Gmail API.

**Rationale**: Every mainstream transactional email provider — including
Gmail/Google Workspace, SendGrid, Mailgun, and Amazon SES — offers an SMTP
relay interface, so stdlib SMTP works with all of them without locking this
feature to one vendor's SDK or credential model. This mirrors Principle II's
provider-agnostic ethos (applied here to email delivery rather than LLM
access) and adds zero new Python dependencies, consistent with 003's
research.md #1 preferring the option with the least new dependency surface
for the value delivered.

**Alternatives considered**: A vendor-specific SDK, e.g. `sendgrid-python`
(rejected — locks the deployment to one provider's account/API-key model for
no functional benefit over SMTP, which every such provider also supports).
The Gmail API via a Google service account (rejected — needs OAuth/service
account plumbing considerably more complex than an SMTP username/password,
for a single outbound email a week).

## 4. Recipe & delivery configuration: new env vars, read directly by the module

**Decision**: `src/scheduled_job/recipe.py` reads its own new environment
variables directly (e.g. `RECIPE_LOCATION`,
`RECIPE_CALENDAR_LENGTH_DAYS`, optionally `RECIPE_MAX_COST`
etc., plus `RECIPIENT_EMAIL` and `SMTP_HOST`/`SMTP_PORT`/
`SMTP_USERNAME`/`SMTP_PASSWORD`/`SMTP_FROM_ADDRESS`) rather than adding these
fields to `src/config.py`'s shared `Config` dataclass. The existing
pipeline-wide variables (`EVENT_CALENDAR_MODEL`, the provider API key,
`TAVILY_API_KEY`, `EVENT_CALENDAR_TRUSTED_SOURCES`) are reused unchanged via
the existing `load_config()`.

**Rationale**: `src/web_api/app.py` already established this precedent —
`EVENT_CALENDAR_WEB_ORIGIN` is read directly by `web_api/app.py`, not added
to `Config`, because it's specific to that one interface. The recipe and
email/SMTP settings are specific to the scheduled job in exactly the same
way; folding them into the shared `Config` would make every interface's
config surface carry fields only one of them uses, which is what plan.md's
"must not introduce a second configuration surface" constraint (echoing
003's plan.md) is meant to prevent for the *shared* concerns — while still
allowing each interface its own, clearly-scoped additions.

**Alternatives considered**: Adding `recipe_location`,
`recipient_email`, etc. to the shared `Config` dataclass (rejected — every
other interface (CLI/MCP/web) would then carry fields it never uses, and
`load_config()` would need to distinguish "required for this caller" from
"required for that caller," adding conditional complexity `Config` doesn't
currently have).

## 5. Failure handling: catch the same typed exceptions, always send exactly one email

**Decision**: `main.py` wraps the pipeline call in a `try`/`except` over the
same exception types the other interfaces already handle
(`DiscoveryUnavailableError`, `MissingConfigError`), plus a final bare
`except Exception` as a last-resort catch-all, and in every branch — success,
zero events, or any failure — sends exactly one email before the process
exits. The process exit code still reflects success/failure (0 vs. non-zero)
for Cloud Run's own run-history/alerting, independent of the email.

**Rationale**: Directly implements FR-006/SC-002 ("100% of scheduled runs
result in an email... never silence"). Reusing the same exception types the
CLI/MCP/web already catch (rather than inventing new ones) means the
failure email's message text can be built from the same `str(exc)` messages
already proven to be plain-language and user-facing (e.g.
`DiscoveryUnavailableError`'s "No trusted sources configured and web search
is unavailable."). The bare `except Exception` catch-all exists specifically
so a genuinely unanticipated bug still produces a failure email rather than
a silent, unexplained non-run — the one behavior SC-002 explicitly rules
out.

**Alternatives considered**: Letting an unhandled exception simply crash the
job (rejected — directly violates FR-006/SC-002; Cloud Run's own failure
logging is not a substitute for the plain-language user-facing notification
the spec requires). Retrying automatically on failure before giving up
(rejected — out of scope per spec.md, which describes one run per week with
a failure notification, not a retry policy; Cloud Scheduler's own
retry/alerting configuration is a deployment concern, not application logic).

## 6. Ephemeral output: the email is the only durable artifact

**Decision**: The generated Markdown file is written to the container's
local filesystem only as an intermediate step before being read back in to
build the email body; nothing in this feature attempts to persist it
anywhere (no bucket upload, no volume mount) once the run completes.

**Rationale**: Cloud Run Jobs containers are stateless and torn down after
each execution — anything written to the local filesystem is gone once the
run ends, unlike the CLI/MCP/web interfaces, which all run on a persistent
local machine where the output file is expected to remain on disk. Spec.md
does not ask for the calendar to be retrievable later by any means other
than the email itself (SC-001/SC-002 are both about the email arriving),
so adding persistence would be solving a problem the spec doesn't have.

**Alternatives considered**: Uploading the generated file to a Cloud Storage
bucket in addition to emailing it (rejected — not requested by spec.md, and
would introduce a second delivery/config surface — bucket name, IAM
permissions — for no described requirement; can be added later as its own
feature if wanted).

## 7. Deployment automation: GitHub Actions, authenticating via Workload Identity Federation

**Decision**: A `.github/workflows/deploy-scheduled-job.yml` workflow
builds the `Dockerfile` image, pushes it to Google Artifact Registry, and
runs `gcloud run jobs update` to point the existing Cloud Run Job at the new
image — triggered on push to `main` for changes under `src/scheduled_job/`,
`src/services/`, `src/llm/`, `src/models/`, `src/config.py`, or `Dockerfile`
itself, plus a manual `workflow_dispatch` for on-demand redeploys.
Authentication to GCP uses **Workload Identity Federation** (via
`google-github-actions/auth`) rather than a downloaded service-account JSON
key stored as a GitHub secret.

**Rationale**: The user explicitly asked for GitHub Actions as the
deployment mechanism. Workload Identity Federation lets GitHub Actions
authenticate to GCP by presenting its own OIDC token, exchanged for
short-lived GCP credentials scoped to one service account — no long-lived
key ever exists to leak, rotate, or accidentally commit, which is both
GitHub's and Google's current recommended pattern for CI-to-GCP auth. The
push-path filter (only these directories) avoids redeploying this feature's
container on changes that don't affect it (e.g. `frontend/` or
`specs/`work), and the manual `workflow_dispatch` trigger covers "redeploy
with no code change" cases (e.g. after rotating a secret in Secret Manager).

**Alternatives considered**: A downloaded service-account JSON key stored as
a `GCP_SA_KEY` GitHub secret (rejected — a long-lived credential is a
standing security liability compared to WIF's short-lived, non-exportable
tokens; both GitHub's and Google's own documentation now recommend WIF over
key-based auth for this exact scenario). Google Cloud Build instead of
GitHub Actions (rejected outright — the user explicitly asked for GitHub
Actions). Deploying manually via the `deploy/README.md` runbook only, with
no CI automation (rejected — the user explicitly asked for automated
deployment via GitHub Actions, not a manual-only process).
