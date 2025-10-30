"""Pydantic models for API request and response payloads."""

from __future__ import annotations

import datetime as dt
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class FlashcardModel(BaseModel):
    """Serialized flashcard content."""

    model_config = ConfigDict(from_attributes=True)

    card_id: int
    source_text: str
    target_text: str
    example_sentence: str
    example_translation: str
    part_of_speech: str | None = None


class DeckSummaryModel(BaseModel):
    """Metadata describing a deck."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    description: str | None = None
    card_count: int
    due_count: int
    created_at: dt.datetime


class DeckCardModel(BaseModel):
    """Card and scheduling information within a deck."""

    model_config = ConfigDict(from_attributes=True)

    user_card_id: int
    deck_id: int
    card: FlashcardModel
    last_rating: str | None = None
    interval_minutes: int
    review_count: int
    next_review_at: dt.datetime
    last_reviewed_at: dt.datetime | None = None


class CreateDeckRequest(BaseModel):
    """Payload for creating a deck."""

    name: str
    description: str | None = None


class UpdateDeckRequest(BaseModel):
    """Payload for updating mutable deck fields."""

    name: str | None = None
    description: str | None = None


class CreateCardRequest(BaseModel):
    """Payload containing the prompt text for generating a card."""

    prompt: str = Field(..., min_length=1)


class GenerateCardsRequest(BaseModel):
    """Payload for generating multiple cards via LLM."""

    prompt: str = Field(..., min_length=1, description="Description of what words to generate")
    count: int = Field(default=15, ge=5, le=30, description="Number of cards to generate")


class FlashcardCreationResponse(BaseModel):
    """Result of a card creation attempt."""

    user_card_id: int
    card: FlashcardModel
    created_card: bool
    reused_existing_card: bool
    linked_to_user: bool


class RatingValue(str, Enum):
    """Enumerate supported review ratings."""

    AGAIN = "again"
    REVIEW = "review"
    EASY = "easy"


class ReviewRequest(BaseModel):
    """Body schema for recording a review."""

    rating: RatingValue


class TrainingCardModel(BaseModel):
    """Flashcard presentation data for training."""

    user_card_id: int
    deck_id: int
    deck_name: str
    prompt: str
    hidden: str
    prompt_side: str
    card: FlashcardModel
