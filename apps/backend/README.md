# Backend Services

Python package that powers the language-learning bot runtime and HTTP API. The code lives under `apps/backend/src/backend`; tests reside in `apps/backend/tests`.

## Local Development
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r requirements-dev.txt
# Provide runtime secrets via `.env` (copy from repository root):
#   OPENAI_API_KEY=...
#   TELEGRAM_BOT_TOKEN=...
#   (optional) DATABASE_URL=sqlite+aiosqlite:///./bot.db
# Run the CLI (alternatively: `make backend-dev` from repo root)
python -m backend.cli
```

## Testing
```bash
pytest  # or run `make backend-test` from the repository root
```

## Key Directories
- `application/` — runtime bootstrap and orchestration.
- `api/` — future HTTP surface for the Telegram mini app.
- `cli/` - command-line entrypoints and tooling.
- `services/` - shared domain services and integrations.

Keep modules focused, document public APIs in place, and capture integration decisions in `docs/adr/`. Use `docker compose up --pull always` (or `make stack-docker`) from the repository root to run the backend alongside the frontend Docker service using the published container images.

The default storage is SQLite (via `DATABASE_URL=sqlite+aiosqlite:///./bot.db`). Swap in PostgreSQL or another engine by updating the connection string—no code changes needed.
