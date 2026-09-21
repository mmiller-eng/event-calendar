"""Build Recipe and EmailDeliveryConfig from environment variables (data-model.md).

Every value here is read fresh from the environment on every call — nothing
is cached or hardcoded, which is what makes changing the recipe or recipient
purely a matter of redeploying with new environment variables (US3).
"""

from __future__ import annotations

import os
from datetime import time as time_cls
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, Field, ValidationError, model_validator


class RecipeConfigError(Exception):
    """Raised when required scheduled-job configuration is missing or invalid.

    Treated as a run failure, not raised to any caller (contracts/scheduled-job-contract.md step 1).
    """


class Recipe(BaseModel):
    location: str
    calendar_length_days: int = Field(gt=0)
    max_cost: Decimal | None = None
    event_types: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)
    start_after: time_cls | None = None
    start_before: time_cls | None = None

    @model_validator(mode="after")
    def _start_window_must_be_complete(self) -> Recipe:
        if (self.start_after is None) != (self.start_before is None):
            raise ValueError(
                "RECIPE_START_AFTER and RECIPE_START_BEFORE must both be set, or both omitted"
            )
        return self

    @property
    def start_time_window(self) -> tuple[time_cls, time_cls] | None:
        if self.start_after is None or self.start_before is None:
            return None
        return (self.start_after, self.start_before)


class EmailDeliveryConfig(BaseModel):
    recipient_email: str
    smtp_host: str
    smtp_port: int
    smtp_username: str | None = None
    smtp_password: str | None = None
    from_address: str


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"{name} is required")
    return value


def _require_int(name: str) -> int:
    raw = _require(name)
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _optional_decimal(name: str) -> Decimal | None:
    raw = os.environ.get(name)
    if not raw:
        return None
    try:
        return Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"{name} must be a decimal number") from exc


def _optional_list(name: str) -> list[str]:
    raw = os.environ.get(name)
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _optional_time(name: str) -> time_cls | None:
    raw = os.environ.get(name)
    if not raw:
        return None
    try:
        return time_cls.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be HH:MM") from exc


def _format_error(exc: ValueError | ValidationError) -> str:
    if isinstance(exc, ValidationError):
        return "; ".join(err["msg"] for err in exc.errors())
    return str(exc)


def build_recipe() -> Recipe:
    try:
        return Recipe(
            location=_require("RECIPE_LOCATION"),
            calendar_length_days=_require_int("RECIPE_CALENDAR_LENGTH_DAYS"),
            max_cost=_optional_decimal("RECIPE_MAX_COST"),
            event_types=_optional_list("RECIPE_EVENT_TYPES"),
            genres=_optional_list("RECIPE_GENRES"),
            start_after=_optional_time("RECIPE_START_AFTER"),
            start_before=_optional_time("RECIPE_START_BEFORE"),
        )
    except (ValueError, ValidationError) as exc:
        raise RecipeConfigError(_format_error(exc)) from exc


def build_email_config() -> EmailDeliveryConfig:
    try:
        return EmailDeliveryConfig(
            recipient_email=_require("RECIPIENT_EMAIL"),
            smtp_host=_require("SMTP_HOST"),
            smtp_port=_require_int("SMTP_PORT"),
            smtp_username=os.environ.get("SMTP_USERNAME") or None,
            smtp_password=os.environ.get("SMTP_PASSWORD") or None,
            from_address=_require("SMTP_FROM_ADDRESS"),
        )
    except (ValueError, ValidationError) as exc:
        raise RecipeConfigError(_format_error(exc)) from exc
