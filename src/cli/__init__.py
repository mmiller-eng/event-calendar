"""CLI entry point: the `calendar` command group."""

from __future__ import annotations

import click

from src.cli import generate as generate_module
from src.cli.sources import sources


@click.group()
def cli() -> None:
    """Cultural Event Calendar Agent."""


cli.add_command(generate_module.generate)
cli.add_command(sources)
