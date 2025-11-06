"""SQLAlchemy ORM models backing Telegram interactions."""

from __future__ import annotations

import datetime as dt
from enum import Enum
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarative class for SQLAlchemy models."""


class MessageDirection(str, Enum):
    """Direction of the message relative to the user."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"


class UserRecord(Base):
    """Persisted Telegram user profile."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active_deck_id: Mapped[int | None] = mapped_column(ForeignKey("decks.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc))

    messages: Mapped[list["MessageRecord"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    owned_decks: Mapped[list["DeckRecord"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        foreign_keys="DeckRecord.owner_id",
    )
    flashcards: Mapped[list["UserCardRecord"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    active_deck: Mapped["DeckRecord | None"] = relationship(foreign_keys=[active_deck_id], viewonly=True)


class MessageRecord(Base):
    """Log of a single inbound or outbound message."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    direction: Mapped[MessageDirection] = mapped_column(
        SAEnum(
            MessageDirection,
            name="messagedirection",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            create_type=False,
        ),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text(), nullable=False)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc), index=True)

    user: Mapped["UserRecord"] = relationship(back_populates="messages")


class DeckRecord(Base):
    """A collection of flashcards grouped for study."""

    __tablename__ = "decks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc))

    __table_args__ = (
        UniqueConstraint("owner_id", "slug", name="uq_decks_owner_slug"),
    )

    owner: Mapped["UserRecord | None"] = relationship(
        back_populates="owned_decks",
        foreign_keys=[owner_id],
    )
    user_cards: Mapped[list["UserCardRecord"]] = relationship(back_populates="deck", cascade="all, delete-orphan")


class CardRecord(Base):
    """Canonical flashcard content reusable across users."""

    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_text: Mapped[str] = mapped_column(Text(), nullable=False)
    source_language: Mapped[str] = mapped_column(String(16), nullable=False, default="ru")
    normalized_source_text: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)
    target_text: Mapped[str] = mapped_column(Text(), nullable=False)
    target_language: Mapped[str] = mapped_column(String(16), nullable=False, default="el")
    normalized_target_text: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    example_sentence: Mapped[str] = mapped_column(Text(), nullable=False)
    example_translation: Mapped[str] = mapped_column(Text(), nullable=False)
    part_of_speech: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extra: Mapped[dict[str, Any] | None] = mapped_column(JSON(), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc))

    user_cards: Mapped[list["UserCardRecord"]] = relationship(back_populates="card")


class UserCardRecord(Base):
    """User-specific study metadata referencing reusable cards."""

    __tablename__ = "user_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    deck_id: Mapped[int] = mapped_column(ForeignKey("decks.id", ondelete="CASCADE"), nullable=False, index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), nullable=False, index=True)
    last_rating: Mapped[str | None] = mapped_column(String(32), nullable=True)
    interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_review_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    last_reviewed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc))

    __table_args__ = (
        UniqueConstraint("user_id", "deck_id", "card_id", name="uq_user_deck_card"),
    )

    user: Mapped["UserRecord"] = relationship(back_populates="flashcards")
    deck: Mapped["DeckRecord"] = relationship(back_populates="user_cards")
    card: Mapped["CardRecord"] = relationship(back_populates="user_cards")
