"""Flashcard service behavior tests."""

from __future__ import annotations

import datetime as dt
import random

import pytest
from sqlalchemy import select

from backend.services.flashcards import FlashcardService, ReviewRating, UserProfile
from backend.services.llm import FlashcardContent, FlashcardGenerator, LLMClient
from backend.services.storage.database import Database
from backend.services.storage.models import CardRecord, DeckRecord, UserCardRecord


class StubFlashcardGenerator(FlashcardGenerator):
    """Deterministic flashcard generator for tests."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def generate_flashcard(self, *, prompt_word: str) -> FlashcardContent:
        self.calls.append(prompt_word)
        return FlashcardContent(
            source_text=prompt_word.strip(),
            target_text=f"ο {prompt_word.strip()}",
            example_sentence="Παράδειγμα πρότασης.",
            example_translation="Пример предложения.",
            part_of_speech="noun",
            extra={"stub": True},
        )


class StubLLMClient(LLMClient):
    """Deterministic LLM client for tests."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def generate_reply(
        self,
        *,
        user_message: str,
        history = None,
    ) -> str:
        self.calls.append(user_message)
        return "καλημέρα\nφαγητό\nταξίδι"


@pytest.mark.asyncio
async def test_add_words_creates_cards_and_links_user(tmp_path) -> None:
    """Adding words should create canonical cards and user-specific links."""
    database = Database(f"sqlite+aiosqlite:///{tmp_path/'flashcards.db'}")
    await database.initialize()

    generator = StubFlashcardGenerator()
    llm_client = StubLLMClient()
    service = FlashcardService(
        database=database,
        generator=generator,
        llm=llm_client,
        random_source=random.Random(0),
    )

    profile = UserProfile(user_id=1, username="learner", first_name="Test", last_name=None)
    results = await service.add_words(profile, ["привет"])

    assert len(results) == 1
    result = results[0]
    assert result.created_card is True
    assert result.linked_to_user is True
    assert result.card is not None
    assert result.card.target_text.startswith("ο ")
    assert result.user_card_id is not None

    async with database.session() as session:
        cards = (await session.execute(select(CardRecord))).scalars().all()
        user_cards = (await session.execute(select(UserCardRecord))).scalars().all()
        decks = (await session.execute(select(DeckRecord))).scalars().all()

    assert len(cards) == 1
    assert cards[0].example_sentence == "Παράδειγμα πρότασης."

    assert len(decks) == 1
    assert decks[0].slug == "default"

    assert len(user_cards) == 1
    assert user_cards[0].user_id == profile.user_id
    assert user_cards[0].review_count == 0

    await database.dispose()


@pytest.mark.asyncio
async def test_add_words_reuses_existing_cards(tmp_path) -> None:
    """Adding the same word twice should reuse the canonical card."""
    database = Database(f"sqlite+aiosqlite:///{tmp_path/'flashcards-reuse.db'}")
    await database.initialize()

    generator = StubFlashcardGenerator()
    llm_client = StubLLMClient()
    service = FlashcardService(
        database=database,
        generator=generator,
        llm=llm_client,
        random_source=random.Random(1),
    )

    profile = UserProfile(user_id=22, username=None, first_name="User", last_name=None)
    await service.add_words(profile, ["привет"])
    reuse_results = await service.add_words(profile, ["Привет"])

    assert len(generator.calls) == 1  # second call reused cached card
    reuse = reuse_results[0]
    assert reuse.created_card is False
    assert reuse.reused_existing_card is True
    assert reuse.linked_to_user is False

    await database.dispose()


@pytest.mark.asyncio
async def test_review_schedule_updates_interval(tmp_path) -> None:
    """Recording reviews should adjust intervals according to rating."""
    database = Database(f"sqlite+aiosqlite:///{tmp_path/'flashcards-review.db'}")
    await database.initialize()

    generator = StubFlashcardGenerator()
    llm_client = StubLLMClient()
    service = FlashcardService(
        database=database,
        generator=generator,
        llm=llm_client,
        random_source=random.Random(2),
    )

    profile = UserProfile(user_id=7, username="tester", first_name="Test", last_name=None)
    results = await service.add_words(profile, ["привет"])
    user_card_record_id = results[0].user_card_id
    assert user_card_record_id is not None

    await service.record_review(
        user_id=profile.user_id,
        user_card_id=user_card_record_id,
        rating=ReviewRating.AGAIN,
    )

    async with database.session() as session:
        updated = await session.get(UserCardRecord, user_card_record_id)

    assert updated is not None
    assert updated.interval_minutes == 10
    assert updated.review_count == 1
    assert updated.last_rating == ReviewRating.AGAIN.value

    scheduled = updated.next_review_at
    assert scheduled is not None
    if scheduled.tzinfo is None:
        scheduled = scheduled.replace(tzinfo=dt.timezone.utc)
    assert scheduled > dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)

    await database.dispose()


@pytest.mark.asyncio
async def test_deck_crud_and_card_generation(tmp_path) -> None:
    """Deck creation, card generation, and removal should work end-to-end."""
    database = Database(f"sqlite+aiosqlite:///{tmp_path/'flashcards-decks.db'}")
    await database.initialize()

    generator = StubFlashcardGenerator()
    llm_client = StubLLMClient()
    service = FlashcardService(
        database=database,
        generator=generator,
        llm=llm_client,
        random_source=random.Random(3),
    )

    profile = UserProfile(user_id=77, username="deckster", first_name="Deck", last_name=None)

    deck = await service.create_deck(profile, name="Morning Practice", description="Warm-up phrases")
    assert deck.slug.startswith("morning-practice")

    duplicate = await service.create_deck(profile, name="Morning Practice", description=None)
    assert duplicate.slug != deck.slug

    await service.delete_deck(profile, deck_id=duplicate.deck_id)

    decks = await service.list_user_decks(profile)
    assert len(decks) == 1
    assert decks[0].deck_id == deck.deck_id

    creation = await service.create_card_for_deck(profile, deck_id=deck.deck_id, prompt_text="привет")
    assert creation.card is not None
    assert creation.user_card_id is not None

    cards = await service.list_deck_cards(profile, deck_id=deck.deck_id)
    assert len(cards) == 1
    assert cards[0].card.source_text == "привет"

    await service.remove_card_from_deck(profile, deck_id=deck.deck_id, user_card_id=creation.user_card_id)
    cards_after_remove = await service.list_deck_cards(profile, deck_id=deck.deck_id)
    assert cards_after_remove == []

    await service.delete_deck(profile, deck_id=deck.deck_id)
    decks_after_delete = await service.list_user_decks(profile)
    assert decks_after_delete == []

    await database.dispose()


@pytest.mark.asyncio
async def test_active_deck_management(tmp_path) -> None:
    """Setting and getting active deck should work correctly."""
    database = Database(f"sqlite+aiosqlite:///{tmp_path/'flashcards-active.db'}")
    await database.initialize()

    generator = StubFlashcardGenerator()
    llm_client = StubLLMClient()
    service = FlashcardService(
        database=database,
        generator=generator,
        llm=llm_client,
        random_source=random.Random(4),
    )

    profile = UserProfile(user_id=100, username="deckuser", first_name="Deck", last_name="User")

    # Initially no active deck
    active = await service.get_active_deck(profile)
    assert active is None

    # Create two decks
    deck1 = await service.create_deck(profile, name="Greek Basics")
    deck2 = await service.create_deck(profile, name="Greek Advanced")

    # Set deck1 as active
    await service.set_active_deck(profile, deck_id=deck1.deck_id)
    active = await service.get_active_deck(profile)
    assert active is not None
    assert active.deck_id == deck1.deck_id
    assert active.name == "Greek Basics"

    # Change to deck2
    await service.set_active_deck(profile, deck_id=deck2.deck_id)
    active = await service.get_active_deck(profile)
    assert active is not None
    assert active.deck_id == deck2.deck_id
    assert active.name == "Greek Advanced"

    # Delete active deck - should clear active_deck_id
    await service.delete_deck(profile, deck_id=deck2.deck_id)
    active = await service.get_active_deck(profile)
    assert active is None

    await database.dispose()


