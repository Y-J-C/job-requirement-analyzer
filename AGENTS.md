# Repository Guidelines

## Project Structure & Module Organization

This pnpm workspace contains a Next.js frontend and FastAPI backend.

- `apps/web/src/app/`: Next.js routes, layouts, and global styles.
- `apps/web/src/features/`: feature-scoped React components, API clients, types, and colocated tests.
- `apps/api/app/`: routes, schemas, models, services, AI, parsing, storage, and workers.
- `apps/api/tests/`: pytest unit tests; infrastructure-dependent cases live in `tests/integration/`.
- `apps/api/migrations/`: Alembic migrations. Never edit an applied migration; add a new revision.
- `docs/`: approved feature specifications, implementation plans, and architecture decisions.
- `docker-compose.yml`: local PostgreSQL and MinIO services.

The nested `apps/web/AGENTS.md` contains additional Next.js instructions.

## Build, Test, and Development Commands

Run commands from the repository root in Windows PowerShell:

- `pnpm install`: install workspace dependencies.
- `pnpm db:up`: start PostgreSQL and MinIO.
- `pnpm api:migrate`: apply database migrations.
- `pnpm dev`: run Web (`:3001`), API (`:8000`), and the worker together.
- `pnpm lint`: run ESLint and Ruff.
- `pnpm test`: run Vitest and pytest unit suites.
- `pnpm test:api:integration`: test real PostgreSQL/MinIO connections; infrastructure must be running.
- `pnpm build`: build Next.js and compile-check Python modules.

## Coding Style & Naming Conventions

Use two-space indentation in TypeScript and four spaces in Python. React components and files use `PascalCase`; functions and variables use `camelCase`. Python modules, functions, and database fields use `snake_case`. Keep logic within its feature or service boundary. Ruff enforces imports and a 100-character line length; ESLint allows no warnings.

## Testing Guidelines

Use Vitest with Testing Library for frontend behavior and pytest for backend logic. Name tests `*.test.tsx` or `test_*.py`. Place tests beside the frontend feature or in the matching backend module. Mark infrastructure tests with `@pytest.mark.integration`. Add regression tests for behavior changes; run the smallest suite first, then the full validation commands before review.

## Commit & Pull Request Guidelines

Recent commits use short, outcome-oriented subjects, usually in Chinese, such as `增加岗位文件上传与异步解析`. Keep each commit focused and avoid generated files or secrets. Pull requests should explain the user-visible change, implementation scope, migrations/configuration, and exact verification performed. Link relevant issues or specs; include screenshots for UI changes and note any deferred risks.

## Security & Configuration

Copy `.env.example` to the ignored `.env`. Never commit API keys, tokens, uploaded documents, or production data. Validate uploads at the API boundary and preserve storage/database cleanup behavior when changing file workflows.
