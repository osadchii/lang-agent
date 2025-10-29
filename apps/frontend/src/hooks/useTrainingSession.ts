import { useCallback, useMemo, useState } from "react";

import { fetchNextTrainingCard, submitReview } from "@api/client";
import type { RatingValue, TrainingCard } from "@api/types";

interface TrainingSessionState {
  currentCard: TrainingCard | null;
  isLoading: boolean;
  isSubmitting: boolean;
  isRevealed: boolean;
  error: string | null;
  loadNextCard: () => Promise<void>;
  revealCard: () => void;
  reviewCard: (rating: RatingValue) => Promise<void>;
  reloadCurrentCard: () => Promise<void>;
}

export function useTrainingSession(): TrainingSessionState {
  const [currentCard, setCurrentCard] = useState<TrainingCard | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRevealed, setIsRevealed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadNextCard = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const card = await fetchNextTrainingCard();
      setCurrentCard(card);
      setIsRevealed(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось получить карточку.");
      setCurrentCard(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const revealCard = useCallback(() => {
    setIsRevealed(true);
  }, []);

  const reviewCard = useCallback(
    async (rating: RatingValue) => {
      if (!currentCard) {
        return;
      }
      setIsSubmitting(true);
      setError(null);
      try {
        await submitReview(currentCard.user_card_id, rating);
        await loadNextCard();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Не удалось сохранить оценку.");
      } finally {
        setIsSubmitting(false);
      }
    },
    [currentCard, loadNextCard]
  );

  const reloadCurrentCard = useCallback(() => {
    setCurrentCard((card) => {
      if (!card) {
        return card;
      }
      const shouldSwap = Math.random() < 0.5;
      if (!shouldSwap) {
        return { ...card, prompt: card.prompt, hidden: card.hidden };
      }
      const isSourcePrompt = card.prompt_side === "source";
      return {
        ...card,
        prompt: isSourcePrompt ? card.card.target_text : card.card.source_text,
        hidden: isSourcePrompt ? card.card.source_text : card.card.target_text,
        prompt_side: isSourcePrompt ? "target" : "source"
      };
    });
    setIsRevealed(false);
  }, []);

  return useMemo(
    () => ({
      currentCard,
      isLoading,
      isSubmitting,
      isRevealed,
      error,
      loadNextCard,
      revealCard,
      reviewCard,
      reloadCurrentCard
    }),
    [currentCard, error, isLoading, isRevealed, isSubmitting, loadNextCard, revealCard, reloadCurrentCard, reviewCard]
  );
}
