import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { useDeckManager } from "@hooks/useDeckManager";
import { generateDeckCards } from "@api/client";

import styles from "./DecksPanel.module.css";

type View = "edit" | "create";

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
    removeCard,
    refreshCards
  } = useDeckManager();

  const [view, setView] = useState<View>("edit");
  const [newDeckName, setNewDeckName] = useState("");
  const [newDeckDescription, setNewDeckDescription] = useState("");

  const selectedDeck = useMemo(() => decks.find((deck) => deck.id === selectedDeckId) ?? null, [decks, selectedDeckId]);

  const [editName, setEditName] = useState(selectedDeck?.name ?? "");
  const [editDescription, setEditDescription] = useState(selectedDeck?.description ?? "");
  const [cardPrompt, setCardPrompt] = useState("");
  const [generatePrompt, setGeneratePrompt] = useState("");
  const [generateCount, setGenerateCount] = useState(10);
  const [isGenerating, setIsGenerating] = useState(false);
  const [recentCardIds, setRecentCardIds] = useState<number[]>([]);

  useEffect(() => {
    setEditName(selectedDeck?.name ?? "");
    setEditDescription(selectedDeck?.description ?? "");
  }, [selectedDeck?.id, selectedDeck?.name, selectedDeck?.description]);

  useEffect(() => {
    setRecentCardIds([]);
  }, [selectedDeckId]);

  const sortedCards = useMemo(() => {
    if (recentCardIds.length === 0) {
      return cards;
    }
    const recentSet = new Set(recentCardIds);
    const recent = cards.filter((card) => recentSet.has(card.user_card_id));
    const others = cards.filter((card) => !recentSet.has(card.user_card_id));
    return [...recent, ...others];
  }, [cards, recentCardIds]);

  const recentCardIdSet = useMemo(() => new Set(recentCardIds), [recentCardIds]);

  const handleRecentCardInteraction = useCallback((userCardId: number) => {
    setRecentCardIds((current) => (current.includes(userCardId) ? current.filter((id) => id !== userCardId) : current));
  }, []);

  const handleCreateDeck = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!newDeckName.trim()) {
      return;
    }
    try {
      await createDeck({ name: newDeckName.trim(), description: newDeckDescription.trim() || null });
      setNewDeckName("");
      setNewDeckDescription("");
      setView("edit");
    } catch (error) {
      console.error("Не удалось создать колоду", error);
    }
  };

  const handleUpdateDeck = async () => {
    if (!selectedDeck || !editName.trim()) {
      return;
    }
    try {
      await updateDeck(selectedDeck.id, { name: editName.trim(), description: editDescription.trim() || null });
    } catch (error) {
      console.error("Не удалось обновить колоду", error);
    }
  };

  const handleDeleteDeck = async () => {
    if (!selectedDeck || !confirm(`Удалить колоду "${selectedDeck.name}"?`)) {
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

  const handleGenerateCards = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedDeck || !generatePrompt.trim()) {
      return;
    }

    setIsGenerating(true);
    setRecentCardIds([]);
    try {
      const generatedCards = await generateDeckCards(selectedDeck.id, generatePrompt.trim(), generateCount);
      const linkedCardIds = generatedCards
        .filter((card) => card.linked_to_user)
        .map((card) => card.user_card_id);
      setGeneratePrompt("");
      // Refresh cards to show newly generated ones
      await refreshCards(selectedDeck.id);
      if (linkedCardIds.length > 0) {
        setRecentCardIds(linkedCardIds);
      }
    } catch (error) {
      console.error("Не удалось сгенерировать карточки", error);
    } finally {
      setIsGenerating(false);
    }
  };

  if (view === "create") {
    return (
      <div className={styles.panel}>
        <div className={styles.header}>
          <button className={styles.backButton} onClick={() => setView("edit")}>← Назад</button>
          <h2>Создать новую колоду</h2>
        </div>

        <form className={styles.createForm} onSubmit={handleCreateDeck}>
          <div className={styles.formRow}>
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
          <div className={styles.formRow}>
            <label htmlFor="new-deck-description">Описание</label>
            <textarea
              id="new-deck-description"
              className={styles.textarea}
              value={newDeckDescription}
              onChange={(event) => setNewDeckDescription(event.target.value)}
              placeholder="Фразы для πρωινό καφέ"
              rows={3}
            />
          </div>
          <button className={styles.primaryButton} type="submit" disabled={isSavingDeck}>
            {isSavingDeck ? "Создаём…" : "Создать колоду"}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h2>Колоды</h2>
      </div>

      {deckError && <p className={styles.error}>{deckError}</p>}

      <div className={styles.deckSelector}>
        <label htmlFor="deck-select">Колода:</label>
        <select
          id="deck-select"
          className={styles.deckSelect}
          value={selectedDeckId ?? ""}
          onChange={(e) => selectDeck(e.target.value ? Number(e.target.value) : null)}
          disabled={isLoadingDecks}
        >
          {decks.length === 0 && <option value="">Нет колод</option>}
          {decks.map((deck) => (
            <option key={deck.id} value={deck.id}>
              {deck.name} ({deck.card_count})
            </option>
          ))}
        </select>
        <button className={styles.createButton} onClick={() => setView("create")}>
          + Создать
        </button>
      </div>

      {selectedDeck && (
        <>
          <div className={styles.deckInfo}>
            <div className={styles.formRow}>
              <label htmlFor="deck-name">Название</label>
              <input
                id="deck-name"
                className={styles.inputCompact}
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                onBlur={() => void handleUpdateDeck()}
              />
            </div>
            <div className={styles.formRow}>
              <label htmlFor="deck-description">Описание</label>
              <textarea
                id="deck-description"
                className={styles.textareaCompact}
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                onBlur={() => void handleUpdateDeck()}
                rows={2}
              />
            </div>
            <button className={styles.deleteButton} onClick={() => void handleDeleteDeck()}>
              Удалить колоду
            </button>
          </div>

          <div className={styles.cardActions}>
            <form className={styles.addCardForm} onSubmit={handleCreateCard}>
              <input
                className={styles.inputCompact}
                value={cardPrompt}
                onChange={(e) => setCardPrompt(e.target.value)}
                placeholder="καλημέρα / доброе утро"
              />
              <button className={styles.addButton} type="submit" disabled={isSavingCard}>
                {isSavingCard ? "..." : "+ Добавить"}
              </button>
            </form>

            <form
              className={isGenerating ? `${styles.generateForm} ${styles.generating}` : styles.generateForm}
              onSubmit={handleGenerateCards}
            >
              <textarea
                className={styles.generatePrompt}
                value={generatePrompt}
                onChange={(e) => setGeneratePrompt(e.target.value)}
                placeholder="Введите описание для генерации"
                rows={3}
                maxLength={500}
                aria-label="Описание для генерации карточек"
                disabled={isGenerating}
              />
              <input
                type="number"
                className={styles.countInput}
                value={generateCount}
                onChange={(e) => setGenerateCount(Number(e.target.value))}
                min={5}
                max={30}
                inputMode="numeric"
                aria-label="Количество карточек для генерации"
                disabled={isGenerating}
              />
              <button
                className={isGenerating ? `${styles.generateButton} ${styles.generatingButton}` : styles.generateButton}
                type="submit"
                disabled={isGenerating}
              >
                {isGenerating ? "Генерируем..." : "✨ Сгенерировать"}
              </button>
            </form>
          </div>

          {cardError && <p className={styles.error}>{cardError}</p>}

          {isLoadingCards ? (
            <p className={styles.muted}>Загружаем карточки…</p>
          ) : sortedCards.length === 0 ? (
            <p className={styles.emptyState}>Добавь слово или сгенерируй карточки</p>
          ) : (
            <div className={styles.cardList}>
              {sortedCards.map((card) => {
                const isRecent = recentCardIdSet.has(card.user_card_id);
                const cardClassName = isRecent ? `${styles.cardItem} ${styles.cardItemRecent}` : styles.cardItem;
                const dismissRecent = () => {
                  if (isRecent) {
                    handleRecentCardInteraction(card.user_card_id);
                  }
                };
                return (
                  <article
                    key={card.user_card_id}
                    className={cardClassName}
                    onPointerEnter={dismissRecent}
                    onPointerDown={dismissRecent}
                    onTouchStart={dismissRecent}
                  >
                    <div className={styles.cardTop}>
                      <strong>{card.card.target_text}</strong>
                      <span className={styles.pos}>{card.card.part_of_speech ?? "—"}</span>
                      <button
                        className={styles.removeButton}
                        onClick={() => void removeCard(card.deck_id, card.user_card_id)}
                        disabled={isSavingCard}
                      >
                        ✕
                      </button>
                    </div>
                    <div className={styles.cardDetails}>
                      <p><em>{card.card.source_text}</em></p>
                      <p className={styles.example}>{card.card.example_sentence}</p>
                      <p className={styles.exampleTranslation}>{card.card.example_translation}</p>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </>
      )}

      {!selectedDeck && decks.length === 0 && (
        <div className={styles.emptyState}>
          <p>Создайте первую колоду, чтобы начать</p>
        </div>
      )}

      <div className={styles.footer}>
        <p>Собирай слова в тематические подборки для точечной πρακτική</p>
      </div>
    </div>
  );
}
