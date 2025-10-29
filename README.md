# Greek Language Learning Platform

[![CI](https://github.com/osadchii/lang-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/osadchii/lang-agent/actions/workflows/ci.yml)
[![Backend Image](https://img.shields.io/badge/ghcr.io-backend-blue)](https://github.com/osadchii/lang-agent/pkgs/container/lang-agent-backend)
[![Frontend Image](https://img.shields.io/badge/ghcr.io-frontend-green)](https://github.com/osadchii/lang-agent/pkgs/container/lang-agent-frontend)
[![Python 3.11](https://img.shields.io/badge/python-3.11%2B-%233776AB)](https://www.python.org/downloads/release/python-3110/)
[![Node 18](https://img.shields.io/badge/node-18.18%2B-%23339933)](https://nodejs.org/docs/latest-v18.x/api/)

AI-assisted tooling for learning Greek. The repository hosts both the backend services (bot runtime, API) and the forthcoming Telegram mini app frontend. Development practices live in `AGENTS.md`.

---

## Highlights
- **Multi-surface**: Python backend (`apps/backend`) plus React/Vite frontend (`apps/frontend`).
- **Automated delivery**: CI builds, tests, publishes Docker images, and deploys to Raspberry Pi via GitHub Actions.
- **Infrastructure-aware**: Optional Traefik routing baked into `docker-compose.yml`; can be disabled for local testing.
- **Documented process**: ADRs in `docs/adr`, engineering expectations in `AGENTS.md`.

## Repository Map
```
apps/backend/     Backend services (bot runtime, API, domain logic)
apps/frontend/    Telegram mini app (React + Vite)
resources/texts/  Lesson content and localized prompts
docs/adr/         Architectural decision records
```

### Backend layout (`apps/backend/src/backend`)
- `application/` – orchestration and lifecycle management.
- `cli/` – command-line entrypoints (`python -m backend.cli`).
- `api/` – HTTP API exposed to the mini app.
- `services/` – integrations and shared service components.
- Tests live under `apps/backend/tests/`.

### Frontend layout (`apps/frontend/src`)
- `routes/` – top-level screens and routing.
- `components/` – reusable UI modules.
- `hooks/` – state management and data fetching helpers.
- `styles/` – global theming and tokens.
- `public/` – static assets served by Vite.

## Quick Start

### Backend (Python)
1. Install Python 3.11+, Docker, and provision PostgreSQL 16 (e.g., via `docker compose up postgres`).
2. Create a virtualenv: `python -m venv .venv && source .venv/bin/activate`.
3. Install the project: `pip install -e .`.
4. Install dev tooling: `pip install -r requirements-dev.txt`.
5. Copy `.env.example` to `.env` and populate required backend secrets.
   - Required: `OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN`.
   - Database defaults (override as needed): `DB_DRIVER`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`. You can still set `DATABASE_URL` directly to bypass composition.
   - Optional overrides: `OPENAI_MODEL`, `OPENAI_SYSTEM_PROMPT`.
   - The backend auto-loads `.env` via `python-dotenv`; no manual sourcing needed.
6. Apply database migrations: `python -m backend.cli migrate`.

### Frontend (React)
1. Install Node.js 18.18+ and npm 9+.
2. From `apps/frontend/`, install deps: `npm install`.
3. Start dev server: `npm run dev` (served at `http://localhost:5173`).

## Running Locally
- Backend CLI: `python -m backend.cli` (or `make backend-dev`).
- Run migrations without starting the bot: `python -m backend.cli migrate`.
- Docker stack: `docker compose up --pull always` (or `make stack-docker`) exposes backend on `http://localhost:8000`, frontend on `http://localhost:4173`, and PostgreSQL on `localhost:5432`.
- The provided `docker-compose.yml` includes Traefik labels and attaches both services to an external `web` network for production deployment. If you are testing locally without Traefik, comment out the `labels:` section and the `networks:` declarations before running `docker compose`.
- Frontend dev server: `npm run dev` in `apps/frontend/` (or `make frontend-dev`).

### Make Targets
- `make backend-dev` – run the backend CLI entrypoint.
- `make backend-test` – execute backend tests (`pytest`).
- `make stack-docker` – build and start both Docker services.
- `make frontend-install` – install frontend dependencies.
- `make frontend-dev` – run the Vite dev server.
- `make frontend-build` – produce a production build.

## Docker Images
GitHub Actions publishes multi-arch images on pushes to `main`:
- Backend: `ghcr.io/osadchii/lang-agent-backend` (`latest` + commit SHA tags).
- Frontend: `ghcr.io/osadchii/lang-agent-frontend` (`latest` + commit SHA tags).

## Testing
- Backend: `pytest`.
- Frontend: `npm run build` (ensures the TypeScript build succeeds). Add UI/unit coverage alongside new features.

## Development Standards
- Follow the engineering practices in `AGENTS.md`.
- Keep documentation and environment files in sync with any setup or runtime changes.
- Coordinate frontend-backend integration work across `apps/frontend` and `apps/backend`, documenting shared contracts before implementation.
