"""Config loading: model/provider selection, API keys, trusted-source file path, output dir."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

# Loads a `.env` file from the current working directory (or a parent of it) into
# the process environment, without overriding variables already set explicitly.
load_dotenv(find_dotenv(usecwd=True))

_PROVIDER_API_KEY_ENV_VARS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}


def api_key_env_var_for_model(model: str) -> str:
    """Map a litellm `provider/model` string to the env var holding its API key."""
    provider = model.split("/", 1)[0] if "/" in model else model
    return _PROVIDER_API_KEY_ENV_VARS.get(provider, f"{provider.upper()}_API_KEY")


@dataclass(frozen=True)
class Config:
    model: str | None
    api_key_env_var: str | None
    api_key: str | None
    tavily_api_key: str | None
    trusted_sources_path: Path
    output_dir: Path


def load_config(model_override: str | None = None) -> Config:
    model = model_override or os.environ.get("EVENT_CALENDAR_MODEL") or None
    api_key_env_var = api_key_env_var_for_model(model) if model else None
    api_key = os.environ.get(api_key_env_var) if api_key_env_var else None
    tavily_api_key = os.environ.get("TAVILY_API_KEY") or None
    trusted_sources_path = Path(
        os.environ.get("EVENT_CALENDAR_TRUSTED_SOURCES", "trusted_sources.yaml")
    )
    output_dir = Path(os.environ.get("EVENT_CALENDAR_OUTPUT_DIR", "calendars"))
    return Config(
        model=model,
        api_key_env_var=api_key_env_var,
        api_key=api_key,
        tavily_api_key=tavily_api_key,
        trusted_sources_path=trusted_sources_path,
        output_dir=output_dir,
    )
