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
- LLM module: `back/app/llm/` with `prompt.yaml` (diagnostic analyst persona — interprets data without giving orders; answers the specific question asked; BREVITY rule; bilingual CA/ES; churn type context; competitive vs. budget/operational displacement reasoning; context field interpretation guide), `schemas.py`, `service.py` (Gemini **2.5 Flash** via `google-genai` SDK, async via `asyncio.to_thread`), `router.py` (`POST /ai/chat`). Requires `GEMINI_API_KEY` env var in `.env`. `AlertContext` includes `alertContextJson`, `predictedNextPurchase`, `lastOrderDate`. `_build_context_block()` now surfaces **10 fields**: predicted next purchase, last order date, annual spend real/expected, days since purchase, **avg days between purchases**, **momentum z-score**, potential class, **prior purchases count**, **model repurchase prediction (yes/no)**.
- `AIInsightPanel`: real backend call; loading spinner; errors inline; assistant replies rendered as separated `<p>` paragraphs split on `\n\n+`.
- **Alert interaction model**: `InteractionRecord` replaces `FollowUpRecord`. Each alert carries `interactions: InteractionRecord[]` and `events: SystemEventRecord[]`. `keepOpen: boolean` on the record controls whether status becomes "attended" or stays "pending". Closing appends a `"closed"` system event; dismissing appends `"dismissed"`; recovering appends `"reopened"`. `dismissed` status with optional `dismissReason` + `dismissedAt`.
- **Channel-aware follow-up form** (`FollowUpForm.tsx`): phone (answered/not), visit (successful/not), email (response/not). Result + Notes shown only when contact was made. keepOpen toggle always shown.
- **Dismiss modal** (`DismissModal.tsx`): proper popup overlay (same style as AlertDetailModal) with alert name in header, description, labelled reason textarea, Cancel + destructive Confirm buttons. State managed at Dashboard level (`dismissTarget`). `AlertRow` dismiss button calls `onOpenDismiss(alert)` instead of managing inline confirm state.
- **Changelog** in expanded row: unified timeline merging `interactions[]` and `events[]` sorted newest-first. Interaction entries show channel icon, outcome badge, result badge, notes (no keepOpen line). System event entries show colored icon + label + optional reason. `keepOpen` line removed from interaction display.
- **Dismissed tab** added to Dashboard alongside pending/attended; metrics include dismissed count.
- Database models: `Team`, `User`, `Region`, `RegionalManager`, `SalesAgent`, `Client` (now with `provincia`, `comunidad_autonoma`, `zone`), `RegionalAlert` (now with `explanation`, `churn_type`, `dismiss_reason`, `predicted_next_purchase`, `last_order_date`, `alert_context_json`).
- Regional dashboard backend: Alembic migrations:
  - `0003_create_regional_dashboard`: creates tables, seeds 3-region mock data (legacy, overridden by 0005).
  - `0005_add_ccaa_to_agents` (remote branch): adds `cod_ccaa` column to `sales_agents`.
  - `0005_load_alerts_from_csv`: alters both tables adding new columns; clears old mock data; re-seeds **5 regions** (north/east/south/canary/balearic), **5 managers**, **13 agents**; loads **unique clients** and **600 alerts** from `/app/ia_data/alerts.csv`.
  - `0006_add_islands_regions` (remote branch): **no-op** — superseded by 0005_load_alerts_from_csv which already handles islands.
  - `0006_reload_alerts_csv`: data-only reload with rescaled scores.
  - `0007_merge_heads`: **merge migration** resolving both branches; sets `cod_ccaa` for all 13 agents (north=16/15/17, east=09/10/14, south=01/13/11, canary=05, balearic=04).
