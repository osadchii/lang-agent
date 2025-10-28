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

export function LessonSummaryCard({ lesson }: LessonSummaryCardProps): JSX.Element {
  return (
    <article className={styles.card}>
      <header className={styles.header}>
        <span className={styles.status} data-status={lesson.status}>
          {STATUS_LABEL[lesson.status]}
        </span>
        <h2>{lesson.title}</h2>
      </header>

      <p className={styles.description}>{lesson.description}</p>

      <div className={styles.progressBar} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={lesson.progress}>
        <div className={styles.progress} style={{ width: `${lesson.progress}%` }} />
      </div>

      <button className={styles.primaryAction} type="button">
        {lesson.status === "completed" ? "Review cards" : "Continue lesson"}
      </button>
    </article>
  );
}
