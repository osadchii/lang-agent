"""Runtime composition for the language learning backend."""

from __future__ import annotations

from dataclasses import dataclass

from ..config import AppConfig as BackendAppConfig


@dataclass
class BotApp:
    """Encapsulate bot lifecycle operations and service orchestration."""

    config: BackendAppConfig
    database: object  # Database - typed as object to avoid import before logging setup
    telegram_bot: object  # TelegramBotRunner

    async def start(self) -> None:
        """Initialize infrastructure and start polling Telegram updates."""
        await self.database.initialize()  # type: ignore[attr-defined]
        try:
            await self.telegram_bot.start()  # type: ignore[attr-defined]
        finally:  # pragma: no branch - ensure resources close during shutdown
            await self.database.dispose()  # type: ignore[attr-defined]


def bootstrap() -> BotApp:
    """Create an application instance backed by environment configuration."""
    config = BackendAppConfig.load()

    # ВАЖНО: Настроить логирование ДО импорта любых сервисов!
    from ..logging import configure_logging
    configure_logging(
        level=config.log_level,
        loki_url=config.loki_url,
        loki_labels=config.loki_labels,
    )

    # Import services AFTER logging is configured
    from ..services.conversation import ConversationService
    from ..services.flashcards import FlashcardService
    from ..services.llm import OpenAIChatClient, OpenAIFlashcardGenerator
    from ..services.storage.database import Database
    from ..services.telegram_bot import TelegramBotRunner

    database = Database(config.database_url)
    llm_client = OpenAIChatClient(
        api_key=config.openai_api_key,
        model=config.openai_model,
        system_prompt=config.openai_system_prompt,
    )
    flashcard_generator = OpenAIFlashcardGenerator(
        api_key=config.openai_api_key,
        model=config.openai_model,
    )
    conversation = ConversationService(
        database=database,
        llm_client=llm_client,
        model_name=config.openai_model,
    )
    flashcards = FlashcardService(
        database=database,
        generator=flashcard_generator,
        llm=llm_client,
    )
    telegram_bot = TelegramBotRunner(
        token=config.telegram_bot_token,
        conversation=conversation,
        flashcards=flashcards,
    )

    return BotApp(
        config=config,
        database=database,  # type: ignore[arg-type]
        telegram_bot=telegram_bot,  # type: ignore[arg-type]
    )
