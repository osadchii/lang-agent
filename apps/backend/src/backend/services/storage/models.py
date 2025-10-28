"""SQLAlchemy ORM models backing Telegram interactions."""

from __future__ import annotations

import datetime as dt
from enum import Enum

from sqlalchemy import BigInteger, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text
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
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc))

    messages: Mapped[list["MessageRecord"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class MessageRecord(Base):
    """Log of a single inbound or outbound message."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    direction: Mapped[MessageDirection] = mapped_column(SAEnum(MessageDirection), nullable=False)
    content: Mapped[str] = mapped_column(Text(), nullable=False)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc), index=True)

    user: Mapped["UserRecord"] = relationship(back_populates="messages")

