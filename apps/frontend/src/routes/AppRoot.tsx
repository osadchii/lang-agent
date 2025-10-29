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
        eyebrow: "Κύμα · Μαθαίνω",
        title: "Cypriot Greek Journeys",
        subtitle: "Design your everyday ritual with sunlit decks, coastal drills, and mindful review.",
        supporting: "A curated flow across flashcards, exercises, and story-driven practice inspired by Mediterranean rhythms."
      }}
      footer={{
        caption: `Sea breeze check-in · ${activeCount} active lesson${activeCount === 1 ? "" : "s"} this week`,
        ctaLabel: "Plan my ritual",
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
