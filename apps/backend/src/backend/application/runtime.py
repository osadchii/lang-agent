"""Runtime composition for the language learning backend."""

from __future__ import annotations

from dataclasses import dataclass

from ..config import AppConfig


@dataclass
class BotApp:
    """Encapsulate bot lifecycle operations and service orchestration."""

    config: AppConfig

    def start(self) -> None:
        """Start the bot runtime. Replace with real bootstrap once integrations exist."""
        # Placeholder implementation until infrastructure is wired in.
        print(f"Starting bot in {self.config.environment} mode...")


def bootstrap() -> BotApp:
    """Create an application instance backed by environment configuration."""
    return BotApp(config=AppConfig.load())
