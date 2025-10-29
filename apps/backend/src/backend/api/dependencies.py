"""Dependency providers for the FastAPI application."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException, status

from ..config import AppConfig
from ..services.flashcards import FlashcardService, UserProfile
from ..services.llm import OpenAIFlashcardGenerator
from ..services.storage.database import Database


@dataclass
class APIContainer:
    """Aggregate application services shared by the HTTP API."""

    config: AppConfig
    database: Database
    flashcards: FlashcardService


_CONTAINER: APIContainer | None = None


def build_container() -> APIContainer:
    """Compose the service container for the API runtime."""
    config = AppConfig.load()
    database = Database(config.database_url)
    generator = OpenAIFlashcardGenerator(
        api_key=config.openai_api_key,
        model=config.openai_model,
    )
    flashcards = FlashcardService(
        database=database,
        generator=generator,
    )
    return APIContainer(config=config, database=database, flashcards=flashcards)


def set_container(container: APIContainer) -> None:
    """Set the global container reference for dependency lookup."""
    global _CONTAINER
    _CONTAINER = container


def get_container() -> APIContainer:
    """Return the configured container instance."""
    if _CONTAINER is None:  # pragma: no cover - defensive guard
        raise RuntimeError("API container has not been initialised.")
    return _CONTAINER


def get_flashcard_service() -> FlashcardService:
    """Dependency hook returning the flashcard service."""
    return get_container().flashcards


def get_user_profile(
    x_user_id: str = Header(default=None, alias="X-User-Id"),
    x_user_username: str | None = Header(default=None, alias="X-User-Username"),
    x_user_first_name: str | None = Header(default=None, alias="X-User-First-Name"),
    x_user_last_name: str | None = Header(default=None, alias="X-User-Last-Name"),
) -> UserProfile:
    """Hydrate a user profile from request headers."""
    if x_user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-User-Id header is required.")
    try:
        user_id = int(x_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-User-Id must be an integer.") from exc

    return UserProfile(
        user_id=user_id,
        username=_normalize_header_value(x_user_username),
        first_name=_normalize_header_value(x_user_first_name),
        last_name=_normalize_header_value(x_user_last_name),
    )


def _normalize_header_value(raw: str | None) -> str | None:
    """Return a trimmed string or None when empty."""
    if raw is None:
        return None
    value = raw.strip()
    return value or None

