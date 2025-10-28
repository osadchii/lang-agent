# Greek Language Bot

AI-assisted bot for learning the Greek language. The project is structured for iterative growth with strict development guidelines documented in `AGENTS.md`.

## Project Layout
- `src/bot/` — application code and service layers.
- `resources/texts/` — localized lesson content and prompts.
- `tests/` — automated test suite.
- `docs/adr/` — architectural decision records.

## Getting Started
1. Ensure Python 3.11+ and Docker are installed.
2. Create a virtual environment: `python -m venv .venv && source .venv/bin/activate`.
3. Install dependencies: `pip install -r requirements-dev.txt`.
4. Copy `.env.example` to `.env` and populate secrets.

## Running Locally
- CLI: `python -m bot.app`.
- Docker: `docker compose up --build`.

## Testing
- Run all tests with `pytest`.

## Development Standards
- Follow the engineering practices in `AGENTS.md`.
- Keep documentation and environment files in sync with any change that affects setup or runtime behavior.

