"""Application configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    """Configuration values loaded from environment variables."""

    environment: str
    log_level: str
    openai_api_key: str | None

    @classmethod
    def load(cls) -> "AppConfig":
        """Load configuration values from the environment."""
        return cls(
            environment=os.getenv("APP_ENV", "development"),
            log_level=os.getenv("BOT_LOG_LEVEL", "INFO"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )

