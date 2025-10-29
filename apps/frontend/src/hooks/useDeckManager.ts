import { useCallback, useEffect, useMemo, useState } from "react";

import {
  createDeck,
  createDeckCard,
  deleteDeck,
  fetchDeckCards,
  fetchDecks,
  removeDeckCard,
  updateDeck
} from "@api/client";
import type { DeckCard, DeckSummary, FlashcardCreationResponse } from "@api/types";

interface DeckManagerState {
  decks: DeckSummary[];
  selectedDeckId: number | null;
  cards: DeckCard[];
  deckError: string | null;
  cardError: string | null;
  isLoadingDecks: boolean;
  isLoadingCards: boolean;
  isSavingDeck: boolean;
  isSavingCard: boolean;
  selectDeck: (deckId: number | null) => void;
  createDeck: (input: { name: string; description?: string | null }) => Promise<void>;
  updateDeck: (deckId: number, input: { name?: string | null; description?: string | null }) => Promise<void>;
  deleteDeck: (deckId: number) => Promise<void>;
  createCard: (deckId: number, prompt: string) => Promise<FlashcardCreationResponse>;
  removeCard: (deckId: number, userCardId: number) => Promise<void>;
  refreshDecks: () => Promise<void>;
  refreshCards: (deckId: number) => Promise<void>;
}

export function useDeckManager(): DeckManagerState {
  const [decks, setDecks] = useState<DeckSummary[]>([]);
  const [selectedDeckId, setSelectedDeckId] = useState<number | null>(null);
  const [cards, setCards] = useState<DeckCard[]>([]);

  const [deckError, setDeckError] = useState<string | null>(null);
  const [cardError, setCardError] = useState<string | null>(null);
  const [isLoadingDecks, setIsLoadingDecks] = useState(true);
  const [isLoadingCards, setIsLoadingCards] = useState(false);
  const [isSavingDeck, setIsSavingDeck] = useState(false);
  const [isSavingCard, setIsSavingCard] = useState(false);

  const loadDecks = useCallback(async () => {
    setIsLoadingDecks(true);
    setDeckError(null);
    try {
      const data = await fetchDecks();
      setDecks(data);
      if (data.length > 0) {
        setSelectedDeckId((current) => current ?? data[0].id);
      } else {
        setSelectedDeckId(null);
        setCards([]);
      }
    } catch (error) {
      setDeckError(error instanceof Error ? error.message : "Не удалось загрузить колоды.");
    } finally {
      setIsLoadingDecks(false);
    }
  }, []);

  const loadCards = useCallback(
    async (deckId: number) => {
      setIsLoadingCards(true);
      setCardError(null);
      try {
        const data = await fetchDeckCards(deckId);
        setCards(data);
      } catch (error) {
        setCardError(error instanceof Error ? error.message : "Не удалось загрузить карточки.");
        setCards([]);
      } finally {
        setIsLoadingCards(false);
      }
    },
    []
  );

  useEffect(() => {
    void loadDecks();
  }, [loadDecks]);

  useEffect(() => {
    if (selectedDeckId === null) {
      setCards([]);
      return;
    }
    void loadCards(selectedDeckId);
  }, [selectedDeckId, loadCards]);

  const handleCreateDeck = useCallback(
    async (input: { name: string; description?: string | null }) => {
      setIsSavingDeck(true);
      setDeckError(null);
      try {
        const deck = await createDeck(input);
        setDecks((current) => [...current, deck]);
        setSelectedDeckId(deck.id);
      } catch (error) {
        setDeckError(error instanceof Error ? error.message : "Не удалось создать колоду.");
        throw error;
      } finally {
        setIsSavingDeck(false);
      }
    },
    []
  );

  const handleUpdateDeck = useCallback(
    async (deckId: number, input: { name?: string | null; description?: string | null }) => {
      setIsSavingDeck(true);
      setDeckError(null);
      try {
        const updated = await updateDeck(deckId, input);
        setDecks((current) => current.map((deck) => (deck.id === deckId ? updated : deck)));
      } catch (error) {
        setDeckError(error instanceof Error ? error.message : "Не удалось обновить колоду.");
        throw error;
      } finally {
        setIsSavingDeck(false);
      }
    },
    []
  );

  const handleDeleteDeck = useCallback(async (deckId: number) => {
      setIsSavingDeck(true);
      setDeckError(null);
      try {
        await deleteDeck(deckId);
        setDecks((current) => {
          const updated = current.filter((deck) => deck.id !== deckId);
          setSelectedDeckId((selected) => {
            if (selected !== deckId) {
              return selected;
            }
            return updated.length > 0 ? updated[0].id : null;
          });
          return updated;
        });
        setCards((current) => current.filter((card) => card.deck_id !== deckId));
      } catch (error) {
        setDeckError(error instanceof Error ? error.message : "Не удалось удалить колоду.");
        throw error;
      } finally {
        setIsSavingDeck(false);
      }
    }, []);

  const handleCreateCard = useCallback(
    async (deckId: number, prompt: string) => {
      setIsSavingCard(true);
      setCardError(null);
      try {
        const result = await createDeckCard(deckId, prompt);
        await loadCards(deckId);
        setDecks((current) =>
          current.map((deck) =>
            deck.id === deckId
              ? {
                  ...deck,
                  card_count: deck.card_count + (result.linked_to_user ? 1 : 0),
                  due_count: deck.due_count + (result.linked_to_user ? 1 : 0)
                }
              : deck
          )
        );
        return result;
      } catch (error) {
        setCardError(error instanceof Error ? error.message : "Не удалось создать карточку.");
        throw error;
      } finally {
        setIsSavingCard(false);
      }
    },
    [loadCards]
  );

  const handleRemoveCard = useCallback(
    async (deckId: number, userCardId: number) => {
      setIsSavingCard(true);
      setCardError(null);
      try {
        await removeDeckCard(deckId, userCardId);
        setCards((current) => current.filter((card) => card.user_card_id !== userCardId));
        setDecks((current) =>
          current.map((deck) =>
            deck.id === deckId
              ? {
                  ...deck,
                  card_count: Math.max(deck.card_count - 1, 0),
                  due_count: Math.max(deck.due_count - 1, 0)
                }
              : deck
          )
        );
      } catch (error) {
        setCardError(error instanceof Error ? error.message : "Не удалось удалить карточку.");
        throw error;
      } finally {
        setIsSavingCard(false);
      }
    },
    []
  );

  const refreshDecks = useCallback(async () => {
    await loadDecks();
  }, [loadDecks]);

  const refreshCards = useCallback(
    async (deckId: number) => {
      await loadCards(deckId);
    },
    [loadCards]
  );

  const state: DeckManagerState = useMemo(
    () => ({
      decks,
      selectedDeckId,
      cards,
      deckError,
      cardError,
      isLoadingDecks,
      isLoadingCards,
      isSavingDeck,
      isSavingCard,
      selectDeck: setSelectedDeckId,
      createDeck: handleCreateDeck,
      updateDeck: handleUpdateDeck,
      deleteDeck: handleDeleteDeck,
      createCard: handleCreateCard,
      removeCard: handleRemoveCard,
      refreshDecks,
      refreshCards
    }),
    [
      cards,
      deckError,
      decks,
      handleCreateCard,
      handleCreateDeck,
      handleDeleteDeck,
      handleRemoveCard,
      handleUpdateDeck,
      isLoadingCards,
      isLoadingDecks,
      isSavingCard,
      isSavingDeck,
      refreshCards,
      refreshDecks,
      selectedDeckId
    ]
  );

  return state;
}
