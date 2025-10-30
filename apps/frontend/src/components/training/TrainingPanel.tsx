import { useEffect } from "react";

import { useTrainingSession } from "@hooks/useTrainingSession";

import styles from "./TrainingPanel.module.css";

export function TrainingPanel(): JSX.Element {
  const { currentCard, isLoading, isSubmitting, isRevealed, error, loadNextCard, revealCard, reviewCard } =
    useTrainingSession();

  useEffect(() => {
    void loadNextCard();
  }, [loadNextCard]);

  const hasCard = Boolean(currentCard);
  const canReview = Boolean(currentCard) && isRevealed && !isSubmitting;

  return (
    <section className={styles.panel}>
      <div className={styles.header}>
        <h2>Тренировка</h2>
        <p>Закрепляйте лексику здесь и в Telegram: короткие сессии с карточками, адаптированные под ваш ритм.</p>
      </div>

      {error && <p className={styles.error}>{error}</p>}

      {isLoading && <p className={styles.muted}>Загружаем следующую карточку…</p>}

      {!isLoading && !hasCard && <p className={styles.muted}>Карточки закончились. Откройте другие колоды в каталоге.</p>}

      {hasCard && currentCard && (
        <div className={styles.cardLayout}>
          <article className={styles.cardShell}>
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
              <div className={styles.prompt}>{currentCard.prompt}</div>
              <p className={styles.secondaryText}>
                Сторона карточки: {currentCard.prompt_side === "source" ? "Лицевая — вопрос" : "Обратная — перевод"}
              </p>

              {isRevealed ? (
                <div className={styles.revealBlock}>
                  <p className={styles.translation}>
                    <strong>{currentCard.card.target_text}</strong>
                    <span className={styles.partOfSpeech}>{currentCard.card.part_of_speech ?? "—"}</span>
                  </p>
                  <p className={styles.secondaryText}>{currentCard.card.example_sentence}</p>
                  <p className={styles.secondaryText}>{currentCard.card.example_translation}</p>
                </div>
              ) : (
                <button className={styles.primaryButton} disabled={isSubmitting} onClick={revealCard}>
                  Показать ответ
                </button>
              )}
            </div>
          </article>

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
    </section>
  );
}
