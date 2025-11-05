# Agent Development Guidelines

## Language And Encoding
- Keep all commit messages, code comments, documentation, and filenames in English; end-user content may include Russian or Greek text when intentional.
- Store and exchange text files in UTF-8; verify that any non-English literals render correctly in editors, git diffs, and application logs.
- Localize user-facing strings via dedicated resource modules to ensure encoding control and future expansion to other languages.

## Architecture And Design
- Organize code so that every module has a narrow, well-defined responsibility and minimal cognitive load; prefer many small files over large multipurpose ones.
- Document the purpose of each public API, function, and module at the point of definition when intent is not obvious from the code.
- Maintain clear boundaries between core language-learning logic, infrastructure (storage, messaging, integrations), and user interface layers to simplify iteration.
- Keep backend code inside `apps/backend` and future mini app code inside `apps/frontend`, sharing only explicit domain contracts and DTOs.
- Structure frontend components as composable, theme-aware building blocks with co-located styles and tests to keep the UI layer maintainable.
- **Design all frontend UI for Telegram Mini App first and foremost**: prioritize mobile viewport optimization (320px-520px width), touch-friendly interactions, and minimal scrolling; desktop is secondary. Avoid fixed heights that cause content jumping or internal scrollbars; use flexible layouts with min-height instead.

## Process And Collaboration
- Update `README.md`, `.env`, and `.env.example` with every change that affects setup, configuration, or usage; keep setup instructions reproducible end-to-end.
- Record architectural decisions in concise ADRs whenever you introduce or revise significant behaviors; store ADRs under `docs/adr`.
- Before implementing features, outline requirements, assumptions, and open questions; resolve ambiguities early to avoid rework.
- Use feature branches named `feature/<short-description>` (or `fix/`, `docs/`, etc.) and craft conventional commits (`type(scope): summary`) to keep history searchable.
- Coordinate cross-surface changes (backend ↔ frontend) by capturing shared contracts, release sequencing, and migration steps in ADRs or integration docs before merging.

## Tooling And Quality
- Favor automated formatting, linting, and static analysis across all languages used in the project; treat warnings as build failures.
- Use the Context7 MCP documentation tools (`resolve-library-id`, then `get-library-docs`) to retrieve up-to-date guidance for external dependencies instead of ad-hoc web searches.
- Develop comprehensive automated tests for every utility, service, and module; aim for meaningful coverage rather than percentage targets.
- Write unit and integration tests alongside new code; keep suites fast, deterministic, and execute them after every code change and before each commit.
- Mock or stub external integrations in tests whenever feasible to maintain reliability, speed, and isolation.
- Always finish backend iterations by running `python3 -m pytest`; capture and surface any failures instead of skipping the run.
- Verify the application launches successfully both locally (`python -m backend.cli`) and via Docker (`docker compose up`) after every change.
- Ensure the frontend passes TypeScript builds (`npm run build`) and UI test suites prior to submitting changes.
- Collect meaningful logging and monitoring data with log levels, correlation IDs, and privacy safeguards to support debugging in production.

## Dependencies And Security
- Pin dependency versions, document installation steps, and audit updates promptly; remove unused libraries to reduce attack surface.
- Store secrets only in environment variables or secret managers; never commit sensitive data to the repository.
- Review third-party services and APIs for compliance with data protection requirements before integration.

## Continuous Improvement
- Keep this guideline file up to date as practices evolve; revise it whenever project direction, tooling, or collaboration modes change.
- Encourage code reviews that focus on correctness, maintainability, and user impact; follow up with refactoring tickets when issues cannot be resolved immediately.
