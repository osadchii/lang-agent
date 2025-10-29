"""CLI entrypoint for bot lifecycle and database utilities."""

from __future__ import annotations

import argparse
import asyncio

from ..application import bootstrap


async def _run_bot() -> None:
    """Start the bot runtime until interrupted."""
    app = bootstrap()
    await app.start()


async def _run_migrations() -> None:
    """Upgrade the database schema to the latest revision."""
    app = bootstrap()
    try:
        await app.database.initialize()
    finally:
        await app.database.dispose()


def main() -> None:
    """Dispatch CLI subcommands."""
    parser = argparse.ArgumentParser(description="Language bot backend utilities.")
    parser.add_argument(
        "command",
        nargs="?",
        choices=("run", "migrate"),
        default="run",
        help="run: start the bot (default); migrate: upgrade database schema.",
    )
    args = parser.parse_args()

    if args.command == "migrate":
        asyncio.run(_run_migrations())
    else:
        asyncio.run(_run_bot())
