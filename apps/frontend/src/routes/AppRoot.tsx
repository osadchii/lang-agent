import { ShellLayout } from "@components/ShellLayout";
import { DecksPanel } from "@components/decks/DecksPanel";
import { TrainingPanel } from "@components/training/TrainingPanel";

import styles from "./AppRoot.module.css";

export function App(): JSX.Element {
  return (
    <ShellLayout
      header={{
        eyebrow: "Κύμα · Μαθαίνω",
        title: "Создавай колоды. Тренируй память. Μαζί играем.",
        subtitle: "Собирай двусторонние карточки русское ↔ ελληνικό с подсказками ИИ и оценивай свои ответы в привычном бот-потоке.",
        supporting: "Управление колодами и тренировки теперь внутри мини-приложения, так что η πρακτική остаётся синхронной где бы ты ни учился."
      }}
      footer={{
        caption: "Готов продолжить? Возвращайся в мастерскую колод в любой момент.",
        ctaLabel: "Синхронизировать с Telegram",
        onCtaClick: () => {
          // Placeholder for navigation once routing lands.
          console.info("Запрошена синхронизация с Telegram");
        }
      }}
    >
      <div className={styles.content}>
        <div className={styles.sections}>
          <DecksPanel />
          <TrainingPanel />
        </div>
      </div>
    </ShellLayout>
  );
}
