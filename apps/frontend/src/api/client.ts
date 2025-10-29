import type {
  DeckCard,
  DeckSummary,
  FlashcardCreationResponse,
  RatingValue,
  TrainingCard
} from "./types";

type RequestOptions = RequestInit & { skipAuthHeaders?: boolean };

type RuntimeConfig = {
  apiBaseUrl?: string;
  userId?: string;
  userUsername?: string;
  userFirstName?: string;
  userLastName?: string;
};

declare global {
  interface Window {
    __APP_CONFIG__?: RuntimeConfig;
  }
}

const runtimeConfig: RuntimeConfig =
  typeof window !== "undefined" && window.__APP_CONFIG__ ? window.__APP_CONFIG__ : {};

const API_BASE_URL =
  runtimeConfig.apiBaseUrl?.trim() || import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";
const USER_ID = Number.parseInt(runtimeConfig.userId ?? import.meta.env.VITE_USER_ID ?? "1", 10);
const USERNAME = runtimeConfig.userUsername ?? import.meta.env.VITE_USER_USERNAME ?? "";
const USER_FIRST_NAME = runtimeConfig.userFirstName ?? import.meta.env.VITE_USER_FIRST_NAME ?? "";
const USER_LAST_NAME = runtimeConfig.userLastName ?? import.meta.env.VITE_USER_LAST_NAME ?? "";

const AUTH_HEADER_VALUES: Record<string, string> = {
  "X-User-Id": Number.isNaN(USER_ID) ? "1" : String(USER_ID)
};

if (USERNAME) {
  AUTH_HEADER_VALUES["X-User-Username"] = USERNAME;
}
if (USER_FIRST_NAME) {
  AUTH_HEADER_VALUES["X-User-First-Name"] = USER_FIRST_NAME;
}
if (USER_LAST_NAME) {
  AUTH_HEADER_VALUES["X-User-Last-Name"] = USER_LAST_NAME;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!options.skipAuthHeaders) {
    for (const [key, value] of Object.entries(AUTH_HEADER_VALUES)) {
      headers.set(key, value);
    }
  }

  const body = options.body;
  if (body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers
  });

  if (response.status === 204) {
    return undefined as T;
  }

  if (!response.ok) {
    const detail = await extractErrorMessage(response);
    throw new Error(detail ?? `Request failed with status ${response.status}`);
  }

  const text = await response.text();
  if (!text) {
    return undefined as T;
  }
  try {
    return JSON.parse(text) as T;
  } catch (error) {
    throw new Error("Failed to parse response payload.");
  }
}

async function extractErrorMessage(response: Response): Promise<string | undefined> {
  try {
    const payload = await response.json();
    if (payload && typeof payload.detail === "string") {
      return payload.detail;
    }
  } catch {
    // Ignore JSON parse failures.
  }
  return undefined;
}

export async function fetchDecks(): Promise<DeckSummary[]> {
  return request<DeckSummary[]>("/decks");
}

export async function createDeck(input: { name: string; description?: string | null }): Promise<DeckSummary> {
  return request<DeckSummary>("/decks", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function updateDeck(
  deckId: number,
  input: { name?: string | null; description?: string | null }
): Promise<DeckSummary> {
  return request<DeckSummary>(`/decks/${deckId}`, {
    method: "PATCH",
    body: JSON.stringify(input)
  });
}

export async function deleteDeck(deckId: number): Promise<void> {
  await request<void>(`/decks/${deckId}`, { method: "DELETE" });
}

export async function fetchDeckCards(deckId: number): Promise<DeckCard[]> {
  return request<DeckCard[]>(`/decks/${deckId}/cards`);
}

export async function createDeckCard(deckId: number, prompt: string): Promise<FlashcardCreationResponse> {
  return request<FlashcardCreationResponse>(`/decks/${deckId}/cards`, {
    method: "POST",
    body: JSON.stringify({ prompt })
  });
}

export async function removeDeckCard(deckId: number, userCardId: number): Promise<void> {
  await request<void>(`/decks/${deckId}/cards/${userCardId}`, {
    method: "DELETE"
  });
}

export async function fetchNextTrainingCard(): Promise<TrainingCard | null> {
  const card = await request<TrainingCard | undefined>("/training/next");
  return card ?? null;
}

export async function fetchCardById(userCardId: number): Promise<TrainingCard> {
  return request<TrainingCard>(`/training/cards/${userCardId}`);
}

export async function submitReview(userCardId: number, rating: RatingValue): Promise<void> {
  await request<void>(`/training/cards/${userCardId}/review`, {
    method: "POST",
    body: JSON.stringify({ rating })
  });
}
