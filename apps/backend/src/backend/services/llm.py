"""Language model client wrappers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Protocol, cast

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


@dataclass(frozen=True)
class FlashcardContent:
    """Structured information required to build a flashcard."""

    source_text: str
    target_text: str
    example_sentence: str
    example_translation: str
    part_of_speech: str | None = None
    extra: dict[str, Any] | None = None


class FlashcardGenerator(Protocol):
    """Protocol definition for generating flashcard content."""

    async def generate_flashcard(self, *, prompt_word: str) -> FlashcardContent:
        """Produce translated card content for the supplied word."""
        ...


@dataclass
class OpenAIFlashcardGenerator:
    """Generate structured flashcard content using the OpenAI Responses API."""

    api_key: str
    model: str
    system_prompt: str = field(
        default=(
            "You are a professional Modern Greek language teacher helping Russian-speaking learners. "
            "Return concise flashcard data in JSON. For Greek nouns, include the appropriate definite article "
            "(ο/η/το) before the translation. Use modern Greek orthography."
        )
    )

    def __post_init__(self) -> None:
        self._client = AsyncOpenAI(api_key=self.api_key)

    async def generate_flashcard(self, *, prompt_word: str) -> FlashcardContent:
        """Request structured flashcard content for the supplied word."""
        response = await self._client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": (
                        "Создай карточку для изучения греческого языка русскоязычным учеником.\n"
                        f"Исходное русское слово или фраза: \"{prompt_word.strip()}\".\n"
                        "Определи часть речи. Дай греческий перевод (для существительных обязательно с артиклем), "
                        "а также пример предложения на греческом и его перевод на русский. "
                        "Верни ответ строго в формате JSON без пояснений и без Markdown, "
                        "со структурой:\n"
                        "{\n"
                        '  "source_text": "",\n'
                        '  "target_text": "",\n'
                        '  "example_sentence": "",\n'
                        '  "example_translation": "",\n'
                        '  "part_of_speech": "noun|verb|... (опционально)",\n'
                        '  "notes": "опционально"\n'
                        "}\n"
                        "Если данных нет, оставляй поле пустой строкой."
                    ),
                },
            ],
        )

        payload = _parse_flashcard_json(_extract_first_text(response))
        extra = {key: value for key, value in payload.items() if key not in {"source_text", "target_text", "example_sentence", "example_translation", "part_of_speech"}}

        return FlashcardContent(
            source_text=payload.get("source_text", prompt_word).strip(),
            target_text=_ensure_article_for_noun(
                payload.get("target_text", "").strip(),
                payload.get("part_of_speech"),
            ),
            example_sentence=payload.get("example_sentence", "").strip(),
            example_translation=payload.get("example_translation", "").strip(),
            part_of_speech=_safe_strip(payload.get("part_of_speech")),
            extra=extra or None,
        )


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


def _parse_flashcard_json(raw: str) -> dict[str, Any]:
    """Parse the JSON payload returned for flashcard generation."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # Remove surrounding Markdown code fences if present.
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    if not cleaned.startswith("{"):
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            cleaned = cleaned[start : end + 1]

    try:
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError("Flashcard response must be a JSON object.")
        return parsed
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive guard
        raise RuntimeError("Не удалось обработать ответ модели для карточки.") from exc


def _safe_strip(value: Any) -> str | None:
    """Trim a string value if present."""
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _ensure_article_for_noun(target_text: str, part_of_speech: Any) -> str:
    """Ensure Greek nouns include a definite article when possible."""
    if not target_text:
        return target_text
    if isinstance(part_of_speech, str) and "noun" in part_of_speech.lower():
        lowered = target_text.strip().lower()
        articles = ("ο ", "η ", "το ")
        if not any(lowered.startswith(article) for article in articles):
            # Fallback to masculine article when uncertain.
            return f"ο {target_text}"
    return target_text
