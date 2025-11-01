"""Centralized logger factory to ensure all loggers are properly configured."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

_logging_configured = False
_pending_loggers: dict[str, logging.Logger] = {}


def mark_logging_configured() -> None:
    """
    Mark that logging has been configured.

    This should be called by configure_logging() after it completes setup.
    """
    global _logging_configured
    _logging_configured = True


def is_logging_configured() -> bool:
    """Check if logging has been configured."""
    return _logging_configured


def get_logger(name: str) -> logging.Logger:
    """
    Get a properly configured logger instance.

    This factory function ensures that all loggers:
    1. Are created with the correct handlers (console + Loki)
    2. Work correctly regardless of creation order
    3. Have all logs properly routed to configured destinations

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        A configured logger instance

    Example:
        ```python
        from backend.logger_factory import get_logger

        logger = get_logger(__name__)
        logger.info("This will go to console and Loki")
        ```
    """
    # Always use the standard logging.getLogger to maintain singleton behavior
    logger = logging.getLogger(name)

    # Track loggers created before configuration
    if not _logging_configured and name not in _pending_loggers:
        _pending_loggers[name] = logger

    # Apply handlers directly to this logger
    # This is called from logging.py so we need to import here to avoid circular dependency
    if _logging_configured and name != "root":
        from .logging import configure_logger
        configure_logger(logger)

    return logger


def get_pending_loggers() -> list[str]:
    """
    Get list of logger names that were created before configure_logging() was called.

    This is useful for debugging and ensuring proper initialization order.
    """
    return list(_pending_loggers.keys())


def reconfigure_all_loggers() -> None:
    """
    Force reconfiguration of all existing loggers.

    This ensures that all loggers (including ones created by third-party libraries
    like aiogram) are properly configured with the correct handlers.

    Call this after configure_logging() if you notice logs are missing from
    specific libraries.
    """
    if not _logging_configured:
        return

    from .logging import configure_logger

    # Get all existing loggers
    logger_names = list(logging.Logger.manager.loggerDict.keys())

    for name in logger_names:
        if name != "root" and not name.startswith(("urllib3", "requests")):
            logger_obj = logging.getLogger(name)
            # Apply handlers directly to this logger
            configure_logger(logger_obj)
