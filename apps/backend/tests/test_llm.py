"""Unit tests for LLM response helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.services.llm import _extract_first_text


def test_extract_first_text_prefers_output_text_string() -> None:
    response = SimpleNamespace(output_text="Γεια σου!", output=[], text=None)
    assert _extract_first_text(response) == "Γεια σου!"


def test_extract_first_text_prefers_first_output_text_chunk() -> None:
    response = SimpleNamespace(output_text=["", "Καλημέρα"], output=[], text=None)
    assert _extract_first_text(response) == "Καλημέρα"


def test_extract_first_text_falls_back_to_text_field() -> None:
    response = SimpleNamespace(output_text=None, text=["", "γειά"], output=[])
    assert _extract_first_text(response) == "γειά"


def test_extract_first_text_uses_output_messages() -> None:
    content = SimpleNamespace(type="text", text=SimpleNamespace(value="χαιρετισμός"))
    message_item = SimpleNamespace(type="message", content=[content])
    response = SimpleNamespace(output=[message_item], output_text=None, text=None)
    assert _extract_first_text(response) == "χαιρετισμός"


def test_extract_first_text_raises_when_empty() -> None:
    response = SimpleNamespace(output=[], output_text=None, text=None)
    with pytest.raises(RuntimeError):
        _extract_first_text(response)
