"""`calendar sources list|add|remove` commands (contracts/cli-contract.md)."""

from __future__ import annotations

import click
from pydantic import ValidationError

from src.config import load_config
from src.services.discovery import trusted_source_store


@click.group("sources")
def sources() -> None:
    """Manage the trusted local source list."""


@sources.command("list")
def list_sources() -> None:
    config = load_config()
    entries = trusted_source_store.load_sources(config.trusted_sources_path)
    if not entries:
        click.echo("No trusted sources configured.")
        return
    for entry in entries:
        click.echo(f"{entry.name}\t{entry.url}\t{entry.added_at.isoformat()}")


@sources.command("add")
@click.option("--name", required=True)
@click.option("--url", required=True)
@click.pass_context
def add_source(ctx: click.Context, name: str, url: str) -> None:
    config = load_config()
    try:
        source, created = trusted_source_store.add_source(
            config.trusted_sources_path, name=name, url=url
        )
    except ValidationError as exc:
        click.echo(f"Invalid --url: {exc}", err=True)
        ctx.exit(2)
        return
    if not created:
        click.echo(
            f"Already exists: {source.name}\t{source.url}\t{source.added_at.isoformat()}"
        )
        ctx.exit(4)
        return
    click.echo(f"Added: {source.name}\t{source.url}\t{source.added_at.isoformat()}")


@sources.command("remove")
@click.option("--url", required=True)
def remove_source(url: str) -> None:
    config = load_config()
    trusted_source_store.remove_source(config.trusted_sources_path, url=url)
    click.echo(f"Removed: {url}")
