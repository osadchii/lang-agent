"""CLI entrypoint for manual bot runtime control."""

from __future__ import annotations

from ..application import bootstrap


def main() -> None:
    """Launch the bot runtime from the command line."""
    app = bootstrap()
    app.start()
