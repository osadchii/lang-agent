"""Telegram bot runner built on top of aiogram."""

from __future__ import annotations

import asyncio
import re
import time
from contextlib import suppress

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatAction, ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, ErrorEvent, Message, Update, User
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..logger_factory import get_logger
from .conversation import ConversationService, UserMessagePayload
from .flashcards import FlashcardCreationResult, FlashcardService, ReviewRating, StudyCard, TranslationResult, UserProfile

logger = get_logger(__name__)

_FLASHCARD_CALLBACK_PREFIX = "flashcard"
_ADD_CARD_CALLBACK_PREFIX = "addcard"
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
        self._token = token
        self._loggers_reconfigured = False  # Track if we've reconfigured aiogram loggers

        self._dispatcher.message.register(self._handle_add_command, Command("add"))
        self._dispatcher.message.register(self._handle_translate_command, Command("translate"))
        self._dispatcher.message.register(self._handle_flashcard_command, Command("flashcard"))
        self._dispatcher.message.register(self._handle_create_deck_command, Command("create_deck"))
        self._dispatcher.message.register(self._handle_list_decks_command, Command("list_decks"))
        self._dispatcher.message.register(self._handle_select_deck_command, Command("select_deck"))
        self._dispatcher.message.register(self._handle_delete_deck_command, Command("delete_deck"))
        self._dispatcher.message.register(self._handle_text_message, F.text)
        self._dispatcher.callback_query.register(self._handle_flashcard_callback, F.data.startswith(_FLASHCARD_CALLBACK_PREFIX))
        self._dispatcher.callback_query.register(self._handle_add_card_callback, F.data.startswith(_ADD_CARD_CALLBACK_PREFIX))
        self._dispatcher.errors.register(self._handle_error)

    @property
    def bot(self) -> Bot:
        """Expose the bot instance for external use."""
        return self._bot

    async def set_webhook(self, webhook_url: str) -> None:
        """Configure Telegram webhook."""
        logger.info("Setting webhook to %s", webhook_url)
        await self._bot.set_webhook(
            url=webhook_url,
            allowed_updates=self._dispatcher.resolve_used_update_types(),
            drop_pending_updates=True,
        )
        logger.info("Webhook set successfully")

    async def delete_webhook(self) -> None:
        """Remove Telegram webhook."""
        logger.info("Deleting webhook")
        await self._bot.delete_webhook(drop_pending_updates=True)

    async def process_update(self, update: Update) -> None:
        """Process a single update from Telegram webhook."""
        # Log BEFORE reconfiguration to test if logging works at all
        logger.info("Processing Telegram update: update_id=%s", update.update_id)

        # Reconfigure all loggers on first update to ensure aiogram loggers work
        if not self._loggers_reconfigured:
            from ..logger_factory import reconfigure_all_loggers
            reconfigure_all_loggers()
            self._loggers_reconfigured = True
            logger.info("Reconfigured all loggers (including aiogram) for proper propagation")

        await self._dispatcher.feed_update(bot=self._bot, update=update)

    async def _handle_add_command(self, message: Message) -> None:
        """Process the /add command for creating flashcards."""
        start_time = time.perf_counter()
        user = message.from_user
        if user is None:
            logger.debug("Skipping /add without sender: %s", message.message_id)
            return

        profile = self._to_profile(user)
        words = self._extract_words(message.text or "")

        logger.info(
            "Bot /add command: user_id=%d, words_count=%d",
            user.id,
            len(words),
        )

        if not words:
            await self._safe_reply(
                message,
                "Добавьте слово после команды, например: /add привет",
            )
            return

        try:
            results = await self._flashcards.add_words(profile, words)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "Bot /add command processed: user_id=%d, duration_ms=%.2f, results=%d",
                user.id,
                elapsed_ms,
                len(results),
            )
        except Exception:  # pragma: no cover - defensive logging
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "Bot /add command failed: user_id=%d, duration_ms=%.2f",
                user.id,
                elapsed_ms,
            )
            await self._safe_reply(message, "Не удалось добавить карточки. Попробуйте позже.")
            return

        response = self._format_add_results(results)
        await self._safe_reply(message, response)

    async def _handle_translate_command(self, message: Message) -> None:
        """Process the /translate command for translating words without adding them."""
        start_time = time.perf_counter()
        user = message.from_user
        if user is None:
            logger.debug("Skipping /translate without sender: %s", message.message_id)
            return

        profile = self._to_profile(user)
        text = message.text or ""
        parts = text.split(maxsplit=1)

        if len(parts) < 2:
            await self._safe_reply(
                message,
                "Добавьте слово после команды, например: /translate привет",
            )
            return

        word = parts[1].strip()
        logger.info("Bot /translate command: user_id=%d, word=%s", user.id, word)

        try:
            result = await self._flashcards.translate_word(profile, word)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "Bot /translate command processed: user_id=%d, duration_ms=%.2f",
                user.id,
                elapsed_ms,
            )

            # Format translation result
            response = self._format_translation_result(result)

            # Add button if word is not in user's decks
            keyboard = None
            if not result.already_in_decks:
                keyboard = self._add_card_keyboard(word, result.card_content.target_text)

            await self._safe_reply(message, response, reply_markup=keyboard)
        except Exception:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "Bot /translate command failed: user_id=%d, duration_ms=%.2f",
                user.id,
                elapsed_ms,
            )
            await self._safe_reply(message, "Не удалось перевести слово. Попробуйте позже.")

    async def _handle_flashcard_command(self, message: Message) -> None:
        """Serve the next due flashcard to the learner."""
        start_time = time.perf_counter()
        user = message.from_user
        if user is None:
            logger.debug("Skipping /flashcard without sender: %s", message.message_id)
            return

        profile = self._to_profile(user)
        await self._flashcards.ensure_user(profile)

        logger.info("Bot /flashcard command: user_id=%d", user.id)

        try:
            study_card = await self._flashcards.get_next_card(user_id=profile.user_id)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            if study_card is None:
                logger.info(
                    "Bot /flashcard no cards: user_id=%d, duration_ms=%.2f",
                    user.id,
                    elapsed_ms,
                )
                await self._safe_reply(
                    message,
                    "Пока нет карточек для повторения. Добавьте новые через /add.",
                )
                return

            logger.info(
                "Bot /flashcard served: user_id=%d, duration_ms=%.2f, card_id=%d",
                user.id,
                elapsed_ms,
                study_card.user_card_id,
            )
        except Exception:  # pragma: no cover - defensive logging
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "Bot /flashcard failed: user_id=%d, duration_ms=%.2f",
                user.id,
                elapsed_ms,
            )
            await self._safe_reply(message, "Не удалось получить карточку. Попробуйте позже.")
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

    async def _handle_add_card_callback(self, callback: CallbackQuery) -> None:
        """Handle adding a card to user's decks with LLM-based deck selection."""
        data = callback.data or ""
        parts = data.split(":", maxsplit=2)
        if len(parts) < 3 or parts[0] != _ADD_CARD_CALLBACK_PREFIX:
            await callback.answer()
            return

        word = parts[1]
        translation = parts[2]
        user = callback.from_user
        if user is None:
            await callback.answer()
            return

        profile = self._to_profile(user)
        logger.info("Bot add card callback: user_id=%d, word=%s", user.id, word)

        try:
            result = await self._flashcards.add_word_with_deck_selection(
                profile,
                word,
                translation,
            )

            if result.error:
                await callback.answer(f"Ошибка: {result.error}", show_alert=True)
                return

            # Get deck info to show in confirmation
            if result.card:
                deck_info = ""
                try:
                    decks = await self._flashcards.list_user_decks(profile)
                    # Find which deck the card was added to
                    # We need to get the deck from the result somehow
                    # For now, just show success message
                    deck_info = ""
                except Exception:
                    pass

                success_message = (
                    f"✅ Карточка добавлена в колоду!\n"
                    f"{result.card.source_text} — {result.card.target_text}"
                )
                await callback.answer(success_message)

                # Update the message to remove the button
                msg = callback.message
                if msg and isinstance(msg, Message):
                    try:
                        await msg.edit_reply_markup(reply_markup=None)
                    except Exception:
                        pass  # Ignore if we can't edit the message
            else:
                await callback.answer("Карточка добавлена!", show_alert=False)

        except Exception:
            logger.exception("Bot add card callback failed: user_id=%d", user.id)
            await callback.answer("Не удалось добавить карточку.", show_alert=True)

    async def _handle_create_deck_command(self, message: Message) -> None:
        """Process the /create_deck command for creating a new deck."""
        user = message.from_user
        if user is None:
            logger.debug("Skipping /create_deck without sender: %s", message.message_id)
            return

        profile = self._to_profile(user)
        text = message.text or ""
        parts = text.split(maxsplit=1)

        if len(parts) < 2 or not parts[1].strip():
            await self._safe_reply(
                message,
                "Добавьте название колоды после команды, например: /create_deck Греческий для путешествий",
            )
            return

        deck_name = parts[1].strip()
        logger.info("Bot /create_deck command: user_id=%d, deck_name=%s", user.id, deck_name)

        try:
            deck = await self._flashcards.create_deck(profile, name=deck_name)
            # Automatically set as active deck
            await self._flashcards.set_active_deck(profile, deck_id=deck.deck_id)
            await self._safe_reply(
                message,
                f"Колода «{deck.name}» успешно создана и установлена как активная.",
            )
        except Exception:
            logger.exception("Bot /create_deck failed: user_id=%d", user.id)
            await self._safe_reply(message, "Не удалось создать колоду. Попробуйте позже.")

    async def _handle_list_decks_command(self, message: Message) -> None:
        """Process the /list_decks command to show all user decks."""
        user = message.from_user
        if user is None:
            logger.debug("Skipping /list_decks without sender: %s", message.message_id)
            return

        profile = self._to_profile(user)
        logger.info("Bot /list_decks command: user_id=%d", user.id)

        try:
            decks = await self._flashcards.list_user_decks(profile)
            active_deck = await self._flashcards.get_active_deck(profile)

            if not decks:
                await self._safe_reply(message, "У вас пока нет колод. Создайте колоду с помощью /create_deck.")
                return

            lines = ["Ваши колоды:\n"]
            for deck in decks:
                active_marker = " ✓ (активная)" if active_deck and deck.deck_id == active_deck.deck_id else ""
                lines.append(
                    f"• ID: {deck.deck_id} | <b>{deck.name}</b>{active_marker}\n"
                    f"  Карточек: {deck.card_count} | К повторению: {deck.due_count}"
                )

            lines.append(
                "\n\nДля выбора активной колоды используйте:\n/select_deck [ID]\n\n"
                "Для удаления колоды используйте:\n/delete_deck [ID]"
            )
            await self._safe_reply(message, "\n".join(lines))
        except Exception:
            logger.exception("Bot /list_decks failed: user_id=%d", user.id)
            await self._safe_reply(message, "Не удалось получить список колод. Попробуйте позже.")

    async def _handle_select_deck_command(self, message: Message) -> None:
        """Process the /select_deck command to set active deck."""
        user = message.from_user
        if user is None:
            logger.debug("Skipping /select_deck without sender: %s", message.message_id)
            return

        profile = self._to_profile(user)
        text = message.text or ""
        parts = text.split()

        if len(parts) < 2:
            await self._safe_reply(
                message,
                "Укажите ID колоды после команды, например: /select_deck 1\n\n"
                "Посмотреть список колод: /list_decks",
            )
            return

        try:
            deck_id = int(parts[1])
        except ValueError:
            await self._safe_reply(message, "ID колоды должен быть числом.")
            return

        logger.info("Bot /select_deck command: user_id=%d, deck_id=%d", user.id, deck_id)

        try:
            await self._flashcards.set_active_deck(profile, deck_id=deck_id)
            deck = await self._flashcards.get_active_deck(profile)
            if deck:
                await self._safe_reply(
                    message,
                    f"Колода «{deck.name}» установлена как активная.\n"
                    f"Карточек: {deck.card_count} | К повторению: {deck.due_count}",
                )
            else:
                await self._safe_reply(message, "Колода установлена как активная.")
        except ValueError as exc:
            await self._safe_reply(message, str(exc))
        except Exception:
            logger.exception("Bot /select_deck failed: user_id=%d", user.id)
            await self._safe_reply(message, "Не удалось выбрать колоду. Попробуйте позже.")

    async def _handle_delete_deck_command(self, message: Message) -> None:
        """Process the /delete_deck command to remove a deck."""
        user = message.from_user
        if user is None:
            logger.debug("Skipping /delete_deck without sender: %s", message.message_id)
            return

        profile = self._to_profile(user)
        text = message.text or ""
        parts = text.split()

        if len(parts) < 2:
            await self._safe_reply(
                message,
                "Укажите ID колоды после команды, например: /delete_deck 1\n\n"
                "Посмотреть список колод: /list_decks",
            )
            return

        try:
            deck_id = int(parts[1])
        except ValueError:
            await self._safe_reply(message, "ID колоды должен быть числом.")
            return

        logger.info("Bot /delete_deck command: user_id=%d, deck_id=%d", user.id, deck_id)

        try:
            await self._flashcards.delete_deck(profile, deck_id=deck_id)
            await self._safe_reply(message, "Колода успешно удалена.")
        except ValueError as exc:
            await self._safe_reply(message, str(exc))
        except Exception:
            logger.exception("Bot /delete_deck failed: user_id=%d", user.id)
            await self._safe_reply(message, "Не удалось удалить колоду. Попробуйте позже.")

    async def _handle_text_message(self, message: Message) -> None:
        """Process inbound text messages."""
        start_time = time.perf_counter()
        user = message.from_user
        if user is None:
            logger.debug("Skipping message without sender: %s", message.message_id)
            return

        message_text = message.text or ""
        profile = self._to_profile(user)

        logger.info(
            "Bot message received: user_id=%d, username=%s, message_length=%d",
            user.id,
            user.username or "unknown",
            len(message_text),
        )

        # Check if message is a single word (for auto-translation)
        stripped_text = message_text.strip()
        if self._is_single_word(stripped_text):
            logger.info("Bot auto-translating single word: user_id=%d, word=%s", user.id, stripped_text)
            try:
                result = await self._flashcards.translate_word(profile, stripped_text)
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                logger.info(
                    "Bot auto-translation processed: user_id=%d, duration_ms=%.2f",
                    user.id,
                    elapsed_ms,
                )

                # Format translation result
                response = self._format_translation_result(result)

                # Add button if word is not in user's decks
                keyboard = None
                if not result.already_in_decks:
                    keyboard = self._add_card_keyboard(stripped_text, result.card_content.target_text)

                await self._safe_reply(message, response, reply_markup=keyboard)
                return
            except Exception:
                # If translation fails, fall back to conversation handler
                logger.info("Bot auto-translation failed, falling back to conversation: user_id=%d", user.id)

        # Default conversation handler
        payload = UserMessagePayload(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            text=message_text,
        )

        chat = message.chat
        chat_id = chat.id if chat else None
        typing_task = None

        if chat_id is not None:
            typing_task = asyncio.create_task(self._typing_indicator(chat_id))

        try:
            reply = await self._conversation.handle_user_message(payload)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "Bot message processed: user_id=%d, duration_ms=%.2f, reply_length=%d",
                user.id,
                elapsed_ms,
                len(reply),
            )
        except Exception:  # pragma: no cover - defensive logging
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "Bot message failed: user_id=%d, duration_ms=%.2f",
                user.id,
                elapsed_ms,
            )
            await self._safe_reply(message, "Произошла ошибка. Попробуйте ещё раз позже.")
            raise
        finally:
            if typing_task is not None:
                typing_task.cancel()
                with suppress(asyncio.CancelledError):
                    await typing_task

        await self._safe_reply(message, reply)

    async def _typing_indicator(self, chat_id: int) -> None:
        """Periodically send 'typing' chat actions while awaiting a response."""
        try:
            while True:
                try:
                    await self._bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
                except TelegramBadRequest:
                    logger.debug("Failed to send typing action for chat_id=%s", chat_id)
                    return
                except Exception:  # pragma: no cover - defensive logging
                    logger.exception("Unexpected error while sending typing action for chat_id=%s", chat_id)
                    return
                await asyncio.sleep(4)
        except asyncio.CancelledError:
            return

    async def _safe_reply(self, message: Message, text: str, reply_markup=None) -> None:
        """Send a reply while guarding against Telegram API errors."""
        try:
            await message.answer(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        except TelegramBadRequest as exc:
            error_text = str(exc).lower()
            if "parse entities" in error_text or "can't parse" in error_text:
                logger.warning(
                    "HTML formatting failed for message %s, retrying without parse mode",
                    message.message_id,
                    exc_info=exc,
                )
                with suppress(TelegramBadRequest):
                    await message.answer(text, reply_markup=reply_markup)
                return
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
            await msg.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        except TelegramBadRequest as exc:
            error_text = str(exc).lower()
            if "parse entities" in error_text or "can't parse" in error_text:
                logger.warning(
                    "HTML formatting failed while editing message %s, retrying without parse mode",
                    callback.id,
                    exc_info=exc,
                )
                with suppress(TelegramBadRequest):
                    await msg.edit_text(text, reply_markup=reply_markup)
                return
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

    @staticmethod
    def _format_translation_result(result: TranslationResult) -> str:
        """Format translation result for display."""
        content = result.card_content
        lines = [
            f"<b>Слово:</b> {content.source_text}",
            f"<b>Перевод:</b> {content.target_text}",
        ]

        if content.part_of_speech:
            lines.append(f"<b>Часть речи:</b> {content.part_of_speech}")

        lines.extend([
            "",
            "<b>Пример:</b>",
            content.example_sentence,
            "",
            "<b>Перевод примера:</b>",
            content.example_translation,
        ])

        if result.already_in_decks:
            lines.append("\n<i>Это слово уже есть в ваших колодах.</i>")

        return "\n".join(lines)

    @staticmethod
    def _add_card_keyboard(word: str, translation: str):
        """Inline keyboard with button to add card to deck."""
        builder = InlineKeyboardBuilder()
        # Encode word and translation in callback data
        # Format: addcard:word:translation
        builder.button(
            text="➕ Добавить в карточки",
            callback_data=f"{_ADD_CARD_CALLBACK_PREFIX}:{word}:{translation}",
        )
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def _is_single_word(text: str) -> bool:
        """Check if the text is a single word suitable for translation."""
        # Remove leading/trailing whitespace
        stripped = text.strip()

        # Empty text is not a single word
        if not stripped:
            return False

        # Check if it contains spaces (multi-word)
        if ' ' in stripped:
            return False

        # Check if it's too long to be a single word (likely a sentence)
        if len(stripped) > 50:
            return False

        # Check if it contains sentence-ending punctuation
        if any(char in stripped for char in '.!?'):
            return False

        return True
