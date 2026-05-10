# Current State

## Implemented
- Fullstack starter: React/Vite/TypeScript/Tailwind/shadcn frontend.
- Backend: FastAPI, async SQLAlchemy 2.0, SQLite, Alembic.
- Docker Compose runs backend on `8000` and frontend on `5173`.
- Auth: email/password register/login, JWT bearer token, `/auth/me`.
- Frontend auth: token persisted in `localStorage`, guarded dashboard route.
- Landing page: animated shader hero with Register/Login CTAs and inline auth form.
- Dashboard: authenticated main page with backend health status cards.
- AI Model: Multi-head `LargePurchaseModel` with masked loss for days prediction (fixes 1500-day bias).
- Frontend auth for INIBSA MVP: mocked role-based session persisted in `localStorage` under key `inibsa.salesDelegateSession`, guarded dashboard routes, no backend auth call. Roles: sales delegate and regional manager.
- Login page: enterprise SaaS mock login at `/` with role selector. Sales delegate routes to `/dashboard`; regional manager routes to `/regional-dashboard`. Uses `logo.png` in card header and `icon.png` in the challenge badge.
- Dashboard: INIBSA sales alerts MVP at `/dashboard`. Alert data now loaded from **real backend API** (`GET /alerts`) backed by `IA/alerts.csv` (600 real ML pipeline alerts). Table-first workflow with **pending / attended / dismissed** tab toggle (pending shown first), channel-aware attended form, dismiss with popup modal, changelog in expanded rows, and AI insight panel connected to Gemini API via `POST /ai/chat` (real LLM, no mock responses).
- LLM module: `back/app/llm/` with `prompt.yaml` (diagnostic analyst persona — interprets data without giving orders; answers the specific question asked; BREVITY rule; bilingual CA/ES; churn type context; competitive vs. budget displacement reasoning), `schemas.py`, `service.py` (Gemini **2.5 Flash** via `google-genai` SDK, async via `asyncio.to_thread`), `router.py` (`POST /ai/chat`). Requires `GEMINI_API_KEY` env var in `.env`. `AlertContext` now includes `alertContextJson`, `predictedNextPurchase`, `lastOrderDate`. `service.py` builds a `context_block` from these (annual spend, days since purchase, potential class, order dates).
- `AIInsightPanel`: real backend call; loading spinner; errors inline; assistant replies rendered as separated `<p>` paragraphs split on `\n\n+`.
- **Alert interaction model**: `InteractionRecord` replaces `FollowUpRecord`. Each alert carries `interactions: InteractionRecord[]` and `events: SystemEventRecord[]`. `keepOpen: boolean` on the record controls whether status becomes "attended" or stays "pending". Closing appends a `"closed"` system event; dismissing appends `"dismissed"`; recovering appends `"reopened"`. `dismissed` status with optional `dismissReason` + `dismissedAt`.
- **Channel-aware follow-up form** (`FollowUpForm.tsx`): phone (answered/not), visit (successful/not), email (response/not). Result + Notes shown only when contact was made. keepOpen toggle always shown.
- **Dismiss modal** (`DismissModal.tsx`): proper popup overlay (same style as AlertDetailModal) with alert name in header, description, labelled reason textarea, Cancel + destructive Confirm buttons. State managed at Dashboard level (`dismissTarget`). `AlertRow` dismiss button calls `onOpenDismiss(alert)` instead of managing inline confirm state.
- **Changelog** in expanded row: unified timeline merging `interactions[]` and `events[]` sorted newest-first. Interaction entries show channel icon, outcome badge, result badge, notes (no keepOpen line). System event entries show colored icon + label + optional reason. `keepOpen` line removed from interaction display.
- **Dismissed tab** added to Dashboard alongside pending/attended; metrics include dismissed count.
- Database models: `Team`, `User`, `Region`, `RegionalManager`, `SalesAgent`, `Client` (now with `provincia`, `comunidad_autonoma`, `zone`), `RegionalAlert` (now with `explanation`, `churn_type`, `dismiss_reason`, `predicted_next_purchase`, `last_order_date`, `alert_context_json`).
- Regional dashboard backend: Alembic migrations:
  - `0003_create_regional_dashboard`: creates tables, seeds 3-region mock data (legacy, overridden by 0005).
  - `0005_load_alerts_from_csv`: alters both tables adding new columns; clears old mock data; re-seeds **5 regions** (north/east/south/canary/balearic), **5 managers**, **13 agents**; loads **unique clients** and **600 alerts** from `/app/ia_data/alerts.csv`.
