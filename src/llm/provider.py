"""Provider-agnostic LLM client wrapper (litellm), model selected via config."""

from __future__ import annotations

import json

import litellm

from src.config import Config

EXTRACTION_SYSTEM_PROMPT = """\
You are an information-extraction assistant. Given raw text from a cultural-events \
source (a venue/organization page or web search result), extract every distinct \
cultural event mentioned.

Return ONLY a JSON array (no prose, no markdown fences). Each element must be an \
object with exactly these keys:
- "name": string
- "date": string, ISO format YYYY-MM-DD
- "start_time": string "HH:MM" (24-hour) or the literal string "unknown"
- "venue": string
- "cost": a number, the literal string "free", or the literal string "unknown"
- "event_type": one of "music", "theater", "festival", "comedy", "art", or another \
short lowercase category
- "genre": string (only when event_type is "music"), "unknown" if music but genre \
can't be determined, or null otherwise

Never fabricate a value you cannot determine from the text — use "unknown" instead. \
If the text describes no events, return an empty array [].
"""


class MissingConfigError(Exception):
    """Raised when a required model/API-key configuration value is absent."""

    def __init__(self, env_var: str, message: str | None = None):
        self.env_var = env_var
        super().__init__(message or f"Missing required configuration: set {env_var}")


class LLMProvider:
    def __init__(self, config: Config):
        if not config.model:
            raise MissingConfigError(
                "EVENT_CALENDAR_MODEL",
                "No model configured: set EVENT_CALENDAR_MODEL or pass --model",
            )
        if not config.api_key:
            raise MissingConfigError(config.api_key_env_var)
        self._model = config.model

    def extract_events(self, text: str, *, source_description: str) -> list[dict]:
        response = litellm.completion(
            model=self._model,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": f"Source: {source_description}\n\n{text}"},
            ],
        )
        content = response["choices"][0]["message"]["content"]
        return _parse_json_array(content)


def _parse_json_array(content: str) -> list[dict]:
    content = content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:]
    content = content.strip()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]
