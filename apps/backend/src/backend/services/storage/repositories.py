"""Repositories encapsulating database access patterns."""

from __future__ import annotations

import datetime as dt
from typing import Optional

import re

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from .models import (
    CardRecord,
    DeckRecord,
    MessageDirection,
    MessageRecord,
    UserCardRecord,
    UserRecord,
)


class UserRepository:
    """Persist and retrieve Telegram user records."""

    async def upsert_user(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        username: Optional[str],
        first_name: Optional[str],
        last_name: Optional[str],
    ) -> UserRecord:
        """Create a new user if not exists, otherwise update profile fields."""
        record = await session.get(UserRecord, user_id)
        if record is None:
            record = UserRecord(
                id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
            session.add(record)
        else:
            record.username = username
            record.first_name = first_name
            record.last_name = last_name

        await session.flush()
        return record

    async def get_user(
        self,
        session: AsyncSession,
        *,
        user_id: int,
    ) -> UserRecord | None:
        """Fetch a user by ID."""
        return await session.get(UserRecord, user_id)

    async def set_active_deck(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        deck_id: int | None,
    ) -> UserRecord:
        """Set the active deck for a user."""
        record = await session.get(UserRecord, user_id)
        if record is None:
            raise ValueError("Пользователь не найден.")
        record.active_deck_id = deck_id
        await session.flush()
        return record

    async def get_active_deck_id(
        self,
        session: AsyncSession,
        *,
        user_id: int,
    ) -> int | None:
        """Get the active deck ID for a user."""
        record = await session.get(UserRecord, user_id)
        if record is None:
            return None
        return record.active_deck_id


class MessageRepository:
    """Store inbound and outbound message logs."""

    async def log_message(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        direction: MessageDirection | str,
        content: str,
        model: Optional[str] = None,
    ) -> MessageRecord:
        """Persist a message tied to a user."""
        direction_member = self._normalize_direction(direction)
        normalized_model = model.strip() if isinstance(model, str) else model
        model_value = normalized_model or "unknown"
        record = MessageRecord(
            user_id=user_id,
            direction=direction_member,
            content=content,
            model=model_value,
        )
        session.add(record)
        await session.flush()
        return record

    async def fetch_recent_messages(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        limit: int = 10,
    ) -> list[MessageRecord]:
        """Retrieve recent messages for conversational context."""
        stmt = (
            select(MessageRecord)
            .where(MessageRecord.user_id == user_id)
            .order_by(MessageRecord.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        records = list(result.scalars())
        records.reverse()
        return records

    @staticmethod
    def _normalize_direction(direction: MessageDirection | str) -> MessageDirection:
        """Coerce arbitrary direction input into the enum value."""
        if isinstance(direction, MessageDirection):
            return direction
        if isinstance(direction, str):
            lowered = direction.lower()
            try:
                return MessageDirection(lowered)
            except ValueError:
                try:
                    return MessageDirection[direction.upper()]
                except KeyError as exc:  # pragma: no cover - defensive branch
                    raise ValueError(f"Unsupported message direction: {direction}") from exc
        raise TypeError(f"Unsupported message direction type: {type(direction)!r}")


class FlashcardRepository:
    """Persist decks, cards, and user study metadata."""

    DEFAULT_DECK_SLUG = "default"
    DEFAULT_DECK_NAME = "Основная колода"

    async def ensure_deck(
        self,
        session: AsyncSession,
        *,
        owner_id: int,
        slug: str | None = None,
        name: str | None = None,
    ) -> DeckRecord:
        """Fetch an existing deck by slug/owner or create it."""
        normalized_slug = (slug or self.DEFAULT_DECK_SLUG).strip().casefold()
        normalized_name = name.strip() if isinstance(name, str) and name.strip() else self.DEFAULT_DECK_NAME

        deck_stmt: Select[tuple[DeckRecord]] = select(DeckRecord).where(
            DeckRecord.owner_id == owner_id,
            DeckRecord.slug == normalized_slug,
        )
        deck = await session.execute(deck_stmt)
        record = deck.scalar_one_or_none()
        if record is None:
            record = DeckRecord(owner_id=owner_id, slug=normalized_slug, name=normalized_name)
            session.add(record)
            await session.flush()
        return record

    async def list_decks(
        self,
        session: AsyncSession,
        *,
        owner_id: int,
        as_of: dt.datetime | None = None,
    ) -> list[tuple[DeckRecord, int, int]]:
        """Return decks owned by the user along with card counts and due counts."""
        reference = as_of or dt.datetime.now(dt.timezone.utc)
        stmt = (
            select(
                DeckRecord,
                func.count(UserCardRecord.id).label("card_count"),
                func.coalesce(
                    func.sum(
                        case(
                            (UserCardRecord.next_review_at <= reference, 1),
                            else_=0,
                        )
                    ),
                    0,
                ).label("due_count"),
            )
            .outerjoin(
                UserCardRecord,
                and_(
                    UserCardRecord.deck_id == DeckRecord.id,
                    UserCardRecord.user_id == owner_id,
                ),
            )
            .where(DeckRecord.owner_id == owner_id)
            .group_by(DeckRecord.id)
            .order_by(DeckRecord.created_at.asc())
        )
        result = await session.execute(stmt)
        rows = list(result.all())
        return [(row[0], int(row[1] or 0), int(row[2] or 0)) for row in rows]

    async def create_deck(
        self,
        session: AsyncSession,
        *,
        owner_id: int,
        name: str,
        description: str | None = None,
    ) -> DeckRecord:
        """Create a new deck owned by the user with a slug derived from its name."""
        slug = self._generate_slug(name)
        unique_slug = await self._ensure_unique_slug(session, owner_id=owner_id, slug=slug)
        deck = DeckRecord(
            owner_id=owner_id,
            slug=unique_slug,
            name=name.strip(),
            description=description.strip() if description else None,
        )
        session.add(deck)
        await session.flush()
        return deck

    async def get_deck(
        self,
        session: AsyncSession,
        *,
        owner_id: int,
        deck_id: int,
    ) -> DeckRecord | None:
        """Return the deck when it belongs to the user."""
        stmt = select(DeckRecord).where(DeckRecord.id == deck_id, DeckRecord.owner_id == owner_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_deck(
        self,
        session: AsyncSession,
        *,
        owner_id: int,
        deck_id: int,
        name: str | None = None,
        description: str | None = None,
    ) -> DeckRecord:
        """Update mutable fields of an existing deck."""
        deck = await self.get_deck(session, owner_id=owner_id, deck_id=deck_id)
        if deck is None:
            raise ValueError("Колода не найдена.")

        if name and name.strip():
            deck.name = name.strip()
        if description is not None:
            deck.description = description.strip() if description.strip() else None
        await session.flush()
        return deck

    async def delete_deck(
        self,
        session: AsyncSession,
        *,
        owner_id: int,
        deck_id: int,
    ) -> None:
        """Delete a deck owned by the user."""
        deck = await self.get_deck(session, owner_id=owner_id, deck_id=deck_id)
        if deck is None:
            raise ValueError("Колода не найдена.")
        await session.delete(deck)
        await session.flush()

    async def list_deck_cards(
        self,
        session: AsyncSession,
        *,
        owner_id: int,
        deck_id: int,
    ) -> list[UserCardRecord]:
        """Return cards in the specified deck for the user."""
        stmt = (
            select(UserCardRecord)
            .options(
                selectinload(UserCardRecord.card),
                selectinload(UserCardRecord.deck),
            )
            .where(
                UserCardRecord.user_id == owner_id,
                UserCardRecord.deck_id == deck_id,
            )
            .order_by(UserCardRecord.next_review_at.asc(), UserCardRecord.created_at.asc())
        )
        result = await session.execute(stmt)
        return list(result.scalars())

    async def remove_user_card(
        self,
        session: AsyncSession,
        *,
        owner_id: int,
        deck_id: int,
        user_card_id: int,
    ) -> None:
        """Unlink a card from the user's deck."""
        stmt = (
            select(UserCardRecord)
            .where(
                UserCardRecord.id == user_card_id,
                UserCardRecord.user_id == owner_id,
                UserCardRecord.deck_id == deck_id,
            )
        )
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None:
            raise ValueError("Карточка не найдена в колоде.")
        await session.delete(record)
        await session.flush()

    async def get_card_by_normalized(self, session: AsyncSession, *, normalized_source: str) -> CardRecord | None:
        """Return an existing card matching the normalized source text."""
        result = await session.execute(
            select(CardRecord).where(CardRecord.normalized_source_text == normalized_source)
        )
        return result.scalar_one_or_none()

    async def get_card_by_normalized_target(
        self,
        session: AsyncSession,
        *,
        normalized_target: str,
    ) -> CardRecord | None:
        """Return an existing card matching the normalized target text."""
        result = await session.execute(
            select(CardRecord).where(CardRecord.normalized_target_text == normalized_target)
        )
        return result.scalar_one_or_none()

    async def create_card(
        self,
        session: AsyncSession,
        *,
        source_text: str,
        target_text: str,
        example_sentence: str,
        example_translation: str,
        part_of_speech: str | None = None,
        source_language: str = "ru",
        target_language: str = "el",
        extra: dict[str, object] | None = None,
    ) -> CardRecord:
        """Persist a new canonical card."""
        normalized_source = self.normalize_text(source_text)
        normalized_target = self.normalize_text(target_text)
        card = CardRecord(
            source_text=source_text.strip(),
            source_language=source_language,
            normalized_source_text=normalized_source,
            target_text=target_text.strip(),
            target_language=target_language,
            normalized_target_text=normalized_target,
            example_sentence=example_sentence.strip(),
            example_translation=example_translation.strip(),
            part_of_speech=part_of_speech.strip() if part_of_speech else None,
            extra=extra,
        )
        session.add(card)
        await session.flush()
        return card

    async def ensure_user_card(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        deck_id: int,
        card_id: int,
        initial_due_at: dt.datetime | None = None,
    ) -> tuple[UserCardRecord, bool]:
        """Ensure a user-specific study record exists for the card."""
        record_stmt: Select[tuple[UserCardRecord]] = select(UserCardRecord).where(
            UserCardRecord.user_id == user_id,
            UserCardRecord.deck_id == deck_id,
            UserCardRecord.card_id == card_id,
        )
        result = await session.execute(record_stmt)
        existing = result.scalar_one_or_none()
        if existing is not None:
            return existing, False

        due_at = initial_due_at or dt.datetime.now(dt.timezone.utc)
        new_record = UserCardRecord(
            user_id=user_id,
            deck_id=deck_id,
            card_id=card_id,
            next_review_at=due_at,
        )
        session.add(new_record)
        await session.flush()
        return new_record, True

    async def fetch_next_due_card(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        deck_id: int | None = None,
        as_of: dt.datetime | None = None,
    ) -> UserCardRecord | None:
        """Return the soonest due flashcard for the user."""
        reference = as_of or dt.datetime.now(dt.timezone.utc)
        conditions = [
            UserCardRecord.user_id == user_id,
            UserCardRecord.next_review_at <= reference,
        ]
        if deck_id is not None:
            conditions.append(UserCardRecord.deck_id == deck_id)

        stmt: Select[tuple[UserCardRecord]] = (
            select(UserCardRecord)
            .options(
                selectinload(UserCardRecord.card),
                selectinload(UserCardRecord.deck),
            )
            .where(*conditions)
            .order_by(UserCardRecord.next_review_at.asc(), UserCardRecord.created_at.asc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def schedule_review(
        self,
        session: AsyncSession,
        record: UserCardRecord,
        *,
        rating: str,
        interval_minutes: int,
        reference_time: dt.datetime | None = None,
    ) -> UserCardRecord:
        """Update review scheduling metadata for the user card."""
        now = reference_time or dt.datetime.now(dt.timezone.utc)
        record.last_rating = rating
        record.interval_minutes = max(interval_minutes, 0)
        record.last_reviewed_at = now
        record.next_review_at = now + dt.timedelta(minutes=max(interval_minutes, 0))
        record.review_count += 1
        await session.flush()
        return record

    @staticmethod
    def normalize_text(text: str) -> str:
        """Return a case-insensitive normalization suitable for unique lookups."""
        return text.strip().casefold()

    @staticmethod
    def _generate_slug(name: str) -> str:
        """Produce a slug-style identifier from the given name."""
        cleaned = name.strip().lower()
        # Replace any sequence of non-word characters with hyphen.
        slug = re.sub(r"[^\w]+", "-", cleaned, flags=re.UNICODE).strip("-")
        return slug or "deck"

    async def _ensure_unique_slug(
        self,
        session: AsyncSession,
        *,
        owner_id: int,
        slug: str,
    ) -> str:
        """Ensure the slug is unique for the owner by appending a numeric suffix when needed."""
        candidate = slug
        index = 1
        while await self._slug_exists(session, owner_id=owner_id, slug=candidate):
            index += 1
            candidate = f"{slug}-{index}"
        return candidate

    async def _slug_exists(
        self,
        session: AsyncSession,
        *,
        owner_id: int,
        slug: str,
    ) -> bool:
        """Return True when the slug already exists for the owner."""
        stmt = select(DeckRecord.id).where(DeckRecord.owner_id == owner_id, DeckRecord.slug == slug)
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None
