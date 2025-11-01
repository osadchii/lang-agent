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
            import socket
            from logging_loki import LokiHandler  # type: ignore[import-not-found]

            # Ensure we have labels
            labels = loki_labels or {}
            # Add hostname if not present
            if "host" not in labels:
                labels["host"] = socket.gethostname()
            if "job" not in labels:
                labels["job"] = "lang-agent"

            loki_handler = LokiHandler(
                url=loki_url,
                tags=labels,
                version="1",
                # Add additional metadata
                auth=None,  # Set if using basic auth
            )
            loki_handler.setLevel(resolved_level)
            handlers.append(loki_handler)
        except ImportError:
            logging.getLogger(__name__).warning(
                "python-logging-loki is not installed. Loki logging disabled. "
                "Install with: pip install python-logging-loki"
            )
        except Exception:
            logging.getLogger(__name__).exception("Failed to configure Loki handler")

    logging.basicConfig(level=resolved_level, handlers=handlers, force=True)
    logging.captureWarnings(True)

    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured (level=%s)",
        logging.getLevelName(resolved_level),
    )

    # Log Loki configuration if enabled
    if loki_url and any(isinstance(h, type(h)) and "Loki" in type(h).__name__ for h in handlers):
        logger.info("Loki logging enabled (url=%s, labels=%s)", loki_url, loki_labels or {})

    # Ensure aiogram and asyncio loggers propagate to the root handler.
    for logger_name in ("aiogram", "asyncio"):
        logger = logging.getLogger(logger_name)
        logger.setLevel(resolved_level)
        logger.propagate = True
