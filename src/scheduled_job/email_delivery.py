"""RunOutcome -> subject/body mapping and SMTP sending (data-model.md `RunOutcome`;
contracts/scheduled-job-contract.md's Email content contract).
"""

from __future__ import annotations

import smtplib
from dataclasses import dataclass, field
from datetime import date as date_cls
from email.message import EmailMessage
from typing import Literal

from src.models.event import CulturalEvent
from src.scheduled_job.recipe import EmailDeliveryConfig
from src.services.markdown import _render_event, _sort_key


@dataclass
class RunOutcome:
    status: Literal["success", "failure"]
    events: list[CulturalEvent] = field(default_factory=list)
    error_message: str | None = None

    @classmethod
    def success(cls, events: list[CulturalEvent]) -> RunOutcome:
        return cls(status="success", events=events)

    @classmethod
    def failure(cls, error_message: str) -> RunOutcome:
        return cls(status="failure", error_message=error_message)


def _build_subject(outcome: RunOutcome, location: str | None) -> str:
    if outcome.status == "failure":
        if location:
            return f"Cultural Event Calendar: {location} — run failed"
        return "Cultural Event Calendar — run failed"
    event_count = len(outcome.events)
    if event_count == 0:
        return f"Cultural Event Calendar: {location} (no events found)"
    return f"Cultural Event Calendar: {location} ({event_count} events)"


def _build_body(outcome: RunOutcome) -> str:
    if outcome.status == "failure":
        return outcome.error_message or "An unknown error occurred."
    if not outcome.events:
        return "No events matched your preferences."

    events_by_date: dict[date_cls, list[CulturalEvent]] = {}
    for event in sorted(outcome.events, key=_sort_key):
        events_by_date.setdefault(event.date, []).append(event)

    lines: list[str] = []
    for event_date in sorted(events_by_date):
        lines.append(event_date.isoformat())
        for event in events_by_date[event_date]:
            lines.append(f"- {_render_event(event)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def send(outcome: RunOutcome, config: EmailDeliveryConfig, location: str | None = None) -> None:
    message = EmailMessage()
    message["Subject"] = _build_subject(outcome, location)
    message["From"] = config.from_address
    message["To"] = config.recipient_email
    message.set_content(_build_body(outcome))

    with smtplib.SMTP(config.smtp_host, config.smtp_port) as smtp:
        if config.smtp_username and config.smtp_password:
            smtp.login(config.smtp_username, config.smtp_password)
        smtp.send_message(message)
