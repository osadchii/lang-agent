"""HTTP API integration tests with stubbed services."""

from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient

from backend.api.app import create_api
from backend.api.dependencies import APIContainer
from backend.services.flashcards import (
    DeckCard,
    DeckSummary,
    FlashcardCreationResult,
    FlashcardData,
    ReviewRating,
    StudyCard,
    UserProfile,
)


class StubDatabase:
    """Minimal database stub satisfying lifespan hooks."""

    def __init__(self) -> None:
        self.initialized = False
        self.disposed = False

    async def initialize(self) -> None:
        self.initialized = True

    async def dispose(self) -> None:
        self.disposed = True


class StubTelegramBot:
    """Minimal Telegram bot stub for testing."""

    async def set_webhook(self, url: str) -> None:
        pass

    async def delete_webhook(self) -> None:
        pass


class StubConfig:
    """Minimal config stub for testing."""

    telegram_webhook_url = None


class StubFlashcardService:
    """Stub flashcard service implementing the methods used by the API."""

    def __init__(self) -> None:
        now = dt.datetime.now(dt.timezone.utc)
        self.deck_summary = DeckSummary(
            deck_id=5,
            slug="evening",
            name="Evening Practice",
            description="Wind-down session",
            card_count=1,
            due_count=1,
            created_at=now,
        )
        flashcard = FlashcardData(
            card_id=42,
            source_text="привет",
            target_text="καλημέρα",
            example_sentence="Καλημέρα σας!",
            example_translation="Доброе утро!",
            part_of_speech="noun",
        )
        self.deck_card = DeckCard(
            user_card_id=77,
            deck_id=5,
            card=flashcard,
            last_rating=None,
            interval_minutes=0,
            review_count=0,
            next_review_at=now,
            last_reviewed_at=None,
        )
        self.creation_result = FlashcardCreationResult(
            input_text="привет",
            created_card=True,
            linked_to_user=True,
            card=flashcard,
            reused_existing_card=False,
            user_card_id=77,
            message=None,
            error=None,
        )
        self.study_card = StudyCard(
            user_card_id=77,
            deck_id=5,
            deck_name="Evening Practice",
            card=flashcard,
        )
        self.created_decks: list[tuple[UserProfile, str, str | None]] = []
        self.removed_cards: list[int] = []
        self.recorded_ratings: list[ReviewRating] = []

    async def list_user_decks(self, profile: UserProfile):  # type: ignore[override]
        return [self.deck_summary]

    async def create_deck(self, profile: UserProfile, *, name: str, description: str | None = None):  # type: ignore[override]
        self.created_decks.append((profile, name, description))
        now = dt.datetime.now(dt.timezone.utc)
        return DeckSummary(
            deck_id=9,
            slug="new-deck",
            name=name,
            description=description,
            card_count=0,
            due_count=0,
            created_at=now,
        )

    async def update_deck(self, *args, **kwargs):  # type: ignore[override]
        return self.deck_summary

    async def delete_deck(self, profile: UserProfile, *, deck_id: int):  # type: ignore[override]
        self.removed_cards.append(deck_id)

    async def list_deck_cards(self, profile: UserProfile, *, deck_id: int):  # type: ignore[override]
        if deck_id != self.deck_summary.deck_id:
            return []
        return [self.deck_card]

    async def create_card_for_deck(self, profile: UserProfile, *, deck_id: int, prompt_text: str):  # type: ignore[override]
        return self.creation_result

    async def remove_card_from_deck(self, profile: UserProfile, *, deck_id: int, user_card_id: int):  # type: ignore[override]
        self.removed_cards.append(user_card_id)

    async def get_next_card(self, *, user_id: int, deck_id: int | None = None):  # type: ignore[override]
        return self.study_card

    async def record_review(self, *, user_id: int, user_card_id: int, rating: ReviewRating):  # type: ignore[override]
        self.recorded_ratings.append(rating)

    async def get_user_card(self, *, user_id: int, user_card_id: int):  # type: ignore[override]
        return self.study_card


@pytest.fixture()
def test_client(monkeypatch) -> tuple[TestClient, StubFlashcardService, StubDatabase]:
    """Provide a FastAPI test client wired with stubbed dependencies."""

    stub_service = StubFlashcardService()
    stub_db = StubDatabase()
    stub_bot = StubTelegramBot()
    stub_config = StubConfig()
    container = APIContainer(
        config=stub_config,  # type: ignore[arg-type]
        database=stub_db,
        flashcards=stub_service,
        telegram_bot=stub_bot,  # type: ignore[arg-type]
    )

    monkeypatch.setattr("backend.api.app.build_container", lambda: container)

    app = create_api()
    client = TestClient(app)
    return client, stub_service, stub_db


def test_list_decks_endpoint(test_client) -> None:
    client, service, database = test_client

    with client:
        response = client.get("/api/decks", headers={"X-User-Id": "1"})

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["name"] == "Evening Practice"
    assert database.initialized is True
    assert database.disposed is True
    assert service.created_decks == []


def test_training_flow_endpoints(test_client) -> None:
    client, service, _ = test_client

    with client:
        next_card = client.get("/api/training/next", headers={"X-User-Id": "2"})
        assert next_card.status_code == 200
        assert next_card.json()["deck_name"] == "Evening Practice"

        review = client.post(
            "/api/training/cards/77/review",
            headers={"X-User-Id": "2"},
            json={"rating": "easy"},
        )
        assert review.status_code == 204

    assert service.recorded_ratings == [ReviewRating.EASY]
