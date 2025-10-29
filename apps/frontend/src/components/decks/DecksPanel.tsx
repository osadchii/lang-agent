import { FormEvent, useEffect, useMemo, useState } from "react";

import { useDeckManager } from "@hooks/useDeckManager";

import styles from "./DecksPanel.module.css";

export function DecksPanel(): JSX.Element {
  const {
    decks,
    selectedDeckId,
    selectDeck,
    cards,
    deckError,
    cardError,
    isLoadingDecks,
    isLoadingCards,
    isSavingDeck,
    isSavingCard,
    createDeck,
    updateDeck,
    deleteDeck,
    createCard,
    removeCard
  } = useDeckManager();

  const [newDeckName, setNewDeckName] = useState("");
  const [newDeckDescription, setNewDeckDescription] = useState("");

  const selectedDeck = useMemo(() => decks.find((deck) => deck.id === selectedDeckId) ?? null, [decks, selectedDeckId]);

  const [editName, setEditName] = useState(selectedDeck?.name ?? "");
  const [editDescription, setEditDescription] = useState(selectedDeck?.description ?? "");
  const [cardPrompt, setCardPrompt] = useState("");

  useEffect(() => {
    setEditName(selectedDeck?.name ?? "");
    setEditDescription(selectedDeck?.description ?? "");
    setCardPrompt("");
  }, [selectedDeck?.id, selectedDeck?.name, selectedDeck?.description]);

  const handleCreateDeck = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!newDeckName.trim()) {
      return;
    }
    try {
      await createDeck({ name: newDeckName.trim(), description: newDeckDescription.trim() || null });
      setNewDeckName("");
      setNewDeckDescription("");
    } catch (error) {
      console.error("Не удалось создать колоду", error);
    }
  };

  const handleUpdateDeck = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedDeck) {
      return;
    }
    if (!editName.trim()) {
      return;
    }
    try {
      await updateDeck(selectedDeck.id, { name: editName.trim(), description: editDescription.trim() || null });
    } catch (error) {
      console.error("Не удалось обновить колоду", error);
    }
  };

  const handleDeleteDeck = async () => {
    if (!selectedDeck) {
      return;
    }
    try {
      await deleteDeck(selectedDeck.id);
    } catch (error) {
      console.error("Не удалось удалить колоду", error);
    }
  };

  const handleCreateCard = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedDeck || !cardPrompt.trim()) {
      return;
    }
    try {
      await createCard(selectedDeck.id, cardPrompt.trim());
      setCardPrompt("");
    } catch (error) {
      console.error("Не удалось создать карточку", error);
    }
  };

  return (
    <div className={styles.panel}>
      <section className={styles.section}>
        <header>
          <h2>Колоды</h2>
          <p className={styles.muted}>Собирай слова в тематические подборки для точечной πρακτική.</p>
        </header>
        {deckError && <p className={styles.error}>{deckError}</p>}
        {isLoadingDecks ? (
          <p className={styles.muted}>Загружаем колоды…</p>
        ) : decks.length === 0 ? (
          <p className={styles.emptyState}>Начни с первой колоды.</p>
        ) : (
          <div className={styles.deckList}>
            {decks.map((deck) => (
              <button
                key={deck.id}
                type="button"
                className={`${styles.deckButton} ${deck.id === selectedDeckId ? styles.deckButtonActive : ""}`}
                onClick={() => selectDeck(deck.id)}
              >
                <strong>{deck.name}</strong>
                {deck.description && <p className={styles.muted}>{deck.description}</p>}
                <div className={styles.deckMeta}>
                  <span>{deck.card_count} карточек</span>
                  <span>{deck.due_count} к повторению</span>
                </div>
              </button>
            ))}
          </div>
        )}
        <hr className={styles.spacer} />
        <form className={styles.form} onSubmit={handleCreateDeck}>
          <h3>Создать колоду</h3>
          <div className={styles.formGroup}>
            <label htmlFor="new-deck-name">Название</label>
            <input
              id="new-deck-name"
              className={styles.input}
              value={newDeckName}
              onChange={(event) => setNewDeckName(event.target.value)}
              placeholder="Утренний ρυθμός"
              required
            />
          </div>
          <div className={styles.formGroup}>
            <label htmlFor="new-deck-description">Описание</label>
            <textarea
              id="new-deck-description"
              className={styles.textarea}
              value={newDeckDescription}
              onChange={(event) => setNewDeckDescription(event.target.value)}
              placeholder="Фразы для πρωινό καφέ и новых знакомых."
            />
          </div>
          <div className={styles.actions}>
            <button className={styles.primaryButton} type="submit" disabled={isSavingDeck}>
              {isSavingDeck ? "Создаём…" : "Добавить колоду"}
            </button>
          </div>
        </form>
      </section>

      <section className={styles.section}>
        <header>
          <h2>Детали колоды</h2>
          <p className={styles.muted}>Генерируй карточки через ИИ, обновляй описания и очищай устаревшие записи.</p>
        </header>
        {selectedDeck ? (
          <>
            <form className={styles.form} onSubmit={handleUpdateDeck}>
              <div className={styles.formGroup}>
                <label htmlFor="deck-name">Название</label>
                <input
                  id="deck-name"
                  className={styles.input}
                  value={editName}
                  onChange={(event) => setEditName(event.target.value)}
                  required
                />
              </div>
              <div className={styles.formGroup}>
                <label htmlFor="deck-description">Описание</label>
                <textarea
                  id="deck-description"
                  className={styles.textarea}
                  value={editDescription}
                  onChange={(event) => setEditDescription(event.target.value)}
                  placeholder="Добавь контекст, например любимый καφές или настроение."
                />
              </div>
              <div className={styles.actions}>
                <button className={styles.primaryButton} type="submit" disabled={isSavingDeck}>
                  {isSavingDeck ? "Сохраняем…" : "Сохранить изменения"}
                </button>
                <button className={styles.dangerButton} type="button" onClick={() => void handleDeleteDeck()} disabled={isSavingDeck}>
                  Удалить колоду
                </button>
              </div>
            </form>

            <hr className={styles.spacer} />

            <form className={styles.form} onSubmit={handleCreateCard}>
              <h3>Создать карточку</h3>
              <div className={styles.formGroup}>
                <label htmlFor="card-prompt">Слово или фраза (русский или ελληνικά)</label>
                <input
                  id="card-prompt"
                  className={styles.input}
                  value={cardPrompt}
                  onChange={(event) => setCardPrompt(event.target.value)}
                  placeholder="καλημέρα / доброе утро"
                  required
                />
              </div>
              <div className={styles.actions}>
                <button className={styles.primaryButton} type="submit" disabled={isSavingCard}>
                  {isSavingCard ? "Генерируем…" : "Сгенерировать карточку"}
                </button>
              </div>
            </form>

            {cardError && <p className={styles.error}>{cardError}</p>}
            {isLoadingCards ? (
              <p className={styles.muted}>Загружаем карточки…</p>
            ) : cards.length === 0 ? (
              <p className={styles.emptyState}>Добавь слово, чтобы заполнить колоду.</p>
            ) : (
              <div className={styles.cardList}>
                {cards.map((card) => (
                  <article key={card.user_card_id} className={styles.cardItem}>
                    <div className={styles.cardHeader}>
                      <strong>{card.card.target_text}</strong>
                      <button
                        type="button"
                        className={styles.secondaryButton}
                        disabled={isSavingCard}
                        onClick={async () => {
                          try {
                            await removeCard(card.deck_id, card.user_card_id);
                          } catch (error) {
                            console.error("Не удалось удалить карточку", error);
                          }
                        }}
                      >
                        Удалить
                      </button>
                    </div>
                    <div className={styles.cardExample}>
                      <p>
                        <em>{card.card.source_text}</em> · {card.card.part_of_speech ?? "—"}
                      </p>
                      <p>{card.card.example_sentence}</p>
                      <p className={styles.muted}>{card.card.example_translation}</p>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </>
        ) : (
          <p className={styles.emptyState}>Выбери колоду, чтобы редактировать детали.</p>
        )}
      </section>
    </div>
  );
}
