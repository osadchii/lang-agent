import { useState } from "react";

import { DecksPanel } from "@components/decks/DecksPanel";
import { TrainingPanel } from "@components/training/TrainingPanel";

import styles from "./AppRoot.module.css";

type Section = "training" | "decks";

export function App(): JSX.Element {
  const [activeSection, setActiveSection] = useState<Section>("training");

  return (
    <div className={styles.appShell}>
      <main className={styles.main}>{activeSection === "training" ? <TrainingPanel /> : <DecksPanel />}</main>

      <footer className={styles.footer}>
        <nav className={styles.navigation} aria-label="Основные разделы">
          <button
            type="button"
            className={`${styles.navButton} ${activeSection === "training" ? styles.navButtonActive : ""}`}
            onClick={() => setActiveSection("training")}
          >
            Тренировка
          </button>
          <button
            type="button"
            className={`${styles.navButton} ${activeSection === "decks" ? styles.navButtonActive : ""}`}
            onClick={() => setActiveSection("decks")}
          >
            Колоды
          </button>
        </nav>

        <header className={styles.header}>
          <h1 className={styles.title}>Ново-греческий бот</h1>
          <p className={styles.subtitle}>Современный греческий для Telegram-миниаппа и мобильных устройств</p>
        </header>
      </footer>
    </div>
  );
}
