FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# uv gives fast, reproducible installs pinned to uv.lock -- this scheduled
# job must be a reproducible, self-contained deployable unit (FR-008).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src/ src/
# Baked in at build time -- this deployment is stateless and never mutates
# it at runtime (spec.md Assumption; research.md #6). config.py's default
# ("trusted_sources.yaml", relative to cwd) resolves to this file as-is.
COPY trusted_sources.yaml ./

RUN uv sync --frozen

# No listening port: this runs to completion as a Cloud Run Job, not a
# Cloud Run Service (research.md #2).
ENTRYPOINT ["uv", "run", "--no-sync", "python", "-m", "src.scheduled_job.main"]
