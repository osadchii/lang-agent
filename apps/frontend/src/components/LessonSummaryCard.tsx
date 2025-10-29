import type { LessonSummary } from "@routes/dashboard/LessonList";

import styles from "./LessonSummaryCard.module.css";

interface LessonSummaryCardProps {
  lesson: LessonSummary;
}

const STATUS_LABEL: Record<LessonSummary["status"], string> = {
  "not-started": "Not started",
  "in-progress": "In progress",
  completed: "Completed"
};

const STATUS_TAGLINE: Record<LessonSummary["status"], string> = {
  "not-started": "Ξεκίνα το ταξίδι",
  "in-progress": "Κράτησε τον ρυθμό",
  completed: "Έφτασες στο λιμάνι"
};

export function LessonSummaryCard({ lesson }: LessonSummaryCardProps): JSX.Element {
  return (
    <article className={styles.card}>
      <div className={styles.cardWave} aria-hidden="true" />
      <header className={styles.header}>
        <div className={styles.meta}>
          <span className={styles.status} data-status={lesson.status}>
            {STATUS_LABEL[lesson.status]}
          </span>
          <span className={styles.progressValue}>{lesson.progress}%</span>
        </div>
        <h2>{lesson.title}</h2>
      </header>

      <p className={styles.description}>{lesson.description}</p>

      <div className={styles.progressBlock}>
        <div className={styles.progressBar} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={lesson.progress}>
          <div className={styles.progress} style={{ width: `${lesson.progress}%` }} />
        </div>
        <span className={styles.progressLabel}>{STATUS_TAGLINE[lesson.status]}</span>
      </div>

      <button className={styles.primaryAction} type="button">
        {lesson.status === "completed" ? "Review cards" : "Continue lesson"}
      </button>
    </article>
  );
}