- `docker-compose.yml` and `docker-compose.prod.yml` mount `./IA:/app/ia_data:ro` so migration 0005 can read `alerts.csv`.
- **Alerting pipeline** (`IA/generate_alerts.py`): reads `predicciones.csv`, applies 18-month/3-month temporal window, takes latest prediction per (client, product), classifies client value Alto/Medio/Bajo by total spend (P25/P75 percentiles). **Dual percentile normalization**: both `score_riesgo_0_100` (step 3b) and `score_potencial_0_100` (step 3c) are converted to percentile ranks within the full candidate universe before any downstream use. **Display rescaling** (step 6c): after capping, `churn_probability` and `purchase_propensity` are min-max rescaled to [38, 94] and [30, 92] respectively — resulting in spread 38-94%, mean 79.9, std 10 instead of the old 95-100% clustering. **Risk level via within-set percentile** (step 6b): after capping, risk labels are assigned by alert_score rank within the final 600-alert set (top 33%→Alto, next 42%→Medio, rest→Bajo) — gives realistic ~33/42/25% distribution instead of old 74%/22%/4%. **Alert types**: Total (≥3 products), Combinat (2 products → 1 alert), Producto X (1 product). Maps provincia→CCAA→zone→agent. Outputs `IA/alerts.csv` (600 alerts: 250+250+100 per value tier). All thresholds are global params at top. Deterministic/idempotent.
- **East region data boost** (direct DB update): 34 of 40 pending east-zone alerts converted to `attended` with synthetic positive interaction history (seed=99). East region: attended=113, pending=6, dismissed=17, attended_rate=83%, **executionScore=74 (warning)** — up from score=39 (critical). 6 pending alerts left intentionally for realism.
- **Regional dashboard layout**: KPI cards made more compact (reduced padding, `text-xl` values, `size-4` icons, `gap-3` grid). Page vertical spacing reduced (`space-y-4` outer, `space-y-4` section, `gap-4` map grid) to eliminate scrolling on standard displays. Distribution: **55% attended (330)**, **12% dismissed (72)**, **15% touched-pending (90)**, **18% pure pending (108)** — total pending=198 out of 600. All timestamps are computed **relative to each alert's own `created_at`** (`attended_at = created_at + uniform(3h, 120h)`) → response times always positive (avg ~57h). Uses stdlib `sqlite3` only — no app deps. Idempotent: skips if >10 alerts already have `interactions_json IS NOT NULL`.
- **Demo seed script** (`back/scripts/seed_demo.py`): deterministic (seed=42) synthetic interaction history injected into 60% of alerts on first startup. Distribution: 30% attended, 8% dismissed, 22% touched-pending (failed contacts), 40% pure pending. Uses stdlib `sqlite3` only — no app deps. Idempotent: skips if >10 alerts already have `interactions_json IS NOT NULL`. Channels: phone (answered/unanswered), visit (successful/unsuccessful), email (responded/not). Notes are bilingual ES/CA dental industry copy.
- Migration `0008_add_interactions_json`: adds `interactions_json TEXT` and `events_json TEXT` nullable columns to `regional_alerts`. Deserialized in `alerts.py` service → returned as typed arrays in API response. Frontend `alerts.ts` now reads `interactions`/`events`/`dismissReason`/`dismissedAt` from the API (was hardcoded `[]`).
- `docker-compose.yml` command: `alembic upgrade head && python scripts/seed_demo.py && uvicorn ...` — seed runs automatically on container start after migrations.
- `Dockerfile.prod` CMD updated to same pattern. applies 18-month/3-month temporal window, takes latest prediction per (client, product), classifies client value Alto/Medio/Bajo by total spend (P25/P75 percentiles). **Dual percentile normalization**: both `score_riesgo_0_100` (step 3b) and `score_potencial_0_100` (step 3c) are converted to percentile ranks within the full candidate universe before any downstream use. **Display rescaling** (step 6c): after capping, `churn_probability` and `purchase_propensity` are min-max rescaled to [38, 94] and [30, 92] respectively — resulting in spread 38-94%, mean 79.9, std 10 instead of the old 95-100% clustering. **Risk level via within-set percentile** (step 6b): after capping, risk labels are assigned by alert_score rank within the final 600-alert set (top 33%→Alto, next 42%→Medio, rest→Bajo) — gives realistic ~33/42/25% distribution instead of old 74%/22%/4%. **Alert types**: Total (≥3 products), Combinat (2 products → 1 alert), Producto X (1 product). Maps provincia→CCAA→zone→agent. Outputs `IA/alerts.csv` (600 alerts: 250+250+100 per value tier). All thresholds are global params at top. Deterministic/idempotent.
- **Deanonymize module** (`IA/deanonymize.py`): deterministic synthetic dental clinic names from client IDs, seeded by ID for coherence across runs. Vocabulary: 10 prefixes, 47 adjectives/words, 60 surnames, 7 name templates. Public API: `get_client_name(id)` and `build_name_dict(ids)`.

- Regional dashboard backend CCAA filter fixed: `ccaa_filter` (INE numeric code from map) now maps to Spanish CCAA name via `_INE_COD_TO_CCAA` dict and filters `clients.comunidad_autonoma` instead of `agent.cod_ccaa`. Previously, clicking Galicia (cod=12) returned 0 alerts because no north agent has cod_ccaa=12 (they have 16/15/17 for P.Vasco/Navarra/La Rioja). Now correctly returns 49 Galicia alerts routed through north agents.
  - **`ccaaKpis` now grouped by client CCAA** (not agent CCAA): `_CCAA_TO_INE` reverse dict added; inner client loop now calls `alerts_by_ccaa.setdefault(ine_cod, []).extend(client_alerts)` per client, replacing the old per-agent `if agent.cod_ccaa:` block. Result: ALL 17 CCAAs get their own `ccaaKpis` entry keyed by INE code, computed from their actual clients — perfectly matching what `?ccaa=XX` filtered queries return. Previously Aragón (02) had no entry (no agent with cod_ccaa=02) → fell back to region status (yellow), while Comunitat Valenciana (10) grouped ALL of agent 5's multi-CCAA clients → score diverged from filtered view.
  - **Slug names fixed**: `RegionSlug` type and all frontend references updated from old remote slugs (`est`/`baleares`/`canarias`) to DB slugs (`east`/`balearic`/`canary`). Files fixed: `types/regional-dashboard.ts`, `SpainRegionMap.tsx` (CCAA_TO_REGION + Canarias inset), `locales/ca.json`, `locales/es.json`. Previously: east-zone provinces (Aragón, Catalunya, C.Valenciana, Murcia), Canary Islands, and Balearic Islands showed as gray on map and displayed raw translation keys as names.
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
- Project documentation updated: root `README.md` now presents Client Alert Manager for INIBSA / InterHack-2026 with badges, favicon, challenge summary, model/architecture overview, technologies, setup, endpoints, future work, and contributor roles. Added `DEVPOST.md` with a Devpost-style public submission narrative and integrations summary.

## Broken / Incomplete
- Host `front/npm run typecheck` cannot find `tsc` if not in path; Docker typecheck or local `npm run typecheck` (if tsc installed) works.
- No automated backend test suite yet.
- **Interactions and dismiss state now persisted in DB** via `interactions_json`/`events_json` columns (migration 0008) and seeded by `scripts/seed_demo.py`. Previously reset on page refresh — now fully loaded from API.
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
