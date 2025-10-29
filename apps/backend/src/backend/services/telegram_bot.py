"""Telegram bot runner built on top of aiogram."""

from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ErrorEvent, Message

from .conversation import ConversationService, UserMessagePayload

logger = logging.getLogger(__name__)


class TelegramBotRunner:
    """Manage Telegram bot lifecycle and delegate updates to the conversation service."""

    def __init__(self, *, token: str, conversation: ConversationService) -> None:
        self._bot = Bot(token=token)
        self._dispatcher = Dispatcher()
        self._conversation = conversation

        self._dispatcher.message.register(self._handle_text_message, F.text)
        self._dispatcher.errors.register(self._handle_error)

    async def start(self) -> None:
        """Begin polling for Telegram updates."""
        logger.info("Starting Telegram polling...")
        await self._dispatcher.start_polling(self._bot)

    async def _handle_text_message(self, message: Message) -> None:
        """Process inbound text messages."""
        if not message.from_user:
            logger.debug("Skipping message without sender: %s", message.message_id)
            return

        payload = UserMessagePayload(
            user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            text=message.text or "",
        )

        try:
            reply = await self._conversation.handle_user_message(payload)
        except Exception as ex:  # pragma: no cover - defensive logging
            logger.exception("Failed to handle message %s", message.message_id)
            await self._safe_reply(message, "Произошла ошибка. Попробуйте ещё раз позже.")
            raise

        await self._safe_reply(message, reply)

    async def _safe_reply(self, message: Message, text: str) -> None:
        """Send a reply while guarding against Telegram API errors."""
        try:
            await message.answer(text)
        except TelegramBadRequest:
            logger.exception("Failed to send reply for message %s", message.message_id)
        except Exception:  # pragma: no cover - unexpected transport errors
            logger.exception("Unexpected error while replying to message %s", message.message_id)

    async def _handle_error(self, event: ErrorEvent) -> None:
        """Log uncaught dispatcher errors and re-raise them for visibility."""
        update_id = getattr(event.update, "update_id", "unknown")
        logger.error(
            "Dispatcher error for update %s: %s",
            update_id,
            event.exception,
            exc_info=event.exception,
        )
        raise event.exception
