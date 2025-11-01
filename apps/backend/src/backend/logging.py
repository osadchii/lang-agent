"""Helpers for configuring structured logging across the backend."""

from __future__ import annotations

import logging
import sys

DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def configure_logging(
    level: str,
    loki_url: str | None = None,
    loki_labels: dict[str, str] | None = None,
) -> None:
    """
    Configure root logging with the provided level and a consistent format.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        loki_url: Optional Loki endpoint URL (e.g., http://loki:3100/loki/api/v1/push)
        loki_labels: Optional labels for Loki logs (e.g., {"application": "lang-agent", "environment": "production"})
    """
    try:
        resolved_level = getattr(logging, level.upper())
    except AttributeError:
        resolved_level = logging.INFO

    handlers: list[logging.Handler] = []

    # Console handler (always enabled)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(resolved_level)
    console_handler.setFormatter(logging.Formatter(DEFAULT_FORMAT))
    handlers.append(console_handler)

    # Loki handler (optional)
    if loki_url:
        try:
            from logging_loki import LokiHandler

            loki_handler = LokiHandler(
                url=loki_url,
                tags=loki_labels or {},
                version="1",
            )
            loki_handler.setLevel(resolved_level)
            handlers.append(loki_handler)
            logging.getLogger(__name__).info("Loki logging enabled (url=%s)", loki_url)
        except ImportError:
            logging.getLogger(__name__).warning(
                "python-logging-loki is not installed. Loki logging disabled. "
                "Install with: pip install python-logging-loki"
            )
        except Exception:
            logging.getLogger(__name__).exception("Failed to configure Loki handler")

    logging.basicConfig(level=resolved_level, handlers=handlers, force=True)
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
