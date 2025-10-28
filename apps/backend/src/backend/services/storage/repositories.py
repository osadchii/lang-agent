"""Repositories encapsulating database access patterns."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import MessageDirection, MessageRecord, UserRecord


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


class MessageRepository:
    """Store inbound and outbound message logs."""

    async def log_message(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        direction: MessageDirection,
        content: str,
        model: Optional[str] = None,
    ) -> MessageRecord:
        """Persist a message tied to a user."""
        record = MessageRecord(user_id=user_id, direction=direction, content=content, model=model)
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