- `docker-compose.yml` and `docker-compose.prod.yml` mount `./IA:/app/ia_data:ro` so migration 0005 can read `alerts.csv`.
- **Alerting pipeline** (`IA/generate_alerts.py`): reads `predicciones.csv`, applies 18-month/3-month temporal window, takes latest prediction per (client, product), classifies client value Alto/Medio/Bajo by total spend (P25/P75 percentiles). **Percentile-based risk**: `score_riesgo_0_100` is converted to its percentile rank within the candidate universe (uniform 0-100) before filtering/scoring — eliminates border clustering (raw scores were 96-100 for all; percentile range is 83-100 with 4× more spread). **Alert types**: Total (≥3 products), Combinat (2 products → collapsed to 1 alert), Producto X (1 product). Risk level from composite (risk_pct×0.5 + propensity×0.3 + value_score×0.2). Maps provincia→CCAA→zone→agent. Outputs `IA/alerts.csv` (600 alerts: 250 Alto + 250 Medio + 100 Bajo caps). All thresholds are global params at top. Deterministic/idempotent.
- **Deanonymize module** (`IA/deanonymize.py`): deterministic synthetic dental clinic names from client IDs, seeded by ID for coherence across runs. Vocabulary: 10 prefixes, 47 adjectives/words, 60 surnames, 7 name templates. Public API: `get_client_name(id)` and `build_name_dict(ids)`.

- Regional dashboard frontend: `/regional-dashboard` — full regional dashboard with KPI cards (reactive to selected region), interactive Spain map, inline drill-down tables, and CA/ES translations.
  - Map: `d3-geo` + `spain-communities.json` module + `topojson-server`/`topojson-client` for exact inter-region boundaries. Scale 1800, HEIGHT 310, peninsula only. Region buttons below SVG (full-width flex-wrap row). SVG: pass 1 = white 0.8px subtle community borders; inter-region boundary drawn as a pre-computed topojson mesh path in neutral dark (#334155) — exact geographic boundary, not status-dependent, always visible regardless of region status colors.
  - Layout: fr-based 3-col grid `xl:grid-cols-[1.6fr_0.7fr_1fr] xl:items-stretch` fills full row width (same as KPI row). Estat and Focus use `relative overflow-hidden` wrappers with `absolute inset-0` inner divs — the wrappers contribute 0 height to grid track sizing (no normal-flow children), so only the Map sets the row height. Estat/Focus cards are `h-full` and exactly match the map height.
  - When a region is selected, an "Info" button appears inside the map card (below SVG, above region buttons). Clicking opens `RegionDetailModal` — a wide (`max-w-5xl`, `90vh`) overlay with the full manager→agent→client drill-down. Modal state (`selectedManager`, `selectedAgent`) is self-contained. Clicking outside or the X closes it. Deselecting a region also closes the modal.
  - Expand actions in `RegionalPerformanceTables` replaced from text+icon Button to icon-only ghost chevron buttons (matches Delegat dashboard pattern).
  - Below-map `<RegionalPerformanceTables>` block removed from `RegionalDashboard.tsx`; details now live exclusively in the modal.
- Fixed missing `front/src/lib/utils.ts` utility file for shadcn/ui components.
- Implemented i18n (Catalan default, Spanish toggle) using React Context. Both locales fully translated — no English terms remain in either locale file.
- Enhanced Dashboard layout to fix horizontal scrolling on desktop (widened container to `max-w-[1440px]`).
- Added subtle UI animations using Framer Motion (fade-ins, staggered lists, smooth row expansion).
- Branding: INIBSA full logo (`front/src/assets/logo.png`) used in AppLayout header and Login card. Icon only (`front/src/assets/icon.png`) used as favicon (`front/public/icon.png`) and in login badge. Page title is "INIBSA".
- "Alertas" nav button removed. App subtitle hidden from AppLayout header.
- Role nav links (Delegats / Direcció Regional) removed from AppLayout header entirely — each role only has one page so the nav links are unnecessary.
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
- **Interactions and dismiss state reset on page refresh** — frontend-only local state; no persistence API for interactions/dismissals.
- No password reset, email verification, refresh tokens, roles, or rate limiting.

## Current Sprint Goal
- DB integration complete: 600 real alerts from ML pipeline load automatically via Alembic migration 0005 on `docker compose up`.

## Active Endpoints
- `GET /health`
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `GET /regional-dashboard`
- `GET /alerts` ← NEW (returns list of SalesAlertResponse from DB)

## Active Frontend Pages
- `/` public mock login page for `Delegado de Ventas`.
- `/dashboard` protected sales alerts dashboard — **real data from `GET /alerts`** (600 ML pipeline alerts).
- `/regional-dashboard` protected regional manager dashboard backed by seeded backend hierarchy/KPI data.
