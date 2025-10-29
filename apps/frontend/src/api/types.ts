export interface Flashcard {
  card_id: number;
  source_text: string;
  target_text: string;
  example_sentence: string;
  example_translation: string;
  part_of_speech: string | null;
}

export interface DeckSummary {
  id: number;
  slug: string;
  name: string;
  description: string | null;
  card_count: number;
  due_count: number;
  created_at: string;
}

export interface DeckCard {
  user_card_id: number;
  deck_id: number;
  card: Flashcard;
  last_rating: string | null;
  interval_minutes: number;
  review_count: number;
  next_review_at: string;
  last_reviewed_at: string | null;
}

export interface FlashcardCreationResponse {
  user_card_id: number;
  card: Flashcard;
  created_card: boolean;
  reused_existing_card: boolean;
  linked_to_user: boolean;
}

export type RatingValue = "again" | "review" | "easy";

export interface TrainingCard {
  user_card_id: number;
  deck_id: number;
  deck_name: string;
  prompt: string;
  hidden: string;
  prompt_side: "source" | "target";
  card: Flashcard;
}
