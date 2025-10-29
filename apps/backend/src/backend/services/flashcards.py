"""Flashcard orchestration service for deck and review management."""

from __future__ import annotations

import datetime as dt
import random
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from sqlalchemy.orm import selectinload

from .llm import FlashcardContent, FlashcardGenerator
from .storage.database import Database
from .storage.models import UserCardRecord
from .storage.repositories import FlashcardRepository, UserRepository


@dataclass(frozen=True)
class UserProfile:
    """Minimal user profile information required for flashcard operations."""

    user_id: int
    username: str | None
    first_name: str | None
    last_name: str | None


@dataclass(frozen=True)
class FlashcardData:
    """Representation of a flashcard ready for presentation."""

    card_id: int
    source_text: str
    target_text: str
    example_sentence: str
    example_translation: str
    part_of_speech: str | None


@dataclass(frozen=True)
class FlashcardCreationResult:
    """Metadata describing the outcome of a card creation attempt."""

    input_text: str
    created_card: bool
    linked_to_user: bool
    card: FlashcardData | None
    reused_existing_card: bool
    user_card_id: int | None
    message: str | None = None
    error: str | None = None


class ReviewRating(str, Enum):
    """Possible review outcomes selected by the learner."""

    AGAIN = "again"  # "Не знаю"
    REVIEW = "review"  # "Повторить"
    EASY = "easy"  # "Знаю"


@dataclass(frozen=True)
class StudyCard:
    """A flashcard ready to be shown to the learner."""

    user_card_id: int
    deck_name: str
    card: FlashcardData


