"""Main application entry point for the Greek language learning bot."""

from __future__ import annotations

from dataclasses import dataclass

from .config import AppConfig


@dataclass
class BotApp:
    """Encapsulates high-level bot lifecycle operations."""

    config: AppConfig

    def start(self) -> None:
        """Start the bot; replace with real initialization logic."""
        # Placeholder implementation until integration is defined.
        print(f"Starting bot in {self.config.environment} mode...")


def bootstrap() -> BotApp:
    """Create the application instance with environment-backed configuration."""
    return BotApp(config=AppConfig.load())


def main() -> None:
    """CLI entrypoint."""
    app = bootstrap()
    app.start()


if __name__ == "__main__":
    main()

