"""Application configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    """Configuration values loaded from environment variables."""

    environment: str
    log_level: str
    openai_api_key: str
    telegram_bot_token: str
    openai_model: str
    database_url: str
    openai_system_prompt: str

    @classmethod
    def load(cls) -> "AppConfig":
        """Load configuration values from the environment."""
        from .resources.prompts import GREEK_TEACHER_PROMPT

        openai_api_key = os.getenv("OPENAI_API_KEY")
        telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

        if not openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required to run the bot.")

        if not telegram_bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is required to run the bot.")

        return cls(
            environment=os.getenv("APP_ENV", "development"),
            log_level=os.getenv("BOT_LOG_LEVEL", "INFO"),
            openai_api_key=openai_api_key,
            telegram_bot_token=telegram_bot_token,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db"),
            openai_system_prompt=os.getenv("OPENAI_SYSTEM_PROMPT", GREEK_TEACHER_PROMPT),
        )
