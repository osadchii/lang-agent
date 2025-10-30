import { useEffect, useState } from "react";

import { useTrainingSession } from "@hooks/useTrainingSession";
import { useDeckManager } from "@hooks/useDeckManager";

import styles from "./TrainingPanel.module.css";

function translatePartOfSpeech(pos: string | null): string {
  if (!pos) return "—";

  const translations: Record<string, string> = {
    "noun": "существительное",
    "verb": "глагол",
    "adjective": "прилагательное",
    "adverb": "наречие",
    "pronoun": "местоимение",
    "preposition": "предлог",
    "conjunction": "союз",
    "interjection": "междометие",
    "particle": "частица",
    "numeral": "числительное",
  };

  return translations[pos.toLowerCase()] || pos;
}

export function TrainingPanel(): JSX.Element {
  const { currentCard, isLoading, isSubmitting, error, selectedDeckId, setSelectedDeckId, loadNextCard, reviewCard } =
    useTrainingSession();
  const { decks } = useDeckManager();

  const [isFlipped, setIsFlipped] = useState(false);
  const [hasFlippedOnce, setHasFlippedOnce] = useState(false);

  useEffect(() => {
    void loadNextCard();
  }, [loadNextCard]);

  // Reset flip state when card changes
  useEffect(() => {
    setIsFlipped(false);
    setHasFlippedOnce(false);
  }, [currentCard?.user_card_id]);

  const handleFlipCard = () => {
    setIsFlipped(!isFlipped);
    if (!hasFlippedOnce) {
      setHasFlippedOnce(true);
    }
  };

  const handleDeckChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value;
    const newDeckId = value === "" ? null : Number(value);
    setSelectedDeckId(newDeckId);
  };

  const hasCard = Boolean(currentCard);
  const canReview = hasCard && hasFlippedOnce && !isSubmitting;

  // Determine what to show on each side based on prompt_side
  const frontText = currentCard?.prompt ?? "";
  const backText = currentCard?.hidden ?? "";
  const frontExample = currentCard?.prompt_side === "source"
    ? currentCard?.card.example_translation
    : currentCard?.card.example_sentence;
  const backExample = currentCard?.prompt_side === "source"
    ? currentCard?.card.example_sentence
    : currentCard?.card.example_translation;

  return (
    <section className={styles.panel}>
      <div className={styles.header}>
        <h2>Тренировка</h2>
      </div>

      <div className={styles.deckSelector}>
        <label htmlFor="deck-select" className={styles.deckLabel}>
          Колода:
        </label>
        <select
          id="deck-select"
          className={styles.deckSelect}
          value={selectedDeckId ?? ""}
          onChange={handleDeckChange}
          disabled={isLoading || isSubmitting}
        >
          <option value="">Все колоды</option>
          {decks.map((deck) => (
            <option key={deck.id} value={deck.id}>
              {deck.name} ({deck.due_count})
            </option>
          ))}
        </select>
      </div>

      {error && <p className={styles.error}>{error}</p>}

      {isLoading && <p className={styles.muted}>Загружаем следующую карточку…</p>}

      {!isLoading && !hasCard && <p className={styles.muted}>Карточки закончились. Откройте другие колоды в каталоге.</p>}

      {hasCard && currentCard && (
        <div className={styles.cardLayout}>
          <div className={`${styles.cardContainer} ${isFlipped ? styles.flipped : ""}`}>
            <article className={`${styles.cardShell} ${styles.cardFront}`}>
              <header className={styles.cardHeader}>
                <h3>{currentCard.deck_name}</h3>
                <button
                  type="button"
                  className={styles.skipButton}
                  disabled={isLoading || isSubmitting}
                  onClick={() => void loadNextCard()}
                >
                  Пропустить
                </button>
              </header>

              <div className={styles.cardBody}>
                <div className={styles.prompt}>{frontText}</div>
                {frontExample && (
                  <p className={styles.exampleText}>{frontExample}</p>
                )}
                {currentCard.card.part_of_speech && (
                  <span className={styles.partOfSpeech}>{translatePartOfSpeech(currentCard.card.part_of_speech)}</span>
                )}
              </div>

              <div className={styles.cardFooter}>
                <button className={styles.primaryButton} disabled={isSubmitting} onClick={handleFlipCard}>
                  Перевернуть карточку
                </button>
              </div>
            </article>

            <article className={`${styles.cardShell} ${styles.cardBack}`}>
              <header className={styles.cardHeader}>
                <h3>{currentCard.deck_name}</h3>
                <button
                  type="button"
                  className={styles.skipButton}
                  disabled={isLoading || isSubmitting}
                  onClick={() => void loadNextCard()}
                >
                  Пропустить
                </button>
              </header>

              <div className={styles.cardBody}>
                <div className={styles.prompt}>{backText}</div>
                {backExample && (
                  <p className={styles.exampleText}>{backExample}</p>
                )}
                {currentCard.card.part_of_speech && (
                  <span className={styles.partOfSpeech}>{translatePartOfSpeech(currentCard.card.part_of_speech)}</span>
                )}
              </div>

              <div className={styles.cardFooter}>
                <button className={styles.primaryButton} disabled={isSubmitting} onClick={handleFlipCard}>
                  Перевернуть карточку
                </button>
              </div>
            </article>
          </div>

          <div className={styles.actions}>
            <button className={styles.againButton} disabled={!canReview} onClick={() => void reviewCard("again")}>
              Еще раз
            </button>
            <button className={styles.reviewButton} disabled={!canReview} onClick={() => void reviewCard("review")}>
              Повторить
            </button>
            <button className={styles.easyButton} disabled={!canReview} onClick={() => void reviewCard("easy")}>
              Легко
            </button>
          </div>
        </div>
      )}

      <div className={styles.footer}>
        <p>Закрепляйте лексику здесь и в Telegram: короткие сессии с карточками, адаптированные под ваш ритм.</p>
      </div>
    </section>
  );
}
