# Greek Language Learning Platform

AI-assisted tooling for learning Greek. This repository houses both the backend services (bot runtime, API) and the forthcoming Telegram mini app frontend. Development practices are documented in `AGENTS.md`.

## Repository Structure
- `apps/backend/` — backend services (bot runtime, API, shared domain logic).
- `apps/frontend/` — Telegram mini app implemented with React + Vite.
- `resources/texts/` — localized lesson content and prompts.
- `docs/adr/` — architectural decision records.
- `infra/` (planned) — deployment manifests and automation as the platform grows.

### Backend layout (`apps/backend/src/backend`)
- `application/` — runtime orchestration and lifecycle management for the bot services.
- `cli/` — command-line entrypoints (`python -m backend.cli`).
- `api/` — HTTP API surface exposed to the Telegram mini app.
- `services/` — shared service layer components and integrations.
- Tests live under `apps/backend/tests/`.

### Frontend layout (`apps/frontend/src`)
- `routes/` — top-level screens and routing entrypoints.
- `components/` — shared UI components (cards, layout primitives, call-to-action blocks).
- `hooks/` — reusable state hooks and data fetchers.
- `styles/` — global styles and design tokens.
- `public/` — static assets served by Vite (icons, manifests).

## Getting Started

### Backend (Python)
1. Ensure Python 3.11+ and Docker are installed.
2. Create a virtual environment: `python -m venv .venv && source .venv/bin/activate`.
3. Install the backend package in editable mode: `pip install -e .`.
4. Install development dependencies: `pip install -r requirements-dev.txt`.
5. Copy `.env.example` to `.env` and populate backend secrets needed by the bot runtime.

### Frontend (React)
1. Ensure Node.js 18.18+ (or newer) and npm 9+ are installed.
2. From `apps/frontend/`, install dependencies: `npm install`.
3. Start the development server: `npm run dev`.
4. The Vite dev server runs on `http://localhost:5173` by default.

## Running Locally
- Backend CLI: `python -m backend.cli` (or `make backend-dev`).
- Entire stack via Docker: `docker compose up --pull always` (or `make stack-docker`) pulls published images and exposes the backend on `http://localhost:8000` plus the frontend on `http://localhost:4173`.
- Frontend dev server: in `apps/frontend/`, run `npm run dev` (or `make frontend-dev`).

### Makefile Shortcuts
- `make backend-dev` — run the backend CLI entrypoint.
- `make backend-test` — execute backend tests (`pytest`).
- `make stack-docker` — build and start both backend and frontend Docker services.
- `make frontend-install` — install frontend dependencies.
- `make frontend-dev` — start the Vite dev server.
- `make frontend-build` — build the frontend for production.

## Docker Images
GitHub Actions builds and publishes multi-architecture images (linux/amd64, linux/arm64) to GHCR on pushes to `main`:
- Backend: `ghcr.io/osadchii/lang-agent-backend` (`latest` and commit SHA tags).
- Frontend: `ghcr.io/osadchii/lang-agent-frontend` (`latest` and commit SHA tags).

## Testing
- Backend: `pytest`.
- Frontend: `npm run build` (ensures the TypeScript build succeeds). Add UI/unit tests as features grow.

## Development Standards
- Follow the engineering practices in `AGENTS.md`.
- Keep documentation and environment files in sync with any change that affects setup or runtime behavior.
- Plan frontend-backend integration work across `apps/frontend` and `apps/backend`, documenting shared contracts before implementation.
