"""CLI entrypoint for manual bot runtime control."""

from __future__ import annotations

import asyncio

from ..application import bootstrap


def main() -> None:
    """Launch the bot runtime from the command line."""
    app = bootstrap()
    asyncio.run(app.start())
