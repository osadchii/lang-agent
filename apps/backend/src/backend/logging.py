"""Helpers for configuring structured logging across the backend."""

from __future__ import annotations

import logging
import sys

DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# Global storage for handlers configured by configure_logging()
_configured_handlers: list[logging.Handler] = []
_logging_level: int = logging.INFO
# Override noisy third-party loggers (match exact name or dotted prefix)
_LOGGER_LEVEL_OVERRIDES: dict[str, int] = {
    "sqlalchemy.engine": logging.WARNING,
    "sqlalchemy.pool": logging.WARNING,
}


def configure_logger(logger: logging.Logger) -> None:
    """
    Apply configured handlers to a specific logger instance.

    This function should be called from the logger factory for each new logger
    to ensure it has the correct handlers (console + Loki) attached directly.

    Args:
        logger: Logger instance to configure

    Note:
        This function is safe to call multiple times on the same logger.
        It will clear existing handlers before applying the configured ones.
    """
    if not _configured_handlers:
        # Logging not yet configured, skip
        return

    # Clear any existing handlers
    logger.handlers.clear()

    # Add all configured handlers (console + Loki)
    for handler in _configured_handlers:
        logger.addHandler(handler)

    # Apply per-logger level overrides when configured
    level_override: int | None = None
    for name, override in _LOGGER_LEVEL_OVERRIDES.items():
        if logger.name == name or logger.name.startswith(f"{name}."):
            level_override = override
            break

    # Set logger level (override noisy defaults such as sqlalchemy.engine)
    logger.setLevel(level_override if level_override is not None else _logging_level)

    # Disable propagation since we're attaching handlers directly
    # This prevents duplicate logs
    logger.propagate = False


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

    # Store handlers and level globally for use by configure_logger()
    global _configured_handlers, _logging_level
    _configured_handlers = handlers.copy()
    _logging_level = resolved_level

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

    # Reconfigure all existing loggers to use the new handlers
    # This is important because loggers are created during module import
    # before configure_logging is called
    logger_names = list(logging.Logger.manager.loggerDict.keys())
    logger.info("Configuring %d existing loggers (backend.*, aiogram.*, etc.)", len(logger_names))

    for name in logger_names:
        if name != "root" and not name.startswith(("urllib3", "requests")):
            child_logger = logging.getLogger(name)
            configure_logger(child_logger)

    # Test that backend loggers work
    backend_test_logger = logging.getLogger("backend.test")
    configure_logger(backend_test_logger)
    backend_test_logger.info("Backend logger test - this should appear in logs and Loki")

    # Mark logging as configured so the factory knows it's safe
    from .logger_factory import mark_logging_configured, get_pending_loggers

    mark_logging_configured()

    # Reconfigure loggers that were created before configure_logging
    pending = get_pending_loggers()
    if pending:
        logger.debug(
            "Detected %d logger(s) created before configure_logging: %s",
            len(pending),
            ", ".join(pending[:5]) + ("..." if len(pending) > 5 else ""),
        )
        # Apply handlers to pending loggers
        for name in pending:
            pending_logger = logging.getLogger(name)
            configure_logger(pending_logger)
