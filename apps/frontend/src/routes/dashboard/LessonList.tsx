import { LessonSummaryCard } from "@components/LessonSummaryCard";

import styles from "./LessonList.module.css";

export type LessonStatus = "not-started" | "in-progress" | "completed";

export interface LessonSummary {
  id: string;
  title: string;
  description: string;
  status: LessonStatus;
  progress: number;
}

interface LessonListProps {
  lessons: LessonSummary[];
}

export function LessonList({ lessons }: LessonListProps): JSX.Element {
  return (
    <section className={styles.container} aria-label="Lesson overview">
      {lessons.map((lesson) => (
        <LessonSummaryCard key={lesson.id} lesson={lesson} />
      ))}
    </section>
  );
}
