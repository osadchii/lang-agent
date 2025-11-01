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

            # Create Loki handler with immediate sending (no buffering)
            loki_handler = LokiHandler(
                url=loki_url,
                tags=labels,
                version="1",
                auth=None,  # Set if using basic auth
            )
            loki_handler.setLevel(resolved_level)
            handlers.append(loki_handler)

            # Log a test message to verify Loki works
            test_logger = logging.getLogger("loki_test")
            test_logger.setLevel(resolved_level)
            test_logger.addHandler(loki_handler)
            test_logger.info("Loki handler test message - if you see this in Grafana, Loki is working!")
        except ImportError:
            logging.getLogger(__name__).warning(
                "python-logging-loki is not installed. Loki logging disabled. "
                "Install with: pip install python-logging-loki"
            )
        except Exception:
            logging.getLogger(__name__).exception("Failed to configure Loki handler")

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(resolved_level)
    # Clear existing handlers and add new ones
    root_logger.handlers.clear()
    for handler in handlers:
        root_logger.addHandler(handler)

    logging.captureWarnings(True)

    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured (level=%s)",
        logging.getLevelName(resolved_level),
    )

    # Log Loki configuration if enabled
    if loki_url and any(isinstance(h, type(h)) and "Loki" in type(h).__name__ for h in handlers):
        logger.info("Loki logging enabled (url=%s, labels=%s)", loki_url, loki_labels or {})

    # Ensure all existing loggers propagate to the root handler
    # This is important because loggers are created during module import
    # before configure_logging is called
    logger_names = list(logging.Logger.manager.loggerDict.keys())
    logger.info("Configuring %d existing loggers: %s", len(logger_names), logger_names)

    for name in logger_names:
        child_logger = logging.getLogger(name)
        # Clear handlers from child loggers so they propagate to root
        child_logger.handlers.clear()
        # Ensure propagation is enabled
        child_logger.propagate = True
        # Set level to match root (or inherit it)
        if child_logger.level == logging.NOTSET:
            child_logger.setLevel(resolved_level)

        logger.info(
            "Configured logger: name=%s, level=%s, propagate=%s, handlers=%d",
            name,
            logging.getLevelName(child_logger.level),
            child_logger.propagate,
            len(child_logger.handlers),
        )

    # Test that backend loggers work
    backend_test_logger = logging.getLogger("backend.test")
    backend_test_logger.info("Backend logger test - this should appear in logs and Loki")
