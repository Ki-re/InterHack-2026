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

## `GET /auth/me`
- Auth: `Authorization: Bearer <token>`.
- Request: none.
- Response `200`:
  - `{ id: number, email: string, created_at: datetime }`
- Errors:
  - `401` for missing, invalid, expired, or unknown-user token.
