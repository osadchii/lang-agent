# Frontend (Telegram Mini App)

React + Vite application that delivers the Telegram mini app experience for the Greek language learning platform. The current scaffold focuses on discoverability and iterative growth—keep files small, components focused, and styles co-located.

## Stack
- React 18 with TypeScript.
- Vite for dev server and bundling.
- CSS Modules for component-scoped styling.

## Structure
- `src/routes/` — top-level screens (e.g., dashboard, lesson player).
- `src/components/` — shared UI primitives such as layouts and cards.
- `src/hooks/` — reusable logic (API bindings, state helpers).
- `src/styles/` — global styles and design tokens.
- `public/` — static assets served by Vite (favicons, manifests).

## Development
```bash
cd apps/frontend
npm install
npm run dev
```

You can also run `make frontend-dev` from the repository root to start the Vite dev server.

The dev server runs at `http://localhost:5173`. Use `npm run build` to validate the production build; add linting and automated UI tests alongside new features.

For a production-style build served through Nginx, run `docker compose up --pull always` (or `make stack-docker`) from the repository root and access the frontend at `http://localhost:4173`.
