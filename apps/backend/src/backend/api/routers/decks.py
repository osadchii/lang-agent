"""Deck and card management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from ...services.flashcards import FlashcardService, FlashcardCreationResult, UserProfile
from ..dependencies import get_flashcard_service, get_user_profile
from .. import schemas

router = APIRouter(prefix="/decks", tags=["decks"])


@router.get("/", response_model=list[schemas.DeckSummaryModel])
async def list_decks(
    profile: UserProfile = Depends(get_user_profile),
    flashcards: FlashcardService = Depends(get_flashcard_service),
) -> list[schemas.DeckSummaryModel]:
    """Return all decks owned by the authenticated user."""
    decks = await flashcards.list_user_decks(profile)
    return [
        schemas.DeckSummaryModel(
            id=deck.deck_id,
            slug=deck.slug,
            name=deck.name,
            description=deck.description,
            card_count=deck.card_count,
            due_count=deck.due_count,
            created_at=deck.created_at,
        )
        for deck in decks
    ]


@router.post("/", response_model=schemas.DeckSummaryModel, status_code=status.HTTP_201_CREATED)
async def create_deck(
    payload: schemas.CreateDeckRequest,
    profile: UserProfile = Depends(get_user_profile),
    flashcards: FlashcardService = Depends(get_flashcard_service),
) -> schemas.DeckSummaryModel:
    """Create a new deck."""
    try:
        deck = await flashcards.create_deck(
            profile,
            name=payload.name,
            description=payload.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return schemas.DeckSummaryModel(
        id=deck.deck_id,
        slug=deck.slug,
        name=deck.name,
        description=deck.description,
        card_count=deck.card_count,
        due_count=deck.due_count,
        created_at=deck.created_at,
    )


@router.patch("/{deck_id}", response_model=schemas.DeckSummaryModel)
async def update_deck(
    deck_id: int,
    payload: schemas.UpdateDeckRequest,
    profile: UserProfile = Depends(get_user_profile),
    flashcards: FlashcardService = Depends(get_flashcard_service),
) -> schemas.DeckSummaryModel:
    """Update deck metadata."""
    try:
        deck = await flashcards.update_deck(
            profile,
            deck_id=deck_id,
            name=payload.name,
            description=payload.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return schemas.DeckSummaryModel(
        id=deck.deck_id,
        slug=deck.slug,
        name=deck.name,
        description=deck.description,
        card_count=deck.card_count,
        due_count=deck.due_count,
        created_at=deck.created_at,
    )


@router.delete("/{deck_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_deck(
    deck_id: int,
    profile: UserProfile = Depends(get_user_profile),
    flashcards: FlashcardService = Depends(get_flashcard_service),
) -> Response:
    """Delete a deck and its associated user cards."""
    try:
        await flashcards.delete_deck(profile, deck_id=deck_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{deck_id}/cards",
    response_model=list[schemas.DeckCardModel],
)
async def list_deck_cards(
    deck_id: int,
    profile: UserProfile = Depends(get_user_profile),
    flashcards: FlashcardService = Depends(get_flashcard_service),
) -> list[schemas.DeckCardModel]:
    """Return cards in the specified deck."""
    try:
        cards = await flashcards.list_deck_cards(profile, deck_id=deck_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return [
        schemas.DeckCardModel(
            user_card_id=card.user_card_id,
            deck_id=card.deck_id,
            card=schemas.FlashcardModel(
                card_id=card.card.card_id,
                source_text=card.card.source_text,
                target_text=card.card.target_text,
                example_sentence=card.card.example_sentence,
                example_translation=card.card.example_translation,
                part_of_speech=card.card.part_of_speech,
            ),
            last_rating=card.last_rating,
            interval_minutes=card.interval_minutes,
            review_count=card.review_count,
            next_review_at=card.next_review_at,
            last_reviewed_at=card.last_reviewed_at,
        )
        for card in cards
    ]


@router.post(
    "/{deck_id}/cards",
    response_model=schemas.FlashcardCreationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_card_in_deck(
    deck_id: int,
    payload: schemas.CreateCardRequest,
    profile: UserProfile = Depends(get_user_profile),
    flashcards: FlashcardService = Depends(get_flashcard_service),
) -> schemas.FlashcardCreationResponse:
    """Generate or reuse a card and attach it to the deck."""
    try:
        result = await flashcards.create_card_for_deck(
            profile,
            deck_id=deck_id,
            prompt_text=payload.prompt,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - propagate unexpected errors with context
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Не удалось создать карточку.") from exc

    return _to_creation_response(result)


@router.delete(
    "/{deck_id}/cards/{user_card_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def remove_card_from_deck(
    deck_id: int,
    user_card_id: int,
    profile: UserProfile = Depends(get_user_profile),
    flashcards: FlashcardService = Depends(get_flashcard_service),
) -> Response:
    """Detach a card from the deck."""
    try:
        await flashcards.remove_card_from_deck(
            profile,
            deck_id=deck_id,
            user_card_id=user_card_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _to_creation_response(result: FlashcardCreationResult) -> schemas.FlashcardCreationResponse:
    """Convert the creation result into a response payload."""
    if result.card is None or result.user_card_id is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ответ сервиса карточек неполный.")

    card = result.card
    user_card_id = result.user_card_id
    return schemas.FlashcardCreationResponse(
        user_card_id=user_card_id,
        card=schemas.FlashcardModel(
            card_id=card.card_id,
            source_text=card.source_text,
            target_text=card.target_text,
            example_sentence=card.example_sentence,
            example_translation=card.example_translation,
            part_of_speech=card.part_of_speech,
        ),
        created_card=result.created_card,
        reused_existing_card=result.reused_existing_card,
        linked_to_user=result.linked_to_user,
    )
