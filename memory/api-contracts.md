# API Contracts

## `GET /health`
- Auth: none.
- Request: none.
- Response: `{ "status": "ok" }`

## `POST /auth/register`
- Auth: none.
- Request JSON:
  - `email: string` normalized lowercase, valid email shape.
  - `password: string` min 8, max 128.
- Response `201`:
  - `access_token: string`
  - `token_type: "bearer"`
  - `user: { id: number, email: string, created_at: datetime }`
- Errors:
  - `409` when email already exists.
  - `422` for validation errors.

## `POST /auth/login`
- Auth: none.
- Request JSON:
  - `email: string`
  - `password: string`
- Response `200`:
  - `access_token: string`
  - `token_type: "bearer"`
  - `user: { id: number, email: string, created_at: datetime }`
- Errors:
  - `401` for invalid email or password.
  - `422` for validation errors.

## `POST /ai/chat`
- Auth: none (API key is server-side only).
- Request JSON:
  - `alert: AlertContext` — `{ clientName, riskLevel, churnProbability, purchasePropensity, customerValue, churnType, explanation, alertContextJson?, predictedNextPurchase?, lastOrderDate? }`
  - `history: ChatMessage[]` — `[{ role: "user"|"assistant", content: string }, ...]` (full prior conversation)
  - `question: string` — the new user message
- Response `200`: `{ response: string }`
- Errors:
  - `503` if `GEMINI_API_KEY` is not configured.
  - `502` if the Gemini API call fails.

## `GET /regional-dashboard`
- Auth: none for current MVP; frontend access is controlled by mocked role routing.
- Request: none.
- Response `200`:
  - `generatedAt: datetime`
  - `kpis: ExecutionKpis`
  - `regions: RegionSummary[]`
  - `underperformers: Underperformer[]`
- `ExecutionKpis`:
  - `totalAlerts`, `pendingAlerts`, `attendedAlerts`, `dismissedAlerts`
  - `attendedRate`, `dismissalRate`, `highRiskBacklog`, `overdueFollowups`
  - `averageResponseHours: number | null`
  - `executionScore: number`
  - `status: "good" | "warning" | "critical"`
- Region hierarchy:
  - `RegionSummary` includes `slug`, `name`, `kpis`, and `managers`.
  - Manager summaries include `agents`.
  - Agent summaries include assigned `clients`.
  - Client rows include customer metadata, `kpis`, and alert execution rows.
- Seeded regions (after migration 0005):
  - `north` — Nord
  - `east` — Est
  - `south` — Sud
  - `canary` — Illes Canàries
  - `balearic` — Illes Balears

## `GET /alerts`
- Auth: none for current MVP.
- Query params: `agent_id?: int` — filter alerts to a specific sales agent.
- Response `200`: `SalesAlertResponse[]`
- `SalesAlertResponse`:
  - `id: string`
  - `clientName: string`
  - `riskLevel: "low" | "medium" | "high"` (mapped from DB "high"/"medium"/"low")
  - `churnProbability: int`
  - `purchasePropensity: int`
  - `customerValue: "low" | "medium" | "high"`
  - `explanation: string`
  - `churnType: string` (e.g. "Total", "Producto 4566")
  - `status: "pending"` (always pending from DB; mutations are local frontend state)
  - `interactions: []`
  - `events: []`
  - `alertContextJson: string | null` (JSON blob of ML ctx_* fields for LLM enrichment)
  - `predictedNextPurchase: string | null` (ISO date string)
  - `lastOrderDate: string | null` (ISO date string)
- Data source: `regional_alerts` JOIN `clients`, ordered by `created_at DESC`. Filtered by `clients.agent_id` if `agent_id` query param provided.

## `GET /agents`
- Auth: none for current MVP.
- Request: none.
- Response `200`: `AgentResponse[]`
  - `id: int`
  - `name: string`
  - `email: string`
  - `zone: "north" | "east" | "south" | "canary" | "balearic"`
  - `managerId: int`
- Data source: `sales_agents` JOIN `regional_managers` JOIN `regions`, ordered by agent id.

## `GET /auth/me`
- Auth: `Authorization: Bearer <token>`.
- Request: none.
- Response `200`:
  - `{ id: number, email: string, created_at: datetime }`
- Errors:
  - `401` for missing, invalid, expired, or unknown-user token.
