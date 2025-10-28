# 1. Telegram Runtime Backed by SQLite, Aiogram, and OpenAI

- Status: Accepted
- Date: 2025-10-28

## Context

The backend application needs an initial end-to-end flow for the Telegram bot: ingest user messages, persist conversations for future features (analytics, pre/post processing), and respond via OpenAI's GPT models while keeping the implementation modular for upcoming commands, menus, and additional processing steps.

## Decision

- Adopt `aiogram` (v3) for the Telegram layer to leverage its async-first design and modular routing.
- Introduce an async SQLAlchemy stack with a default `sqlite+aiosqlite` connection string, encapsulated behind repositories to ease future migrations to PostgreSQL.
- Persist message logs with explicit user/message tables and direction metadata to support future analytics and conversational context.
- Wrap OpenAI access in an `OpenAIChatClient` that injects a default "professional Greek teacher" system prompt and configurable model (`gpt-4.1-mini` via environment variable).

## Consequences

- We must provide `OPENAI_API_KEY` and `TELEGRAM_BOT_TOKEN` in the environment; the runtime validates their presence during bootstrap.
- The conversation service can evolve to add pre/post-processing and richer context handling without coupling to Telegram specifics.
- Swapping the database engine or LLM provider will require new implementations for the storage or LLM client interfaces but not changes to the Telegram orchestration code.
- SQLite suits local development; production deployments should point `DATABASE_URL` to a managed PostgreSQL instance for reliability and concurrency.

