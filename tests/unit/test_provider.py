from __future__ import annotations

from pathlib import Path

import pytest

from src.config import Config, api_key_env_var_for_model
from src.llm.provider import LLMProvider, MissingConfigError


def _config(**overrides) -> Config:
    defaults = dict(
        model=None,
        api_key_env_var=None,
        api_key=None,
        tavily_api_key=None,
        trusted_sources_path=Path("trusted_sources.yaml"),
        output_dir=Path("calendars"),
    )
    defaults.update(overrides)
    return Config(**defaults)


def test_api_key_env_var_for_known_providers():
    assert api_key_env_var_for_model("anthropic/claude-sonnet-5") == "ANTHROPIC_API_KEY"
    assert api_key_env_var_for_model("openai/gpt-5") == "OPENAI_API_KEY"


def test_api_key_env_var_for_unknown_provider_falls_back_to_convention():
    assert api_key_env_var_for_model("mistral/large") == "MISTRAL_API_KEY"


def test_missing_model_raises():
    with pytest.raises(MissingConfigError):
        LLMProvider(_config())


def test_missing_api_key_raises_naming_env_var():
    config = _config(model="anthropic/claude-sonnet-5", api_key_env_var="ANTHROPIC_API_KEY")
    with pytest.raises(MissingConfigError) as exc_info:
        LLMProvider(config)
    assert exc_info.value.env_var == "ANTHROPIC_API_KEY"


def test_valid_config_constructs_provider():
    config = _config(
        model="anthropic/claude-sonnet-5",
        api_key_env_var="ANTHROPIC_API_KEY",
        api_key="test-key",
    )
    provider = LLMProvider(config)
    assert provider is not None
