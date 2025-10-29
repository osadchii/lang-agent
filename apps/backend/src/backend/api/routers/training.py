"""Training flow endpoints mirroring the Telegram bot interactions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from ...services.flashcards import FlashcardService, ReviewRating, UserProfile
from ..dependencies import get_flashcard_service, get_user_profile
from .. import schemas

router = APIRouter(prefix="/training", tags=["training"])


@router.get("/next", response_model=schemas.TrainingCardModel, responses={204: {"description": "No due cards"}})
async def get_next_training_card(
    profile: UserProfile = Depends(get_user_profile),
    flashcards: FlashcardService = Depends(get_flashcard_service),
):
    """Return the next due card or 204 when none are available."""
    study_card = await flashcards.get_next_card(user_id=profile.user_id)
    if study_card is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    # Deterministically present the source side first; keep API predictable.
    prompt = study_card.card.source_text
    hidden = study_card.card.target_text
    prompt_side = "source"

    return schemas.TrainingCardModel(
        user_card_id=study_card.user_card_id,
        deck_id=study_card.deck_id,
        deck_name=study_card.deck_name,
        prompt=prompt,
        hidden=hidden,
        prompt_side=prompt_side,
        card=schemas.FlashcardModel(
            card_id=study_card.card.card_id,
            source_text=study_card.card.source_text,
            target_text=study_card.card.target_text,
            example_sentence=study_card.card.example_sentence,
            example_translation=study_card.card.example_translation,
            part_of_speech=study_card.card.part_of_speech,
        ),
    )


@router.get("/cards/{user_card_id}", response_model=schemas.TrainingCardModel)
async def get_card_by_id(
    user_card_id: int,
    profile: UserProfile = Depends(get_user_profile),
    flashcards: FlashcardService = Depends(get_flashcard_service),
) -> schemas.TrainingCardModel:
    """Return full card details for the specified user card."""
    try:
        study_card = await flashcards.get_user_card(
            user_id=profile.user_id,
            user_card_id=user_card_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return schemas.TrainingCardModel(
        user_card_id=study_card.user_card_id,
        deck_id=study_card.deck_id,
        deck_name=study_card.deck_name,
        prompt=study_card.card.source_text,
        hidden=study_card.card.target_text,
        prompt_side="source",
        card=schemas.FlashcardModel(
            card_id=study_card.card.card_id,
            source_text=study_card.card.source_text,
            target_text=study_card.card.target_text,
            example_sentence=study_card.card.example_sentence,
            example_translation=study_card.card.example_translation,
            part_of_speech=study_card.card.part_of_speech,
        ),
    )


@router.post("/cards/{user_card_id}/review", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def review_card(
    user_card_id: int,
    payload: schemas.ReviewRequest,
    profile: UserProfile = Depends(get_user_profile),
    flashcards: FlashcardService = Depends(get_flashcard_service),
) -> Response:
    """Persist the user's rating for the card."""
    try:
        rating = ReviewRating(payload.rating.value)
    except ValueError as exc:  # pragma: no cover - payload is already validated
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Некорректная оценка.") from exc

    try:
        await flashcards.record_review(
            user_id=profile.user_id,
            user_card_id=user_card_id,
            rating=rating,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
