<p align="center">
  <img src="front/src/assets/logo.png" alt="INIBSA icon" width="388"/>
</p>

# KeepInibsa

<p align="center">
  <strong>Smart Demand Signals for INIBSA, built during InterHack-2026.</strong>
</p>

<p align="center">
  <img alt="InterHack 2026" src="https://img.shields.io/badge/InterHack-2026-2563eb?style=for-the-badge" />
  <img alt="React" src="https://img.shields.io/badge/React-19-61dafb?style=for-the-badge&logo=react&logoColor=111827" />
  <img alt="Vite" src="https://img.shields.io/badge/Vite-6-646cff?style=for-the-badge&logo=vite&logoColor=white" />
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-5.7-3178c6?style=for-the-badge&logo=typescript&logoColor=white" />
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img alt="SQLite" src="https://img.shields.io/badge/SQLite-Alembic-003b57?style=for-the-badge&logo=sqlite&logoColor=white" />
  <img alt="Gemini" src="https://img.shields.io/badge/Gemini-2.5_Flash-8e75b2?style=for-the-badge&logo=googlegemini&logoColor=white" />
  <img alt="Docker" src="https://img.shields.io/badge/Docker-Compose-2496ed?style=for-the-badge&logo=docker&logoColor=white" />
</p>

## Challenge

This project answers the INIBSA challenge **"Smart Demand Signals: Prediccion de necesidad de compra y deteccion temprana de riesgo de abandono en clinicas dentales"** from **InterHack-2026**.

INIBSA works with a large dental-clinic customer base and years of sales history at customer and product level. The challenge is to transform transactional patterns into commercial signals that help teams decide:

- when a clinic is likely to need a replenishment purchase,
- when a loyal customer is starting to deteriorate,
- when a promiscuous buyer may have a capture window versus competitors,
- when a technical-product buyer is showing early churn risk,
- and which commercial channel should act next.

The solution is designed as a standalone application that can later integrate with CRM, tele-sales, and marketing automation platforms.

## What We Built

**KeepInibsa** turns predictive signals into operational sales workflows.

- **Sales Delegate Dashboard**: a table-first alert workspace for dental-clinic clients, with priority, churn risk, purchase propensity, customer value, explanation, product-family context, status tabs, attended/dismissed workflows, and action history.
- **Regional Manager Dashboard**: an executive dashboard with KPI cards, a Spain map by commercial area/autonomous community, regional performance status, and manager -> agent -> client drill-down.
- **AI Insight Panel**: a Gemini-backed assistant that explains each alert using the selected client context and answers the specific question asked by the user.
- **Voice and notification integrations**: backend modules for audio/voice-oriented flows and notification support, prepared for richer commercial workflows.
- **Daily alert pipeline concept**: data ingestion, prediction, alert generation, backend loading, and frontend activation are separated so the solution can evolve from hackathon demo to production pipeline.

## Model and Analytics Architecture

The analytical layer lives under `IA/` and focuses on generating interpretable commercial alerts from customer-product purchase behavior.

### Purchase Need and Repurchase Signals

The pipeline estimates whether a customer-product relationship is approaching a likely repurchase moment. It uses historical behavior, recency, purchase frequency, product-family context, and expected next purchase timing.

### Churn and Deterioration Risk

For technical or less regular products, the solution detects changes in order frequency, volume, recency, and customer-specific momentum. It avoids treating normal irregularity as churn by comparing behavior with historical and segment-level expectations.

### Customer Potential and Prioritization

Alerts are ranked using customer value, expected demand gap, urgency, risk, purchase propensity, and commercial impact. The current generated alert set is normalized and rescaled to avoid clustered scores and produce usable operational spread.

### Explainability

Each alert carries business-facing context: affected product family, churn type, predicted next purchase, last order date, annual spend signals, purchase cadence, momentum, and model repurchase signal. The AI assistant receives this context to produce concise, question-aligned explanations.

### Models Used

- `LargePurchaseModel`: multi-head purchase model with a shared representation and specialized outputs for purchase likelihood and days-to-next-purchase. The days head uses masked loss so missing timing targets do not bias the prediction.
- Repurchase prediction model: estimates whether a client/product relationship is likely to reactivate or buy again.
- Purchase propensity model: scores capture opportunity and commercial potential from purchase history and expected demand.
- Churn/risk signal layer: combines model scores, customer history, demand gap, recency, momentum, product-family logic, and percentile-based prioritization.
- Explainability layer: packages model and business variables into a compact alert context that can be shown directly or passed to the assistant.
- Gemini 2.5 Flash: used through the backend for contextual alert interpretation and question-specific explanations.

