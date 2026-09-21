"""Scheduled job entrypoint (contracts/scheduled-job-contract.md).

No CLI args, no stdin -- all configuration is environment variables.
Every run ends in exactly one email, success or failure (FR-006/SC-002).
"""

from __future__ import annotations

import sys

from src.config import load_config
from src.llm.provider import LLMProvider, MissingConfigError
from src.models.event import CulturalEvent
from src.scheduled_job import email_delivery
from src.scheduled_job.email_delivery import RunOutcome
from src.scheduled_job.recipe import Recipe, RecipeConfigError, build_email_config, build_recipe
from src.services.discovery import DiscoveryUnavailableError


def _run_pipeline(recipe: Recipe) -> list[CulturalEvent]:
    config = load_config()
    LLMProvider(config)  # may raise MissingConfigError
    # T010 wires discover_events -> dedup.dedup_events -> filtering.filter_events
    # -> render_markdown here, matching research.md #1's in-process reuse.
    return []


def run() -> int:
    try:
        email_config = build_email_config()
    except RecipeConfigError as exc:
        print(f"FATAL: cannot send any notification: {exc}", file=sys.stderr)
        return 1

    location: str | None = None
    try:
        recipe = build_recipe()
        location = recipe.location
        events = _run_pipeline(recipe)
        outcome = RunOutcome.success(events)
    except (RecipeConfigError, MissingConfigError, DiscoveryUnavailableError) as exc:
        outcome = RunOutcome.failure(str(exc))

    try:
        email_delivery.send(outcome, email_config, location=location)
    except Exception as exc:
        print(f"FATAL: failed to send notification email: {exc}", file=sys.stderr)
        return 1

    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
