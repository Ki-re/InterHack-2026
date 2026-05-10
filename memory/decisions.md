# Decisions

## Stack
- Frontend uses React, Vite, TypeScript, Tailwind CSS, shadcn/ui, React Router, TanStack Query, and Framer Motion for subtle animations.
- Backend uses FastAPI, Pydantic, async SQLAlchemy 2.0, SQLite, Alembic.
- Infra uses Docker Compose with hot reload for frontend and backend.

## Architecture
- SQLite remains the default local database.
- Backend endpoints stay thin; reusable logic belongs in `back/app/services`.
- Backend database access uses `AsyncSession`; sync SQLAlchemy sessions are not used.
- Frontend pages live in `front/src/pages`; shared UI lives in `front/src/components`.
- shadcn UI components live in `front/src/components/ui` via the `@/components/ui` alias.
- i18n is implemented via a lightweight React Context (`LanguageContext`) and JSON locale files in `front/src/locales`.

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
- INIBSA frontend MVP temporarily uses mocked localStorage auth with role selection (`sales_delegate`, `regional_manager`) and does not call backend auth endpoints.

## INIBSA MVP
- Sales alerts are mocked in the frontend until backend alert endpoints are defined.
- Regional dashboard uses real backend tables and deterministic seed data as the bridge from mockups to future production data.
- Regional manager performance is alert-execution centered: pending load, attended rate, high-risk backlog, overdue follow-ups, dismissals, and response time.
- The interactive Spain map is a custom SVG with three commercial areas; no chart/map package is added for this MVP.
- React local state is sufficient for attended status, follow-up questionnaire data, and AI insight panel messages.
- The UI direction is clean enterprise SaaS: neutral surfaces, dense table-first workflow, and restrained blue/green/red status accents.
- Mock clients are dental clinics with dental supply context.
- ChurnType is open-ended (`"total" | string`) — "total" is translated via i18n, any other string (e.g. "Producto 1") is displayed as-is.
- Percentage columns use color-coded pill badges (not progress bars): risk uses red/amber/green, opportunity uses the inverse.

## Branding
- Brand name is INIBSA (not INSIBA).
- `front/src/assets/logo.png`: full logo (icon + name). Used in AppLayout header and Login card.
- `front/src/assets/icon.png`: icon only. Used as favicon (`front/public/icon.png`), page title "INIBSA", and small badge contexts in Login.
- No nav links or subtitles shown in the AppLayout header — logo stands alone.

## Docker
- Frontend uses a named volume (`frontend_node_modules`) to persist node_modules for hot-reload performance.
- When new npm packages are added to `package.json`, the volume must be removed (`docker volume rm interhack-2026_frontend_node_modules`) and the container restarted so it repopulates from the rebuilt image.
- When new Python packages are added to `requirements.txt`, the backend image must be rebuilt (`docker compose build backend && docker compose up -d backend`).

## LLM / Gemini AI
- AI chat is routed through the FastAPI backend (`POST /ai/chat`) so the `GEMINI_API_KEY` never reaches the browser.
- System prompt lives in `back/app/llm/prompt.yaml` as the single source of truth for model behaviour — iterate prompt without touching Python code.
- Model: Gemini 1.5 Flash. System prompt injected via `system_instruction`. Conversation history passed as `contents[]` (alternating user/model turns).
- Gemini call is synchronous (`google-generativeai` SDK); wrapped in `asyncio.to_thread` to stay non-blocking in the FastAPI async context.
- No streaming for now — add later if UX requires it.
- If `GEMINI_API_KEY` is empty, the endpoint returns `503` with a clear message; frontend shows inline error in the chat, not a toast.
- Prompt guardrails: language-adaptive (CA/ES), concise (2–4 paragraphs), non-technical phrasing, INIBSA domain only, no hallucination of data not in the alert context.

## Tradeoffs
- Prefer small starter patterns over enterprise abstractions.
- Avoid global state libraries until needed.
- Use Docker Compose commands as the reliable verification path.
