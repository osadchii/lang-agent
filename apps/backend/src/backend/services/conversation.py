"""Conversation orchestration between Telegram, storage, and the LLM."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .llm import LLMClient
from .storage.database import Database
from .storage.models import MessageDirection
from .storage.repositories import MessageRepository, UserRepository


@dataclass
class UserMessagePayload:
    """Incoming message metadata from Telegram."""

    user_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    text: str


class ConversationService:
    """Coordinate message flow across persistence and the LLM."""

    CONTEXT_MESSAGE_LIMIT = 10

    def __init__(
        self,
        *,
        database: Database,
        llm_client: LLMClient,
        model_name: str,
        user_repository: UserRepository | None = None,
        message_repository: MessageRepository | None = None,
    ) -> None:
        self._database = database
        self._llm_client = llm_client
        self._model_name = model_name
        self._users = user_repository or UserRepository()
        self._messages = message_repository or MessageRepository()

    async def handle_user_message(self, payload: UserMessagePayload) -> str:
        """Persist the inbound message, request a reply, persist it, and return it."""
        async with self._database.session() as session:
            user = await self._users.upsert_user(
                session,
                user_id=payload.user_id,
                username=payload.username,
                first_name=payload.first_name,
                last_name=payload.last_name,
            )

            history_records = await self._messages.fetch_recent_messages(
                session,
                user_id=user.id,
                limit=self.CONTEXT_MESSAGE_LIMIT,
            )
            history: Sequence[Mapping[str, str]] = [
                {
                    "role": "user" if record.direction == MessageDirection.INBOUND else "assistant",
                    "content": record.content,
                }
                for record in history_records
            ]

            await self._messages.log_message(
                session,
                user_id=user.id,
                direction=MessageDirection.INBOUND,
                content=payload.text,
            )

            reply = await self._llm_client.generate_reply(user_message=payload.text, history=history)

            await self._messages.log_message(
                session,
                user_id=user.id,
                direction=MessageDirection.OUTBOUND,
                content=reply,
                model=self._model_name,
            )

            await session.commit()

        return reply
