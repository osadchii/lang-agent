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
_MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_MARKDOWN_TABLE_RE = re.compile(r"^\|.+\|$", re.MULTILINE)
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
    """
    Prepare LLM response for Telegram HTML mode.

    The LLM is instructed to generate Telegram-compatible HTML directly.
    This function provides fallback conversion for basic Markdown patterns
    and removes unsupported elements if the LLM makes mistakes.
    """
    stripped = raw_text.strip()
    if not stripped:
        return stripped

    # Check if response already uses proper HTML tags (and no Markdown)
    tag_names = {match.group(1).lower() for match in _HTML_TAG_RE.finditer(stripped)}
    has_markdown_markers = any([
        '**' in stripped,
        stripped.count('*') > len(tag_names) * 2,  # More asterisks than HTML tags
        _MARKDOWN_HEADING_RE.search(stripped),
        _MARKDOWN_TABLE_RE.search(stripped),
    ])
    if tag_names and tag_names.issubset(_ALLOWED_HTML_TAGS) and not has_markdown_markers:
        # Response is already in proper format, return as-is
        return stripped

    # Fallback: sanitize and convert basic Markdown patterns

    # Remove unsupported HTML tags (keep content)
    def _drop_disallowed_tags(match: re.Match[str]) -> str:
        tag = match.group(1).lower()
        return match.group(0) if tag in _ALLOWED_HTML_TAGS else ""

    text = _HTML_TAG_RE.sub(_drop_disallowed_tags, stripped)

    # Remove Markdown tables - convert to plain text
    lines = text.splitlines()
    filtered_lines = []
    for line in lines:
        if _MARKDOWN_TABLE_RE.match(line.strip()):
            # Extract cell content from table row
            cells = [cell.strip() for cell in line.split('|') if cell.strip() and cell.strip() not in ('---', '')]
            if cells:
                filtered_lines.append("  ".join(cells))
        else:
            filtered_lines.append(line)
    text = "\n".join(filtered_lines)

    # Store code blocks before escaping (use unique marker that won't be escaped)
    code_blocks: list[str] = []
    def _store_code(match: re.Match[str]) -> str:
        code_blocks.append(f"<pre><code>{html.escape(match.group(2) or '')}</code></pre>")
        return f"\x00CODE{len(code_blocks) - 1}\x00"  # Use null bytes as markers
    text = _MARKDOWN_CODE_BLOCK_RE.sub(_store_code, text)

    # Store headings before escaping
    headings: list[str] = []
    def _store_heading(match: re.Match[str]) -> str:
        headings.append(match.group(2).strip())
        return f"\x00HEADING{len(headings) - 1}\x00"
    text = _MARKDOWN_HEADING_RE.sub(_store_heading, text)

    # Escape HTML special characters (null bytes pass through)
    text = html.escape(text)

    # Convert basic Markdown to HTML
    text = _MARKDOWN_INLINE_CODE_RE.sub(lambda m: f"<code>{m.group(1)}</code>", text)
    text = _MARKDOWN_BOLD_RE.sub(lambda m: f"<b>{m.group(1)}</b>", text)
    text = _MARKDOWN_STRONG_RE.sub(lambda m: f"<b>{m.group(1)}</b>", text)
    text = _MARKDOWN_ITALIC_RE.sub(lambda m: f"<i>{m.group(1)}</i>", text)
    text = _MARKDOWN_EM_RE.sub(lambda m: f"<i>{m.group(1)}</i>", text)

    # Convert bullet lists
    lines = text.splitlines()
    formatted_lines = []
    for line in lines:
        stripped_line = line.lstrip()
        if stripped_line.startswith(("- ", "* ")):
            bullet_text = stripped_line[2:].strip()
            formatted_lines.append(f"• {bullet_text}")
        else:
            formatted_lines.append(line)
    text = "\n".join(formatted_lines)

    # Restore code blocks and headings
    for i, code in enumerate(code_blocks):
        text = text.replace(f"\x00CODE{i}\x00", code)
    for i, heading in enumerate(headings):
        text = text.replace(f"\x00HEADING{i}\x00", f"<b>{heading}</b>")

    # Clean up excessive newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


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
