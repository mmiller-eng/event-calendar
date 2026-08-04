"""Load/save the trusted-source list (trusted_sources.yaml). Uniqueness key: url."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from src.models.trusted_source import TrustedSource


def load_sources(path: Path) -> list[TrustedSource]:
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [TrustedSource(**entry) for entry in raw]


def save_sources(path: Path, sources: list[TrustedSource]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = [
        {"name": s.name, "url": str(s.url), "added_at": s.added_at.isoformat()}
        for s in sources
    ]
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")


def add_source(path: Path, *, name: str, url: str) -> tuple[TrustedSource, bool]:
    """Returns (source, created) — created is False if url already existed (no-op)."""
    sources = load_sources(path)
    for existing in sources:
        if str(existing.url) == url:
            return existing, False
    new_source = TrustedSource(name=name, url=url, added_at=date.today())
    sources.append(new_source)
    save_sources(path, sources)
    return new_source, True


def remove_source(path: Path, *, url: str) -> bool:
    """Returns True if an entry was removed, False if it was already absent."""
    sources = load_sources(path)
    remaining = [s for s in sources if str(s.url) != url]
    if len(remaining) == len(sources):
        return False
    save_sources(path, remaining)
    return True
