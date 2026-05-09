# Decisions

## Stack
- Frontend uses React, Vite, TypeScript, Tailwind CSS, shadcn/ui, React Router, TanStack Query.
- Backend uses FastAPI, Pydantic, async SQLAlchemy 2.0, SQLite, Alembic.
- Infra uses Docker Compose with hot reload for frontend and backend.

## Architecture
- SQLite remains the default local database.
- Backend endpoints stay thin; reusable logic belongs in `back/app/services`.
- Backend database access uses `AsyncSession`; sync SQLAlchemy sessions are not used.
- Frontend pages live in `front/src/pages`; shared UI lives in `front/src/components`.
- shadcn UI components live in `front/src/components/ui` via the `@/components/ui` alias.

## AI
- AI models use a multi-head architecture for multi-task learning to prevent gradient interference.
- Prediction heads are 2-layer MLPs (`Linear -> BN -> SiLU -> Linear`) for increased non-linear capacity.
- Feature engineering includes:
    - `log1p` transformation for highly skewed numeric features.
    - Cyclical encoding (sin/cos) for temporal features (month, day of week).
    - Interaction ratios (e.g., `ratio_ciclo_compra`, `ratio_recencia_media`, `ratio_gasto_categoria`).
    - Explicit flags like `is_first_purchase`.
- Target masking is applied to loss functions and metrics when certain targets (like 'days') are only relevant for a subset of samples (like 'repurchase' class).
- Accuracy for 'days' prediction is measured with both a static (±3 days) and a relative (10% error) tolerance.

## Auth
- Email/password auth uses JWT bearer tokens.
- Frontend stores the access token in `localStorage`.
- Password hashes use stdlib PBKDF2-HMAC SHA-256.
- No OAuth, session cookies, refresh tokens, or roles in the starter auth flow.

## Tradeoffs
- Prefer small starter patterns over enterprise abstractions.
- Avoid global state libraries until needed.
- Use Docker Compose commands as the reliable verification path.
