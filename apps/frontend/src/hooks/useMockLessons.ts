import { useMemo } from "react";

import type { LessonSummary } from "@routes/dashboard/LessonList";

const MOCK_DATA: LessonSummary[] = [
  {
    id: "lesson-phrases-001",
    title: "Essential Phrases",
    description: "Key phrases for greetings, gratitude, and everyday interactions.",
    status: "in-progress",
    progress: 45
  },
  {
    id: "lesson-vocab-food",
    title: "Food & Markets",
    description: "Vocabulary for dining out, shopping at local markets, and recipes.",
    status: "not-started",
    progress: 0
  },
  {
    id: "lesson-grammar-a1",
    title: "Grammar Foundations A1",
    description: "Sentence structure, articles, and present tense conjugations.",
    status: "in-progress",
    progress: 70
  },
  {
    id: "lesson-culture-essentials",
    title: "Culture Essentials",
    description: "Etiquette, gestures, and cultural notes for confident conversations.",
    status: "completed",
    progress: 100
  }
];

export function useMockLessons(): LessonSummary[] {
  return useMemo(() => MOCK_DATA, []);
}
