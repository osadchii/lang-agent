"""Conversation orchestration between Telegram, storage, and the LLM."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Mapping, Sequence

from .llm import LLMClient
from .storage.database import Database
from .storage.models import MessageDirection
from .storage.repositories import MessageRepository, UserRepository

_MARKDOWN_CODE_BLOCK_RE = re.compile(r"```(\w+)?\n([\s\S]*?)```", re.MULTILINE)
_MARKDOWN_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_MARKDOWN_STRONG_RE = re.compile(r"__(.+?)__")
_MARKDOWN_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
_MARKDOWN_EM_RE = re.compile(r"_(.+?)_")
_MARKDOWN_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_HTML_TAG_RE = re.compile(r"</?([a-zA-Z0-9]+)(?:\s[^>]*)?>")
_ALLOWED_HTML_TAGS = {
    "a",
    "b",
    "strong",
    "i",
    "em",
    "u",
    "ins",
    "s",
    "strike",
    "del",
    "code",
    "pre",
    "br",
    "blockquote",
    "tg-spoiler",
    "span",
}


def _format_reply_to_html(raw_text: str) -> str:
    """Convert lightweight Markdown-style formatting into Telegram-friendly HTML."""
    stripped = raw_text.strip()
    if not stripped:
        return stripped

    # If the model already returned only allowed HTML tags, keep it untouched.
    tag_names = {match.group(1).lower() for match in _HTML_TAG_RE.finditer(stripped)}
    if tag_names and tag_names.issubset(_ALLOWED_HTML_TAGS):
        return stripped

    # Remove disallowed HTML tags while preserving the enclosed content.
    def _drop_disallowed_tags(match: re.Match[str]) -> str:
        tag = match.group(1).lower()
        return match.group(0) if tag in _ALLOWED_HTML_TAGS else ""

    sanitized_source = _HTML_TAG_RE.sub(_drop_disallowed_tags, stripped)

    code_block_snippets: list[str] = []

    def _store_code_block(match: re.Match[str]) -> str:
        code_content = match.group(2) or ""
        code_block_snippets.append(f"<pre><code>{html.escape(code_content.strip())}</code></pre>")
        return f"[[CODE_BLOCK_{len(code_block_snippets) - 1}]]"

    without_code_blocks = _MARKDOWN_CODE_BLOCK_RE.sub(_store_code_block, sanitized_source)

    escaped = html.escape(without_code_blocks)

    escaped = _MARKDOWN_INLINE_CODE_RE.sub(lambda m: f"<code>{m.group(1)}</code>", escaped)
    escaped = _MARKDOWN_BOLD_RE.sub(lambda m: f"<b>{m.group(1)}</b>", escaped)
    escaped = _MARKDOWN_STRONG_RE.sub(lambda m: f"<b>{m.group(1)}</b>", escaped)
    escaped = _MARKDOWN_ITALIC_RE.sub(lambda m: f"<i>{m.group(1)}</i>", escaped)
    escaped = _MARKDOWN_EM_RE.sub(lambda m: f"<i>{m.group(1)}</i>", escaped)

    lines = escaped.splitlines()
    formatted_lines: list[str] = []
    for line in lines:
        stripped_line = line.lstrip()
        if stripped_line.startswith(("- ", "* ")):
            if formatted_lines and formatted_lines[-1].strip() and not formatted_lines[-1].lstrip().startswith("•"):
                formatted_lines.append("")
            bullet_text = stripped_line[2:].strip()
            formatted_lines.append(f"• {bullet_text}")
        else:
            formatted_lines.append(line)

    converted_text = "\n".join(formatted_lines)
    converted_text = re.sub(r"\n{3,}", "\n\n", converted_text)

    for index, snippet in enumerate(code_block_snippets):
        converted_text = converted_text.replace(f"[[CODE_BLOCK_{index}]]", snippet)

    return converted_text.strip()


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
            formatted_reply = _format_reply_to_html(reply)

            await self._messages.log_message(
                session,
                user_id=user.id,
                direction=MessageDirection.OUTBOUND,
                content=reply,
                model=self._model_name,
            )

            await session.commit()

        return formatted_reply
