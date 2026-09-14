"""Small helpers shared across the CLI, MCP server, and web API interfaces."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.config import Config


def default_output_path(config: Config, generated_at: datetime) -> Path:
    return config.output_dir / f"{generated_at.date().isoformat()}.md"
