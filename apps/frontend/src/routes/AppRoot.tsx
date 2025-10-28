import { useMemo } from "react";

import { LessonList } from "@routes/dashboard/LessonList";
import { ShellLayout } from "@components/ShellLayout";
import { useMockLessons } from "@hooks/useMockLessons";

export function App(): JSX.Element {
  const lessons = useMockLessons();
  const activeCount = useMemo(() => lessons.filter((lesson) => lesson.status === "in-progress").length, [lessons]);

  return (
    <ShellLayout
      header={{
        title: "Greek Lessons",
        subtitle: "Progress through bitesized exercises and vocabulary cards."
      }}
      footer={{
        caption: `${activeCount} lesson${activeCount === 1 ? "" : "s"} in progress`,
        ctaLabel: "View Schedule",
        onCtaClick: () => {
          // Placeholder for navigation once routing lands.
          console.info("Schedule navigation requested");
        }
      }}
    >
      <LessonList lessons={lessons} />
    </ShellLayout>
  );
}