@pytest.mark.asyncio
async def test_add_words_uses_active_deck(tmp_path) -> None:
    """Words should be added to the active deck when specified."""
    database = Database(f"sqlite+aiosqlite:///{tmp_path/'flashcards-add-active.db'}")
    await database.initialize()

    generator = StubFlashcardGenerator()
    llm_client = StubLLMClient()
    service = FlashcardService(
        database=database,
        generator=generator,
        llm=llm_client,
        random_source=random.Random(5),
    )

    profile = UserProfile(user_id=101, username="learner2", first_name="Test", last_name="User")

    # Create two decks
    deck1 = await service.create_deck(profile, name="Travel Greek")
    deck2 = await service.create_deck(profile, name="Business Greek")

    # Set deck1 as active
    await service.set_active_deck(profile, deck_id=deck1.deck_id)

    # Add word without specifying deck_id - should use active deck
    results = await service.add_words(profile, ["γεια"])
    assert len(results) == 1
    assert results[0].created_card is True

    # Check word is in deck1
    cards_deck1 = await service.list_deck_cards(profile, deck_id=deck1.deck_id)
    cards_deck2 = await service.list_deck_cards(profile, deck_id=deck2.deck_id)
    assert len(cards_deck1) == 1
    assert len(cards_deck2) == 0
    assert cards_deck1[0].card.source_text == "γεια"

    # Change active deck to deck2
    await service.set_active_deck(profile, deck_id=deck2.deck_id)

    # Add another word - should go to deck2
    results = await service.add_words(profile, ["καλημέρα"])
    assert len(results) == 1

    cards_deck1_after = await service.list_deck_cards(profile, deck_id=deck1.deck_id)
    cards_deck2_after = await service.list_deck_cards(profile, deck_id=deck2.deck_id)
    assert len(cards_deck1_after) == 1  # still only one
    assert len(cards_deck2_after) == 1  # new word here
    assert cards_deck2_after[0].card.source_text == "καλημέρα"

    await database.dispose()


@pytest.mark.asyncio
async def test_get_next_card_uses_active_deck(tmp_path) -> None:
    """get_next_card should return cards from the active deck."""
    database = Database(f"sqlite+aiosqlite:///{tmp_path/'flashcards-next-active.db'}")
    await database.initialize()

    generator = StubFlashcardGenerator()
    llm_client = StubLLMClient()
    service = FlashcardService(
        database=database,
        generator=generator,
        llm=llm_client,
        random_source=random.Random(6),
    )

    profile = UserProfile(user_id=102, username="reviewer", first_name="Review", last_name="User")

    # Create two decks with cards
    deck1 = await service.create_deck(profile, name="Deck One")
    deck2 = await service.create_deck(profile, name="Deck Two")

    # Add words to deck1
    await service.add_words(profile, ["γεια"], deck_id=deck1.deck_id)
    # Add words to deck2
    await service.add_words(profile, ["καλημέρα"], deck_id=deck2.deck_id)

    # Set deck1 as active
    await service.set_active_deck(profile, deck_id=deck1.deck_id)

    # Get next card - should come from deck1
    card = await service.get_next_card(user_id=profile.user_id)
    assert card is not None
    assert card.deck_id == deck1.deck_id
    assert card.card.source_text == "γεια"

    # Change active deck to deck2
    await service.set_active_deck(profile, deck_id=deck2.deck_id)

    # Get next card - should come from deck2
    card = await service.get_next_card(user_id=profile.user_id)
    assert card is not None
    assert card.deck_id == deck2.deck_id
    assert card.card.source_text == "καλημέρα"

    await database.dispose()
