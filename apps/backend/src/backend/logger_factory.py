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
    1. Are created with the correct propagation settings
    2. Don't add their own handlers (use root logger's handlers)
    3. Work correctly with Loki when configured

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

    # CRITICAL: Force configuration even if logging was already configured
    # This ensures all loggers work correctly regardless of creation order
    if name != "root":
        # Child loggers should propagate to root and not have their own handlers
        logger.propagate = True
        # Remove any handlers that might have been added
        logger.handlers.clear()
        # Set level to NOTSET so it inherits from root
        if logger.level != logging.NOTSET:
            logger.level = logging.NOTSET

    # Track loggers created before configuration
    if not _logging_configured and name not in _pending_loggers:
        _pending_loggers[name] = logger

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
    like aiogram) are properly configured to propagate to root logger.

    Call this after configure_logging() if you notice logs are missing from
    specific libraries.
    """
    if not _logging_configured:
        return

    root_logger = logging.getLogger()
    root_level = root_logger.level

    # Get all existing loggers
    logger_names = list(logging.Logger.manager.loggerDict.keys())

    for name in logger_names:
        logger_obj = logging.getLogger(name)
        if name != "root" and not name.startswith(("urllib3", "requests")):
            # Force proper configuration
            logger_obj.handlers.clear()
            logger_obj.propagate = True
            logger_obj.setLevel(logging.NOTSET)  # Inherit from root
