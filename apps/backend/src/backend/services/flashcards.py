"""Flashcard orchestration service for deck and review management."""

from __future__ import annotations

import datetime as dt
import random
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from sqlalchemy.orm import selectinload

from .llm import FlashcardContent, FlashcardGenerator, LLMClient
from .storage.database import Database
from .storage.models import DeckRecord, UserCardRecord
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
    deck_id: int
    deck_name: str
    card: FlashcardData


@dataclass(frozen=True)
class DeckSummary:
    """Aggregated information about a user's deck."""

    deck_id: int
    slug: str
    name: str
    description: str | None
    card_count: int
    due_count: int
    created_at: dt.datetime


@dataclass(frozen=True)
class DeckCard:
    """Card information tied to a specific deck for the user."""

    user_card_id: int
    deck_id: int
    card: FlashcardData
    last_rating: str | None
    interval_minutes: int
    review_count: int
    next_review_at: dt.datetime
    last_reviewed_at: dt.datetime | None


class FlashcardService:
    """Coordinate flashcard creation, scheduling, and retrieval."""

    def __init__(
        self,
        *,
        database: Database,
        generator: FlashcardGenerator,
        llm: LLMClient,
        flashcard_repository: FlashcardRepository | None = None,
        user_repository: UserRepository | None = None,
        random_source: random.Random | None = None,
    ) -> None:
        self._database = database
        self._generator = generator
        self._llm = llm
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

    async def get_next_card(self, *, user_id: int, deck_id: int | None = None) -> StudyCard | None:
        """Return the next due card for the user, if any."""
        async with self._database.session() as session:
            record = await self._flashcards.fetch_next_due_card(session, user_id=user_id, deck_id=deck_id)
            if record is None:
                return None
            card_data = _to_flashcard_data(record.card)
            return StudyCard(
                user_card_id=record.id,
                deck_id=record.deck_id,
                deck_name=record.deck.name,
                card=card_data,
            )

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
                deck_id=record.deck_id,
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

    async def list_user_decks(self, profile: UserProfile) -> list[DeckSummary]:
        """Return all decks owned by the user."""
        async with self._database.session() as session:
            user = await self._get_or_create_user(session, profile)
            rows = await self._flashcards.list_decks(session, owner_id=user.id)
            return [
                DeckSummary(
                    deck_id=deck.id,
                    slug=deck.slug,
                    name=deck.name,
                    description=deck.description,
                    card_count=card_count,
                    due_count=due_count,
                    created_at=deck.created_at,
                )
                for deck, card_count, due_count in rows
            ]

    async def create_deck(
        self,
        profile: UserProfile,
        *,
        name: str,
        description: str | None = None,
    ) -> DeckSummary:
        """Create a new deck owned by the user."""
        if not name or not name.strip():
            raise ValueError("Название колоды не может быть пустым.")

        async with self._database.session() as session:
            user = await self._get_or_create_user(session, profile)
            deck = await self._flashcards.create_deck(
                session,
                owner_id=user.id,
                name=name.strip(),
                description=description,
            )
            await session.commit()
            return DeckSummary(
                deck_id=deck.id,
                slug=deck.slug,
                name=deck.name,
                description=deck.description,
                card_count=0,
                due_count=0,
                created_at=deck.created_at,
            )

    async def update_deck(
        self,
        profile: UserProfile,
        *,
        deck_id: int,
        name: str | None = None,
        description: str | None = None,
    ) -> DeckSummary:
        """Update an existing deck owned by the user."""
        async with self._database.session() as session:
            user = await self._get_or_create_user(session, profile)
            deck = await self._flashcards.update_deck(
                session,
                owner_id=user.id,
                deck_id=deck_id,
                name=name,
                description=description,
            )
            rows = await self._flashcards.list_decks(session, owner_id=user.id)
            await session.commit()
        for deck_row, card_count, due_count in rows:
            if deck_row.id == deck.id:
                return DeckSummary(
                    deck_id=deck_row.id,
                    slug=deck_row.slug,
                    name=deck_row.name,
                    description=deck_row.description,
                    card_count=card_count,
                    due_count=due_count,
                    created_at=deck_row.created_at,
                )
        raise ValueError("Колода не найдена.")

    async def delete_deck(self, profile: UserProfile, *, deck_id: int) -> None:
        """Remove a deck owned by the user."""
        async with self._database.session() as session:
            user = await self._get_or_create_user(session, profile)
            await self._flashcards.delete_deck(session, owner_id=user.id, deck_id=deck_id)
            await session.commit()

    async def list_deck_cards(
        self,
        profile: UserProfile,
        *,
        deck_id: int,
    ) -> list[DeckCard]:
        """Return cards in a deck for the user."""
        async with self._database.session() as session:
            user = await self._get_or_create_user(session, profile)
            deck = await self._require_deck(session, owner_id=user.id, deck_id=deck_id)
            records = await self._flashcards.list_deck_cards(
                session,
                owner_id=user.id,
                deck_id=deck.id,
            )
            await session.commit()
        return [
            DeckCard(
                user_card_id=record.id,
                deck_id=record.deck_id,
                card=_to_flashcard_data(record.card),
                last_rating=record.last_rating,
                interval_minutes=record.interval_minutes,
                review_count=record.review_count,
                next_review_at=record.next_review_at,
                last_reviewed_at=record.last_reviewed_at,
            )
            for record in records
        ]

    async def create_card_for_deck(
        self,
        profile: UserProfile,
        *,
        deck_id: int,
        prompt_text: str,
    ) -> FlashcardCreationResult:
        """Generate or reuse a card and attach it to the specified deck."""
        cleaned = prompt_text.strip()
        if not cleaned:
            raise ValueError("Текст карточки не может быть пустым.")

        async with self._database.session() as session:
            user = await self._get_or_create_user(session, profile)
            deck = await self._require_deck(session, owner_id=user.id, deck_id=deck_id)

            normalized_prompt = self._flashcards.normalize_text(cleaned)
            card = await self._flashcards.get_card_by_normalized(session, normalized_source=normalized_prompt)
            reused_existing = card is not None

            if card is None:
                card = await self._flashcards.get_card_by_normalized_target(
                    session,
                    normalized_target=normalized_prompt,
                )
                reused_existing = card is not None

            if card is None:
                generated = await self._generator.generate_flashcard(prompt_word=cleaned)
                card = await self._flashcards.create_card(
                    session,
                    source_text=generated.source_text or cleaned,
                    target_text=generated.target_text,
                    example_sentence=generated.example_sentence,
                    example_translation=generated.example_translation,
                    part_of_speech=generated.part_of_speech,
                    extra=generated.extra,
                )

            user_card, created_link = await self._flashcards.ensure_user_card(
                session,
                user_id=user.id,
                deck_id=deck.id,
                card_id=card.id,
            )
            await session.commit()

        return FlashcardCreationResult(
            input_text=cleaned,
            created_card=not reused_existing,
            reused_existing_card=reused_existing,
            linked_to_user=created_link,
            card=_to_flashcard_data(card),
            user_card_id=user_card.id,
            message=None,
            error=None,
        )

    async def remove_card_from_deck(
        self,
        profile: UserProfile,
        *,
        deck_id: int,
        user_card_id: int,
    ) -> None:
        """Detach the specified user card from the deck."""
        async with self._database.session() as session:
            user = await self._get_or_create_user(session, profile)
            await self._require_deck(session, owner_id=user.id, deck_id=deck_id)
            await self._flashcards.remove_user_card(
                session,
                owner_id=user.id,
                deck_id=deck_id,
                user_card_id=user_card_id,
            )
            await session.commit()

    async def generate_cards_for_deck(
        self,
        profile: UserProfile,
        *,
        deck_id: int,
        prompt: str,
        count: int = 15,
    ) -> list[FlashcardCreationResult]:
        """Generate multiple flashcards via LLM based on prompt and add to deck."""
        cleaned_prompt = prompt.strip()
        if not cleaned_prompt:
            raise ValueError("Промпт не может быть пустым.")

        # Generate a list of words/phrases based on the prompt using LLM
        generation_prompt = (
            f"You are a Modern Greek language teacher for Russian-speaking students.\n"
            f"Generate exactly {count} useful Modern Greek words or short phrases related to the topic: '{cleaned_prompt}'.\n"
            f"These words should be practical and commonly used in everyday Greek.\n"
            f"Focus on variety: include nouns, verbs, adjectives, and useful expressions.\n"
            f"Return ONLY the Greek words (in Greek alphabet), one per line.\n"
            f"Do NOT include:\n"
            f"- Translations\n"
            f"- Numbering\n"
            f"- Latin transliterations\n"
            f"- Any explanations or additional text\n"
            f"Example output format:\n"
            f"καλημέρα\n"
            f"φαγητό\n"
            f"ταξίδι"
        )

        # Use the LLM client to generate words
        response = await self._llm.generate_reply(user_message=generation_prompt)
        words = [line.strip() for line in response.strip().split('\n') if line.strip()]

        # Limit to requested count
        words = words[:count]

        if not words:
            raise ValueError("Не удалось сгенерировать слова.")

        # Generate flashcards for each word
        results: list[FlashcardCreationResult] = []
        for word in words:
            try:
                result = await self.create_card_for_deck(
                    profile,
                    deck_id=deck_id,
                    prompt_text=word,
                )
                results.append(result)
            except Exception:
                # Skip words that fail, but continue with others
                continue

        return results

    async def _get_or_create_user(self, session, profile: UserProfile):
        """Ensure a user record exists and return it."""
        return await self._users.upsert_user(
            session,
            user_id=profile.user_id,
            username=profile.username,
            first_name=profile.first_name,
            last_name=profile.last_name,
        )

    async def _require_deck(
        self,
        session,
        *,
        owner_id: int,
        deck_id: int,
    ) -> DeckRecord:
        """Fetch the deck for the user or raise a ValueError."""
        deck = await self._flashcards.get_deck(
            session,
            owner_id=owner_id,
            deck_id=deck_id,
        )
        if deck is None:
            raise ValueError("Колода не найдена.")
        return deck


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
