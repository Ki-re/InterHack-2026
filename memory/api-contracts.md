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
  - `alert: AlertContext` — `{ clientName, riskLevel, churnProbability, purchasePropensity, customerValue, churnType, explanation }`
  - `history: ChatMessage[]` — `[{ role: "user"|"assistant", content: string }, ...]` (full prior conversation)
  - `question: string` — the new user message
- Response `200`: `{ response: string }`
- Errors:
  - `503` if `GEMINI_API_KEY` is not configured.
  - `502` if the Gemini API call fails.

## `GET /auth/me`
- Auth: `Authorization: Bearer <token>`.
- Request: none.
- Response `200`:
  - `{ id: number, email: string, created_at: datetime }`
- Errors:
  - `401` for missing, invalid, expired, or unknown-user token.