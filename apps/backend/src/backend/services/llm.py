"""Language model client wrappers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Protocol

from openai import AsyncOpenAI
from openai.types.responses import Response


class LLMClient(Protocol):
    """Protocol definition for language model clients."""

    async def generate_reply(
        self,
        *,
        user_message: str,
        history: Iterable[Mapping[str, str]] | None = None,
    ) -> str:
        """Return a model-generated reply."""


@dataclass
class OpenAIChatClient:
    """Wrapper around OpenAI's Responses API."""

    api_key: str
    model: str
    system_prompt: str

    def __post_init__(self) -> None:
        self._client = AsyncOpenAI(api_key=self.api_key)

    async def generate_reply(
        self,
        *,
        user_message: str,
        history: Iterable[Mapping[str, str]] | None = None,
    ) -> str:
        """Generate a reply using the configured OpenAI model."""
        conversation: list[dict[str, str]] = [
            {"role": "system", "content": self.system_prompt},
        ]

        if history:
            conversation.extend(history)

        conversation.append({"role": "user", "content": user_message})

        response = await self._client.responses.create(
            model=self.model,
            input=conversation,
        )

        return _extract_first_text(response)


def _extract_first_text(response: Response) -> str:
    """Fetch the first text segment produced by the Responses API."""
    output_text = getattr(response, "output_text", None)
    if output_text:
        if isinstance(output_text, str) and output_text.strip():
            return output_text
        if isinstance(output_text, Iterable):
            for chunk in output_text:
                if isinstance(chunk, str) and chunk.strip():
                    return chunk

    text_field = getattr(response, "text", None)
    if text_field:
        if isinstance(text_field, str) and text_field.strip():
            return text_field
        if isinstance(text_field, Iterable):
            for segment in text_field:
                if isinstance(segment, str) and segment.strip():
                    return segment

    for item in response.output or []:
        if item.type != "message":
            continue
        for content in item.content or []:
            if content.type == "text" and content.text:
                return content.text.value
    raise RuntimeError("OpenAI response did not include a text message.")
