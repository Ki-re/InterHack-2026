# Current State

## Implemented
- Fullstack starter: React/Vite/TypeScript/Tailwind/shadcn frontend.
- Backend: FastAPI, async SQLAlchemy 2.0, SQLite, Alembic.
- Docker Compose runs backend on `8000` and frontend on `5173`.
- Auth: email/password register/login, JWT bearer token, `/auth/me`.
- Frontend auth for INIBSA MVP: mocked role-based session persisted in `localStorage` under key `inibsa.salesDelegateSession`, guarded dashboard routes, no backend auth call. Roles: sales delegate and regional manager.
- Login page: enterprise SaaS mock login at `/` with role selector. Sales delegate routes to `/dashboard`; regional manager routes to `/regional-dashboard`. Uses `logo.png` in card header and `icon.png` in the challenge badge.
- Dashboard: INIBSA sales alerts MVP at `/dashboard` with mock alert data (dental clinic clients), table-first workflow with **pending / attended / dismissed** tab toggle (pending shown first), channel-aware attended form, dismiss with inline confirm, changelog in expanded rows, and AI insight panel connected to Gemini API via `POST /ai/chat` (real LLM, no mock responses).
- LLM module: `back/app/llm/` with `prompt.yaml` (INIBSA system prompt with alert context injection, guardrails, multilingual, no recommendations, no contact-history references, short-paragraph rules), `schemas.py`, `service.py` (Gemini 2.5 Flash via `google-genai` SDK, async via `asyncio.to_thread`), `router.py` (`POST /ai/chat`). Requires `GEMINI_API_KEY` env var in `.env`.
- `AIInsightPanel`: real backend call; loading spinner; errors inline; assistant replies rendered as separated `<p>` paragraphs split on `\n\n+`.
- **Alert interaction model**: `InteractionRecord` replaces `FollowUpRecord`. Each alert carries `interactions: InteractionRecord[]` and `events: SystemEventRecord[]`. `keepOpen: boolean` on the record controls whether status becomes "attended" or stays "pending". Closing appends a `"closed"` system event; dismissing appends `"dismissed"`; recovering appends `"reopened"`. `dismissed` status with optional `dismissReason` + `dismissedAt`.
- **Channel-aware follow-up form** (`FollowUpForm.tsx`): phone (answered/not), visit (successful/not), email (response/not). Result + Notes shown only when contact was made. keepOpen toggle always shown.
- **Dismiss modal** (`DismissModal.tsx`): proper popup overlay (same style as AlertDetailModal) with alert name in header, description, labelled reason textarea, Cancel + destructive Confirm buttons. State managed at Dashboard level (`dismissTarget`). `AlertRow` dismiss button calls `onOpenDismiss(alert)` instead of managing inline confirm state.
- **Changelog** in expanded row: unified timeline merging `interactions[]` and `events[]` sorted newest-first. Interaction entries show channel icon, outcome badge, result badge, notes (no keepOpen line). System event entries show colored icon + label + optional reason. `keepOpen` line removed from interaction display.
- **Dismissed tab** added to Dashboard alongside pending/attended; metrics include dismissed count.
- Database models: `Team`, `User`.
- Regional dashboard backend: Alembic `0003_create_regional_dashboard` adds `regions`, `regional_managers`, `sales_agents`, `clients`, and `regional_alerts` with deterministic seed data for Catalonia+Valencia, North, and South.
- Regional manager API: `GET /regional-dashboard` returns global, region, manager, agent, client, and underperformer KPI data focused on alert execution.
- Regional dashboard frontend: `/regional-dashboard` — full regional dashboard with KPI cards (reactive to selected region), interactive Spain map, inline drill-down tables, and CA/ES translations.
  - Map: `d3-geo` + `spain-communities.json` module + `topojson-server`/`topojson-client` for exact inter-region boundaries. Scale 1800, HEIGHT 310, peninsula only. Region buttons below SVG (full-width flex-wrap row). SVG: pass 1 = white 0.8px subtle community borders; inter-region boundary drawn as a pre-computed topojson mesh path in neutral dark (#334155) — exact geographic boundary, not status-dependent, always visible regardless of region status colors.
  - Layout: fr-based 3-col grid `xl:grid-cols-[1.6fr_0.7fr_1fr] xl:items-stretch` fills full row width (same as KPI row). Estat and Focus use `relative overflow-hidden` wrappers with `absolute inset-0` inner divs — the wrappers contribute 0 height to grid track sizing (no normal-flow children), so only the Map sets the row height. Estat/Focus cards are `h-full` and exactly match the map height.
  - Map: SVG wrapper changed to `p-3` (uniform 12px margin all around). Topojson imports/variables/border paths removed — no divisor line between region groups. Only the subtle white 0.8px community borders remain.
- Fixed missing `front/src/lib/utils.ts` utility file for shadcn/ui components.
- Implemented i18n (Catalan default, Spanish toggle) using React Context. Both locales fully translated — no English terms remain in either locale file.
- Enhanced Dashboard layout to fix horizontal scrolling on desktop (widened container to `max-w-[1440px]`).
- Added subtle UI animations using Framer Motion (fade-ins, staggered lists, smooth row expansion).
- Branding: INIBSA full logo (`front/src/assets/logo.png`) used in AppLayout header and Login card. Icon only (`front/src/assets/icon.png`) used as favicon (`front/public/icon.png`) and in login badge. Page title is "INIBSA".
- "Alertas" nav button removed. App subtitle hidden from AppLayout header.
- "Alertes INIBSA" eyebrow label removed from dashboard page header.
- ChurnType is open-ended (`"total" | string`); mock data uses "total", "Producto 1", "Producto 2".
- Percentage columns (churn risk, purchase propensity) display as color-coded pill badges (red/amber/green) instead of progress bars.
- "Marcar atesa" button icon changed to ClipboardCheck. Both action buttons are `w-full`.
- "Descartar" (Trash2 icon) button added at same level as Ask AI + Mark as Attended; disabled for attended/dismissed alerts.
- `risk.low` fixed to "Baix" (was "Baixa") in `ca.json`.
- Docker named volume `frontend_node_modules` must be removed and recreated when new npm packages are added (framer-motion issue resolved this way).
- Page title changed to "Client Alert Manager".
- `GEMINI_API_KEY` is loaded from `.env` file at the project root via `docker-compose.yml` env_file directive (not hardcoded).

## Broken / Incomplete
- Host `front/npm run typecheck` cannot find `tsc` if not in path; Docker typecheck or local `npm run typecheck` (if tsc installed) works.
- No automated backend test suite yet.
- Sales alerts are frontend mock data only; no alert API or persistence exists yet. Interactions and dismiss state reset on page refresh.
- Regional dashboard data is seeded backend data, not production ingestion yet.
- No password reset, email verification, refresh tokens, roles, or rate limiting.

## Current Sprint Goal
- Add backend-backed regional manager visibility while preserving the delegate alert dashboard.

## Next Tasks
- Add frontend smoke coverage for login, dashboard routing, attended flow, and AI panel.
- Add tests for `GET /regional-dashboard` aggregation and frontend regional drill-down.
- Define backend alert API contracts when delegate alert persistence starts.
- Replace development `JWT_SECRET_KEY` before any shared deployment if backend auth is reintroduced in the frontend flow.

## Active Endpoints
- `GET /health`
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `GET /regional-dashboard`

## Active Frontend Pages
- `/` public mock login page for `Delegado de Ventas`.
- `/dashboard` protected sales alerts dashboard with mocked dental clinic alerts.
- `/regional-dashboard` protected regional manager dashboard backed by seeded backend hierarchy/KPI data.
