"""Runtime composition for the language learning backend."""

from __future__ import annotations

from dataclasses import dataclass

from ..config import AppConfig
from ..services.conversation import ConversationService
from ..services.llm import OpenAIChatClient
from ..services.storage.database import Database
from ..services.telegram_bot import TelegramBotRunner


@dataclass
class BotApp:
    """Encapsulate bot lifecycle operations and service orchestration."""

    config: AppConfig
    database: Database
    telegram_bot: TelegramBotRunner

    async def start(self) -> None:
        """Initialize infrastructure and start polling Telegram updates."""
        await self.database.initialize()
        try:
            await self.telegram_bot.start()
        finally:  # pragma: no branch - ensure resources close during shutdown
            await self.database.dispose()


def bootstrap() -> BotApp:
    """Create an application instance backed by environment configuration."""
    config = AppConfig.load()
    database = Database(config.database_url)
    llm_client = OpenAIChatClient(
        api_key=config.openai_api_key,
        model=config.openai_model,
        system_prompt=config.openai_system_prompt,
    )
    conversation = ConversationService(
        database=database,
        llm_client=llm_client,
        model_name=config.openai_model,
    )
    telegram_bot = TelegramBotRunner(token=config.telegram_bot_token, conversation=conversation)

    return BotApp(config=config, database=database, telegram_bot=telegram_bot)
