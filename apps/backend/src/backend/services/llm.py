"""Language model client wrappers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Protocol, cast

from openai import AsyncOpenAI
from openai.types.responses import Response, ResponseInputItemParam


class LLMClient(Protocol):
    """Protocol definition for language model clients."""

    async def generate_reply(
        self,
        *,
        user_message: str,
        history: Iterable[Mapping[str, str]] | None = None,
    ) -> str:
        """Return a model-generated reply."""
        ...


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
            conversation.extend(
                [
                    {"role": entry["role"], "content": entry["content"]}
                    for entry in history
                ]
            )

        conversation.append({"role": "user", "content": user_message})

        response = await self._client.responses.create(
            model=self.model,
            input=cast(list[ResponseInputItemParam], conversation),
        )

        return _extract_first_text(response)


def _extract_first_text(response: Response) -> str:
    """Fetch the first text segment produced by the Responses API."""
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    if isinstance(output_text, Iterable):
        for chunk in output_text:
            if isinstance(chunk, str) and chunk.strip():
                return chunk.strip()

    text_field = getattr(response, "text", None)
    if isinstance(text_field, str) and text_field.strip():
        return text_field.strip()
    if isinstance(text_field, Iterable):
        for segment in text_field:
            if isinstance(segment, str) and segment.strip():
                return segment.strip()

    for item in response.output or []:
        if item.type != "message":
            continue
        for content in item.content or []:
            if content.type == "text" and content.text and content.text.value.strip():
                return content.text.value.strip()
    raise RuntimeError("OpenAI response did not include a text message.")
