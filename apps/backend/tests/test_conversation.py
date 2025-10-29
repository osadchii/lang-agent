"""Tests for the conversation service end-to-end persistence flow."""

from __future__ import annotations

from typing import Iterable, Mapping

import pytest
from sqlalchemy import select

from backend.services.conversation import ConversationService, UserMessagePayload
from backend.services.llm import LLMClient
from backend.services.storage.database import Database
from backend.services.storage.models import MessageDirection, MessageRecord, UserRecord
from backend.services.storage.repositories import MessageRepository


class DummyLLM(LLMClient):
    """LLM stub returning a canned response."""

    def __init__(self, response: str) -> None:
        self._response = response
        self.calls: list[tuple[str, list[Mapping[str, str]]]] = []

    async def generate_reply(
        self,
        *,
        user_message: str,
        history: Iterable[Mapping[str, str]] | None = None,
    ) -> str:
        self.calls.append((user_message, list(history or [])))
        return self._response


@pytest.mark.asyncio
async def test_conversation_persists_inbound_and_outbound_messages(tmp_path) -> None:
    """The service should log both user and assistant messages and reuse history."""
    db_path = tmp_path / "conversation.db"
    database = Database(f"sqlite+aiosqlite:///{db_path}")
    await database.initialize()

    llm = DummyLLM("Γεια σου!")
    service = ConversationService(database=database, llm_client=llm, model_name="test-model")

    payload = UserMessagePayload(
        user_id=123,
        username="learner",
        first_name="Антон",
        last_name=None,
        text="Привет! Как будет 'здравствуйте' по-гречески?",
    )

    reply = await service.handle_user_message(payload)

    assert reply == "Γεια σου!"
    assert llm.calls[0][0] == payload.text
    assert llm.calls[0][1] == []

    async with database.session() as session:
        messages = (await session.execute(select(MessageRecord))).scalars().all()
        users = (await session.execute(select(UserRecord))).scalars().all()

    assert len(users) == 1
    assert users[0].username == "learner"

    assert len(messages) == 2
    inbound, outbound = messages
    assert inbound.direction is MessageDirection.INBOUND
    assert inbound.content == payload.text

    assert outbound.direction is MessageDirection.OUTBOUND
    assert outbound.content == "Γεια σου!"
    assert outbound.model == "test-model"

    await database.dispose()


@pytest.mark.asyncio
async def test_conversation_limits_history_to_last_ten_messages(tmp_path) -> None:
    """Only the last configured number of messages should be sent to the LLM."""
    db_path = tmp_path / "conversation-history.db"
    database = Database(f"sqlite+aiosqlite:///{db_path}")
    await database.initialize()

    llm = DummyLLM("response")
    service = ConversationService(database=database, llm_client=llm, model_name="test-model")

    user_messages: list[str] = []

    for index in range(7):
        payload = UserMessagePayload(
            user_id=321,
            username="learner",
            first_name="User",
            last_name="Test",
            text=f"Message {index}",
        )
        await service.handle_user_message(payload)

        user_messages.append(payload.text)

    for index, (_, history) in enumerate(llm.calls):
        expected_length = min(index * 2, service.CONTEXT_MESSAGE_LIMIT)
        assert len(history) == expected_length

    final_history = llm.calls[-1][1]
    assert len(final_history) == service.CONTEXT_MESSAGE_LIMIT
    history_user_messages = [entry["content"] for entry in final_history if entry["role"] == "user"]
    assert "Message 0" not in history_user_messages
    assert "Message 5" in history_user_messages


@pytest.mark.asyncio
async def test_log_message_normalizes_blank_model(tmp_path) -> None:
    """MessageRepository should store a fallback model name when blank."""
    db_path = tmp_path / "blank-model.db"
    database = Database(f"sqlite+aiosqlite:///{db_path}")
    await database.initialize()

    message_repo = MessageRepository()

    async with database.session() as session:
        record = await message_repo.log_message(
            session,
            user_id=999,
            direction="OUTBOUND",
            content="test",
            model="   ",
        )
        await session.commit()

    assert record.model == "unknown"

    async with database.session() as session:
        inbound = await message_repo.log_message(
            session,
            user_id=1000,
            direction="INBOUND",
            content="test inbound",
            model=None,
        )
        await session.commit()

    assert inbound.model == "unknown"

    await database.dispose()

    await database.dispose()
