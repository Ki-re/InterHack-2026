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
- Feature engineering:
    - The dataset is enriched with extensive rolling window features (30d, 90d, 180d, 365d) for spend and purchase frequency.
    - `log1p` transformation is applied to skewed monetary and count features during training.
- Training strategy:
    - **Dynamic Loss Weighting**: Implemented to balance tasks (BCE: 1.0, Days: 5.0, Potential: 2.0) and prioritize harder targets.
    - **Label Smoothing**: Applied to the 'repurchase' BCE loss (0.05) to prevent overconfidence and gradient domination.
    - **Masked Loss**: 'Days' loss is only calculated for samples with actual repurchases.
- Evaluation: 'Days' accuracy is measured with ±3 days and 10% relative tolerance.

## Auth
- Email/password auth uses JWT bearer tokens.
- Frontend stores the access token in `localStorage`.
- Password hashes use stdlib PBKDF2-HMAC SHA-256.
- No OAuth, session cookies, refresh tokens, or roles in the starter auth flow.

## Tradeoffs
- Prefer small starter patterns over enterprise abstractions.
- Avoid global state libraries until needed.
- Use Docker Compose commands as the reliable verification path.
