"""Dependency providers for the FastAPI application."""

from __future__ import annotations

import os
from dataclasses import dataclass

from fastapi import Header, HTTPException, status

from ..config import AppConfig
from ..services.flashcards import FlashcardService, UserProfile
from ..services.llm import OpenAIFlashcardGenerator
from ..services.storage.database import Database
from ..services.telegram_auth import TelegramAuthError, parse_telegram_user


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


def get_authenticated_user(
    telegram_init_data: str | None = Header(default=None, alias="Telegram-Init-Data"),
) -> UserProfile:
    """
    Authenticate user via Telegram WebApp initData.

    This is the SECURE authentication method that validates cryptographic signatures.
    Use this in production to prevent user impersonation.

    Args:
        telegram_init_data: The initData string from window.Telegram.WebApp.initData

    Returns:
        UserProfile with validated user data

    Raises:
        HTTPException: 401 if initData is missing or invalid
    """
    if not telegram_init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram-Init-Data header is required for authentication",
        )

    bot_token = get_container().config.telegram_bot_token
    try:
        telegram_user = parse_telegram_user(telegram_init_data, bot_token)
    except TelegramAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Telegram authentication: {exc}",
        ) from exc

    return UserProfile(
        user_id=telegram_user.id,
        username=telegram_user.username,
        first_name=telegram_user.first_name,
        last_name=telegram_user.last_name,
    )


def get_user_profile(
    telegram_init_data: str | None = Header(default=None, alias="Telegram-Init-Data"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_username: str | None = Header(default=None, alias="X-User-Username"),
    x_user_first_name: str | None = Header(default=None, alias="X-User-First-Name"),
    x_user_last_name: str | None = Header(default=None, alias="X-User-Last-Name"),
) -> UserProfile:
    """
    Hydrate a user profile from Telegram initData or fallback to headers.

    Security model:
    - If REQUIRE_TELEGRAM_AUTH=true (production): Only accepts Telegram-Init-Data
    - If REQUIRE_TELEGRAM_AUTH=false (dev): Accepts either Telegram-Init-Data or X-User-* headers

    This allows:
    - Production: Cryptographically verified Telegram users only
    - Development: Testing with curl/Postman using X-User-Id headers

    Args:
        telegram_init_data: Signed initData from Telegram WebApp (preferred)
        x_user_id: User ID header (dev fallback)
        x_user_username: Username header (dev fallback)
        x_user_first_name: First name header (dev fallback)
        x_user_last_name: Last name header (dev fallback)

    Returns:
        UserProfile with user data

    Raises:
        HTTPException: 401 if authentication fails
    """
    require_telegram_auth = os.getenv("REQUIRE_TELEGRAM_AUTH", "false").lower() == "true"

    # Try Telegram authentication first
    if telegram_init_data:
        bot_token = get_container().config.telegram_bot_token
        try:
            telegram_user = parse_telegram_user(telegram_init_data, bot_token)
            return UserProfile(
                user_id=telegram_user.id,
                username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
            )
        except TelegramAuthError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Telegram authentication: {exc}",
            ) from exc

    # Fallback to header-based auth (only if not requiring Telegram)
    if require_telegram_auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram-Init-Data is required in production mode (REQUIRE_TELEGRAM_AUTH=true)",
        )

    # Development mode: allow header-based auth
    if x_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either Telegram-Init-Data or X-User-Id header is required",
        )

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

