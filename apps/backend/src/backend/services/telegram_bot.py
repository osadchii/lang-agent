"""Telegram bot runner built on top of aiogram."""

from __future__ import annotations

import logging
import re

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, ErrorEvent, Message, User
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .conversation import ConversationService, UserMessagePayload
from .flashcards import FlashcardCreationResult, FlashcardService, ReviewRating, StudyCard, UserProfile

logger = logging.getLogger(__name__)

_FLASHCARD_CALLBACK_PREFIX = "flashcard"
_FLASHCARD_SPLIT_PATTERN = re.compile(r"[,\n;]+")


class TelegramBotRunner:
    """Manage Telegram bot lifecycle and delegate updates to the conversation and flashcard services."""

    def __init__(
        self,
        *,
        token: str,
        conversation: ConversationService,
        flashcards: FlashcardService,
    ) -> None:
        self._bot = Bot(token=token)
        self._dispatcher = Dispatcher()
        self._conversation = conversation
        self._flashcards = flashcards

        self._dispatcher.message.register(self._handle_add_command, Command("add"))
        self._dispatcher.message.register(self._handle_flashcard_command, Command("flashcard"))
        self._dispatcher.message.register(self._handle_text_message, F.text)
        self._dispatcher.callback_query.register(self._handle_flashcard_callback, F.data.startswith(_FLASHCARD_CALLBACK_PREFIX))
        self._dispatcher.errors.register(self._handle_error)

    async def start(self) -> None:
        """Begin polling for Telegram updates."""
        logger.info("Starting Telegram polling...")
        await self._dispatcher.start_polling(self._bot)

    async def _handle_add_command(self, message: Message) -> None:
        """Process the /add command for creating flashcards."""
        user = message.from_user
        if user is None:
            logger.debug("Skipping /add without sender: %s", message.message_id)
            return

        profile = self._to_profile(user)
        words = self._extract_words(message.text or "")
        if not words:
            await self._safe_reply(
                message,
                "Добавьте слово после команды, например: /add привет",
            )
            return

        try:
            results = await self._flashcards.add_words(profile, words)
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Failed to add flashcards for user %s", profile.user_id)
            await self._safe_reply(message, "Не удалось добавить карточки. Попробуйте позже.")
            return

        response = self._format_add_results(results)
        await self._safe_reply(message, response)

    async def _handle_flashcard_command(self, message: Message) -> None:
        """Serve the next due flashcard to the learner."""
        user = message.from_user
        if user is None:
            logger.debug("Skipping /flashcard without sender: %s", message.message_id)
            return

        profile = self._to_profile(user)
        await self._flashcards.ensure_user(profile)

        try:
            study_card = await self._flashcards.get_next_card(user_id=profile.user_id)
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Failed to fetch next flashcard for user %s", profile.user_id)
            await self._safe_reply(message, "Не удалось получить карточку. Попробуйте позже.")
            return

        if study_card is None:
            await self._safe_reply(
                message,
                "Пока нет карточек для повторения. Добавьте новые через /add.",
            )
            return

        prompt, _ = self._flashcards.choose_prompt_side(study_card.card)
        side_label = "Слово" if prompt == study_card.card.source_text else "Перевод"
        text = (
            f"Колода: {study_card.deck_name}\n"
            f"{side_label}: {prompt}\n\n"
            "Нажмите «Показать полностью», чтобы увидеть ответ."
        )
        keyboard = self._reveal_keyboard(study_card.user_card_id)
        await self._safe_reply(message, text, reply_markup=keyboard)

    async def _handle_flashcard_callback(self, callback: CallbackQuery) -> None:
        """Dispatch flashcard-related callback actions."""
        data = callback.data or ""
        parts = data.split(":")
        if len(parts) < 2 or parts[0] != _FLASHCARD_CALLBACK_PREFIX:
            await callback.answer()
            return

        action = parts[1]
        try:
            if action == "show" and len(parts) >= 3:
                user_card_id = int(parts[2])
                await self._handle_flashcard_show(callback, user_card_id)
            elif action == "rate" and len(parts) >= 4:
                user_card_id = int(parts[2])
                rating = ReviewRating(parts[3])
                await self._handle_flashcard_rate(callback, user_card_id, rating)
            else:
                await callback.answer("Некорректный запрос.", show_alert=True)
        except ValueError:
            await callback.answer("Не удалось обработать действие.", show_alert=True)

    async def _handle_flashcard_show(self, callback: CallbackQuery, user_card_id: int) -> None:
        """Reveal the complete flashcard content."""
        user = callback.from_user
        if user is None:
            await callback.answer()
            return
        try:
            study_card = await self._flashcards.get_user_card(
                user_id=user.id,
                user_card_id=user_card_id,
            )
        except Exception:
            logger.exception("Failed to load flashcard %s for reveal", user_card_id)
            await callback.answer("Не удалось показать карточку.", show_alert=True)
            return

        text = self._render_full_card(study_card)
        keyboard = self._rating_keyboard(study_card.user_card_id)
        await self._safe_edit(callback, text, keyboard)
        await callback.answer()

    async def _handle_flashcard_rate(
        self,
        callback: CallbackQuery,
        user_card_id: int,
        rating: ReviewRating,
    ) -> None:
        """Apply the learner's feedback to the flashcard schedule."""
        user = callback.from_user
        if user is None:
            await callback.answer()
            return

        phrases = {
            ReviewRating.AGAIN: "Не знаю",
            ReviewRating.REVIEW: "Повторить",
            ReviewRating.EASY: "Знаю",
        }

        try:
            study_card = await self._flashcards.get_user_card(
                user_id=user.id,
                user_card_id=user_card_id,
            )
            await self._flashcards.record_review(
                user_id=user.id,
                user_card_id=user_card_id,
                rating=rating,
            )
        except Exception:
            logger.exception("Failed to record rating %s for user_card %s", rating, user_card_id)
            await callback.answer("Не удалось сохранить ответ.", show_alert=True)
            return

        text = f"{self._render_full_card(study_card)}\n\nОтметка: {phrases[rating]}"
        await self._safe_edit(callback, text, reply_markup=None)
        await callback.answer("Ответ сохранён.")

    async def _handle_text_message(self, message: Message) -> None:
        """Process inbound text messages."""
        user = message.from_user
        if user is None:
            logger.debug("Skipping message without sender: %s", message.message_id)
            return

        payload = UserMessagePayload(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            text=message.text or "",
        )

        try:
            reply = await self._conversation.handle_user_message(payload)
        except Exception as ex:  # pragma: no cover - defensive logging
            logger.exception("Failed to handle message %s", message.message_id)
            await self._safe_reply(message, "Произошла ошибка. Попробуйте ещё раз позже.")
            raise

        await self._safe_reply(message, reply)

    async def _safe_reply(self, message: Message, text: str, reply_markup=None) -> None:
        """Send a reply while guarding against Telegram API errors."""
        try:
            await message.answer(text, reply_markup=reply_markup)
        except TelegramBadRequest:
            logger.exception("Failed to send reply for message %s", message.message_id)
        except Exception:  # pragma: no cover - unexpected transport errors
            logger.exception("Unexpected error while replying to message %s", message.message_id)

    async def _safe_edit(self, callback: CallbackQuery, text: str, reply_markup=None) -> None:
        """Edit a message while handling Telegram errors gracefully."""
        msg = callback.message
        if msg is None:
            return
        # In group contexts or when the bot lacks access, Telegram returns
        # InaccessibleMessage which doesn't support edit operations.
        if not isinstance(msg, Message):
            return
        try:
            await msg.edit_text(text, reply_markup=reply_markup)
        except TelegramBadRequest:
            logger.exception("Failed to edit reply for callback %s", callback.id)
        except Exception:  # pragma: no cover - defensive branch
            logger.exception("Unexpected error while editing message %s", callback.id)

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

    @staticmethod
    def _to_profile(user: User) -> UserProfile:
        """Convert a Telegram user into a lightweight user profile."""
        return UserProfile(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )

    def _extract_words(self, text: str) -> list[str]:
        """Split a command payload into candidate words or phrases."""
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            return []
        payload = parts[1]
        tokens = _FLASHCARD_SPLIT_PATTERN.split(payload)
        return [token.strip() for token in tokens if token.strip()]

    @staticmethod
    def _format_add_results(results: list[FlashcardCreationResult]) -> str:
        """Format flashcard creation results for user feedback."""
        lines: list[str] = []
        for result in results:
            if result.error:
                lines.append(f"⚠️ {result.input_text}: {result.error}")
                continue

            if not result.card:
                lines.append(f"⚠️ {result.input_text}: карточка не сохранена.")
                continue

            base = f"{result.card.source_text} — {result.card.target_text}"
            if result.created_card:
                status = "добавлена новая карточка"
            elif result.linked_to_user:
                status = "карточка добавлена в вашу колоду"
            else:
                status = "карточка уже есть в вашей колоде"
            lines.append(f"✅ {base} ({status})")

        if not lines:
            return "Карточки не были добавлены."

        header = "Результат добавления карточек:"
        return "\n".join([header, *lines])

    @staticmethod
    def _reveal_keyboard(user_card_id: int):
        """Inline keyboard with a single button to reveal the card."""
        builder = InlineKeyboardBuilder()
        builder.button(
            text="Показать полностью",
            callback_data=f"{_FLASHCARD_CALLBACK_PREFIX}:show:{user_card_id}",
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def _rating_keyboard(user_card_id: int):
        """Inline keyboard offering spaced repetition ratings."""
        builder = InlineKeyboardBuilder()
        builder.button(
            text="Не знаю",
            callback_data=f"{_FLASHCARD_CALLBACK_PREFIX}:rate:{user_card_id}:{ReviewRating.AGAIN.value}",
        )
        builder.button(
            text="Повторить",
            callback_data=f"{_FLASHCARD_CALLBACK_PREFIX}:rate:{user_card_id}:{ReviewRating.REVIEW.value}",
        )
        builder.button(
            text="Знаю",
            callback_data=f"{_FLASHCARD_CALLBACK_PREFIX}:rate:{user_card_id}:{ReviewRating.EASY.value}",
        )
        builder.adjust(3)
        return builder.as_markup()

    @staticmethod
    def _render_full_card(card: StudyCard) -> str:
        """Render the full card content for display."""
        lines = [
            f"Колода: {card.deck_name}",
            f"Слово: {card.card.source_text}",
            f"Перевод: {card.card.target_text}",
            "",
            "Пример:",
            card.card.example_sentence,
            "",
            "Перевод примера:",
            card.card.example_translation,
        ]
        if card.card.part_of_speech:
            lines.insert(3, f"Часть речи: {card.card.part_of_speech}")
        return "\n".join(lines)