## Product Architecture

```text
IA pipelines / CSV outputs
        |
        v
FastAPI backend + Alembic migrations + SQLite
        |
        v
Typed API clients with TanStack Query
        |
        v
React dashboards for delegates and regional managers
```

### Backend

- FastAPI application with modular routers under `back/app/api`.
- Async SQLAlchemy models and Alembic migrations.
- SQLite for the standalone hackathon deployment.
- Alert API backed by generated ML alert data.
- Regional dashboard API with aggregated manager, agent, client, and KPI data.
- LLM endpoint that keeps model/API keys server-side.

### Frontend

- React 19, Vite, TypeScript, Tailwind CSS, shadcn-style primitives.
- React Router for role-based dashboard routing.
- TanStack Query for backend reads.
- Framer Motion for subtle dashboard transitions.
- d3-geo and topojson for the interactive Spain map.
- Catalan and Spanish localization.

### Integrations

- **Gemini**: AI insight generation for alert explanations.
- **Groq**: backend dependency prepared for alternative LLM workflows.
- **ElevenLabs**: backend dependency for voice-oriented UX.
- **AssemblyAI**: backend dependency for transcription/audio flows.
- **Docker Compose**: reproducible local full-stack runtime.

## Main User Flows

1. A user selects a role on the login screen.
2. Sales delegates enter the operational alert dashboard.
3. Regional managers enter the regional performance dashboard.
4. Alerts are reviewed, filtered, attended, dismissed, or reopened.
5. The AI panel explains a selected alert in the context of the user question.
6. Commercial interactions are persisted as event history for learning and traceability.

## Running the Project

### Prerequisites

- Docker Desktop with Docker Compose v2
- PowerShell on Windows
- Environment variables based on `.env.example`

### Start

```powershell
./start.ps1
```

The script checks Docker, creates `.env` from `.env.example` when missing, runs migrations when needed, and starts the Docker stack.

### URLs

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- FastAPI docs: http://localhost:8000/docs

### Useful Commands

```powershell
docker compose up --build
docker compose run --rm backend alembic upgrade head
docker compose run --rm frontend npm run typecheck
docker compose run --rm frontend npm run build
```

## Repository Layout

```text
front/      React + Vite frontend
back/       FastAPI backend, models, services, migrations
IA/         ML pipelines, generated predictions, alert CSVs, explainability work
docs/       planning/spec artifacts
memory/     project state used by AI agents
nginx/      production reverse proxy configuration
scripts/    project automation
```

## Key API Endpoints

- `GET /health`
- `GET /alerts`
- `GET /regional-dashboard`
- `POST /ai/chat`
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

## Future Work

- Connect the alert pipeline to a scheduled production data source.
- Replace mocked frontend role auth with backend authorization.
- Add CRM and marketing automation export hooks.
- Add automated regression tests for alert generation and KPI aggregation.
- Feed commercial outcomes back into model tuning and false-positive reduction.

---

## Contributors

<table>
  <tr>
    <td align="center" width="33%">
      <a href="https://github.com/Ki-re">
        <img src="https://github.com/Ki-re.png" width="120" style="border-radius:50%" alt="Erik Batiste"/><br/>
        <strong>Erik Batiste</strong>
      </a><br/>
      <em>Core Full Stack Engineer</em><br/><br/>
      Architected the foundational full-stack app with FastAPI/React, DevOps infrastructure, DB pipelines and Gemini LLM integrations.
    </td>
    <td align="center" width="33%">
      <a href="https://github.com/Yearsuck">
        <img src="https://github.com/Yearsuck.png" width="120" style="border-radius:50%" alt="Ernest Rull"/><br/>
        <strong>Ernest Rull</strong>
      </a><br/>
      <em>DevOps & Frontend Engineer</em><br/><br/>
      Led VPS deployment, bilingual frontend features, ElevenLabs voice cloning and agent-scoped notifications.
    </td>
    <td align="center" width="33%">
      <a href="https://github.com/Alvaroost8">
        <img src="https://github.com/Alvaroost8.png" width="120" style="border-radius:50%" alt="Alvaro Saenz-Torre"/><br/>
        <strong>Alvaro Saenz-Torre</strong>
      </a><br/>
      <em>Lead Machine Learning Engineer</em><br/><br/>
      Designed and trained the B2B neural networks, ingestion, inference, explainability and actionable Alert routing.
    </td>
  </tr>
</table>