class FlashcardService:
    """Coordinate flashcard creation, scheduling, and retrieval."""

    def __init__(
        self,
        *,
        database: Database,
        generator: FlashcardGenerator,
        flashcard_repository: FlashcardRepository | None = None,
        user_repository: UserRepository | None = None,
        random_source: random.Random | None = None,
    ) -> None:
        self._database = database
        self._generator = generator
        self._flashcards = flashcard_repository or FlashcardRepository()
        self._users = user_repository or UserRepository()
        self._random = random_source or random.Random()

    async def add_words(
        self,
        profile: UserProfile,
        words: Sequence[str],
    ) -> list[FlashcardCreationResult]:
        """Create or reuse flashcards for the supplied words and link them to the user."""
        cleaned_words = [word.strip() for word in words if word and word.strip()]
        if not cleaned_words:
            return [
                FlashcardCreationResult(
                    input_text="",
                    created_card=False,
                    linked_to_user=False,
                    card=None,
                    reused_existing_card=False,
                    user_card_id=None,
                    message=None,
                    error="Не удалось распознать слова для добавления.",
                )
            ]

        outcomes: list[FlashcardCreationResult] = []
        async with self._database.session() as session:
            user = await self._users.upsert_user(
                session,
                user_id=profile.user_id,
                username=profile.username,
                first_name=profile.first_name,
                last_name=profile.last_name,
            )
            deck = await self._flashcards.ensure_deck(session, owner_id=user.id)

            for word in cleaned_words:
                normalized = self._flashcards.normalize_text(word)
                try:
                    card = await self._flashcards.get_card_by_normalized(session, normalized_source=normalized)
                    reused_existing = card is not None

                    if card is None:
                        generated = await self._generator.generate_flashcard(prompt_word=word)
                        card = await self._flashcards.create_card(
                            session,
                            source_text=generated.source_text or word,
                            target_text=generated.target_text,
                            example_sentence=generated.example_sentence,
                            example_translation=generated.example_translation,
                            part_of_speech=generated.part_of_speech,
                            extra=generated.extra,
                        )
                    user_card, created_user_link = await self._flashcards.ensure_user_card(
                        session,
                        user_id=user.id,
                        deck_id=deck.id,
                        card_id=card.id,
                    )

                    outcomes.append(
                        FlashcardCreationResult(
                            input_text=word,
                            created_card=not reused_existing,
                            reused_existing_card=reused_existing,
                            linked_to_user=created_user_link,
                            card=_to_flashcard_data(card),
                            user_card_id=user_card.id,
                            message=None,
                            error=None,
                        )
                    )
                except Exception as exc:
                    outcomes.append(
                        FlashcardCreationResult(
                            input_text=word,
                            created_card=False,
                            reused_existing_card=False,
                            linked_to_user=False,
                            card=None,
                            user_card_id=None,
                            message=None,
                            error=str(exc),
                        )
                    )

            await session.commit()

        return outcomes

    async def ensure_user(self, profile: UserProfile) -> None:
        """Guarantee that a user record exists."""
        async with self._database.session() as session:
            await self._users.upsert_user(
                session,
                user_id=profile.user_id,
                username=profile.username,
                first_name=profile.first_name,
                last_name=profile.last_name,
            )
            await session.commit()

    async def get_next_card(self, *, user_id: int) -> StudyCard | None:
        """Return the next due card for the user, if any."""
        async with self._database.session() as session:
            record = await self._flashcards.fetch_next_due_card(session, user_id=user_id)
            if record is None:
                return None
            card_data = _to_flashcard_data(record.card)
            return StudyCard(user_card_id=record.id, deck_name=record.deck.name, card=card_data)

    async def get_user_card(self, *, user_id: int, user_card_id: int) -> StudyCard:
        """Load a specific user-card record ensuring ownership."""
        async with self._database.session() as session:
            record = await session.get(
                UserCardRecord,
                user_card_id,
                options=(
                    selectinload(UserCardRecord.card),
                    selectinload(UserCardRecord.deck),
                ),
            )
            if record is None or record.user_id != user_id:
                raise ValueError("Карточка не найдена для этого пользователя.")
            return StudyCard(
                user_card_id=record.id,
                deck_name=record.deck.name,
                card=_to_flashcard_data(record.card),
            )

    async def record_review(
        self,
        *,
        user_id: int,
        user_card_id: int,
        rating: ReviewRating,
    ) -> None:
        """Apply spaced repetition scheduling updates based on the user's rating."""
        async with self._database.session() as session:
            record = await session.get(UserCardRecord, user_card_id)
            if record is None or record.user_id != user_id:
                raise ValueError("Карточка не найдена для этого пользователя.")

            interval = self._calculate_next_interval(record.interval_minutes, record.review_count, rating)
            await self._flashcards.schedule_review(
                session,
                record,
                rating=rating.value,
                interval_minutes=interval,
            )
            await session.commit()

    def choose_prompt_side(self, card: FlashcardData) -> tuple[str, str]:
        """Randomly select which side of the card to present first."""
        if self._random.random() < 0.5:
            prompt = card.source_text
            hidden = card.target_text
        else:
            prompt = card.target_text
            hidden = card.source_text
        return prompt, hidden

    @staticmethod
    def _calculate_next_interval(
        previous_interval: int,
        review_count: int,
        rating: ReviewRating,
    ) -> int:
        """Determine the next review interval (minutes) using a simple spaced repetition heuristic."""
        base_again = 10  # minutes
        base_review = 12 * 60  # 12 hours
        base_easy = 3 * 24 * 60  # 3 days

        if rating is ReviewRating.AGAIN:
            return base_again

        previous = max(previous_interval, base_again)
        if rating is ReviewRating.REVIEW:
            if review_count == 0:
                return base_review
            return max(base_review, int(previous * 1.5))

        # EASY
        if review_count == 0:
            return base_easy
        return max(base_easy, int(previous * 2.5))


def _to_flashcard_data(card) -> FlashcardData:
    """Convert a CardRecord into a FlashcardData payload."""
    return FlashcardData(
        card_id=card.id,
        source_text=card.source_text,
        target_text=card.target_text,
        example_sentence=card.example_sentence,
        example_translation=card.example_translation,
        part_of_speech=card.part_of_speech,
    )
