"""Helpers for configuring structured logging across the backend."""

from __future__ import annotations

import logging
import sys

DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def configure_logging(level: str) -> None:
    """Configure root logging with the provided level and a consistent format."""
    try:
        resolved_level = getattr(logging, level.upper())
    except AttributeError:
        resolved_level = logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(resolved_level)
    handler.setFormatter(logging.Formatter(DEFAULT_FORMAT))

    logging.basicConfig(level=resolved_level, handlers=[handler], force=True)
    logging.captureWarnings(True)

    logging.getLogger(__name__).info(
        "Logging configured (level=%s)",
        logging.getLevelName(resolved_level),
    )

    # Ensure aiogram and asyncio loggers propagate to the root handler.
    for logger_name in ("aiogram", "asyncio"):
        logger = logging.getLogger(logger_name)
        logger.setLevel(resolved_level)
        logger.propagate = True
