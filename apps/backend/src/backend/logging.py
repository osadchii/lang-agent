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

            # CRITICAL: Disable urllib3 and requests logging BEFORE creating Loki handler
            # to prevent infinite recursion when Loki is unreachable
            logging.getLogger("urllib3").setLevel(logging.WARNING)
            logging.getLogger("urllib3").propagate = False
            logging.getLogger("requests").setLevel(logging.WARNING)
            logging.getLogger("requests").propagate = False

            # Create a filter to prevent urllib3/requests logs from going to Loki
            class NoHTTPLibLogsFilter(logging.Filter):
                def filter(self, record: logging.LogRecord) -> bool:
                    return not record.name.startswith(("urllib3", "requests"))

            # Create Loki handler with immediate sending (no buffering)
            loki_handler = LokiHandler(
                url=loki_url,
                tags=labels,
                version="1",
                auth=None,  # Set if using basic auth
            )
            loki_handler.setLevel(resolved_level)
            loki_handler.addFilter(NoHTTPLibLogsFilter())
            handlers.append(loki_handler)
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

    # Import get_logger after logging is configured to avoid circular dependency
    from .logger_factory import get_logger as _get_logger

    logger = _get_logger(__name__)
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
    logger.info("Configuring %d existing loggers (backend.*, aiogram.*, etc.)", len(logger_names))

    for name in logger_names:
        child_logger = logging.getLogger(name)
        # Clear handlers from child loggers so they propagate to root
        child_logger.handlers.clear()
        # Ensure propagation is enabled
        child_logger.propagate = True
        # Set level to NOTSET so it inherits from root
        child_logger.setLevel(logging.NOTSET)

    # Test that backend loggers work
    backend_test_logger = logging.getLogger("backend.test")
    backend_test_logger.info("Backend logger test - this should appear in logs and Loki")

    # Install a factory to ensure all future loggers also propagate correctly
    try:
        old_logger_class = logging.getLoggerClass()

        class PropagatingLogger(old_logger_class):  # type: ignore[misc,valid-type]
            """Custom logger that ensures propagation is always enabled."""

            def __init__(self, name: str, level: int = logging.NOTSET) -> None:
                super().__init__(name, level)
                # Ensure propagation for all new loggers
                self.propagate = True
                # Don't add handlers to child loggers - let them propagate to root
                if name != "root":
                    self.handlers = []

        logging.setLoggerClass(PropagatingLogger)
        logger.info("Installed custom logger class to ensure all future loggers propagate to root")
    except Exception:
        logger.exception("Failed to install custom logger class - continuing with default")

    # Mark logging as configured so the factory knows it's safe
    from .logger_factory import mark_logging_configured, get_pending_loggers

    mark_logging_configured()

    # Log information about loggers created before configuration
    pending = get_pending_loggers()
    if pending:
        logger.debug(
            "Detected %d logger(s) created before configure_logging: %s",
            len(pending),
            ", ".join(pending[:5]) + ("..." if len(pending) > 5 else ""),
        )
