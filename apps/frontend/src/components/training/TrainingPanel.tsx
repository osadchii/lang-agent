import { useEffect } from "react";

import { useTrainingSession } from "@hooks/useTrainingSession";

import styles from "./TrainingPanel.module.css";

export function TrainingPanel(): JSX.Element {
  const { currentCard, isLoading, isSubmitting, isRevealed, error, loadNextCard, revealCard, reviewCard, reloadCurrentCard } =
    useTrainingSession();

  useEffect(() => {
    void loadNextCard();
  }, [loadNextCard]);

  const hasCard = Boolean(currentCard);

  return (
    <section className={styles.panel}>
      <div className={styles.header}>
        <h2>Тренировка</h2>
        <p>Повторяй в том же ритме, что и в Telegram: открой ответ и оцени, насколько хорошо вспомнил.</p>
      </div>

      {error && <p className={styles.error}>{error}</p>}

      {isLoading && <p className={styles.muted}>Получаем следующую карточку…</p>}

      {!isLoading && !hasCard && <p className={styles.muted}>Все карточки пройдены. Добавь новое слово и возвращайся.</p>}

      {hasCard && currentCard && (
        <article className={styles.cardShell}>
          <h3>{currentCard.deck_name}</h3>
          <div className={styles.prompt}>{currentCard.prompt}</div>
          <p className={styles.secondaryText}>
            Сторона подсказки: {currentCard.prompt_side === "source" ? "Русский → Ελληνικά" : "Ελληνικά → Русский"}
          </p>

          {isRevealed ? (
            <>
              <p className={styles.secondaryText}>
                <strong>{currentCard.card.target_text}</strong> · {currentCard.card.part_of_speech ?? "—"}
              </p>
              <p className={styles.secondaryText}>{currentCard.card.example_sentence}</p>
              <p className={styles.secondaryText}>{currentCard.card.example_translation}</p>
            </>
          ) : (
            <button className={styles.primaryButton} disabled={isSubmitting} onClick={revealCard}>
              Показать ответ
            </button>
          )}
        </article>
      )}

      <div className={styles.actions}>
        <button className={styles.secondaryButton} disabled={isLoading || isSubmitting} onClick={() => void loadNextCard()}>
          Пропустить
        </button>
        <button className={styles.secondaryButton} disabled={!currentCard || isSubmitting} onClick={() => void reloadCurrentCard()}>
          Поменять сторону
        </button>
        <button
          className={styles.againButton}
          disabled={!isRevealed || isSubmitting || !currentCard}
          onClick={() => void reviewCard("again")}
        >
          Ещё раз
        </button>
        <button
          className={styles.reviewButton}
          disabled={!isRevealed || isSubmitting || !currentCard}
          onClick={() => void reviewCard("review")}
        >
          Повторить позже
        </button>
        <button
          className={styles.easyButton}
          disabled={!isRevealed || isSubmitting || !currentCard}
          onClick={() => void reviewCard("easy")}
        >
          Легко
        </button>
      </div>
    </section>
  );
}
