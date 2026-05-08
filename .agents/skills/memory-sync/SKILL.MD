---
name: memory-sync
description: Always run after any code modification to keep the /memory folder synchronized with the current state of the repository
---

# memory-sync

This skill is ALWAYS used after any code modification in the repository.

## Purpose
Ensure /memory folder stays synchronized with the current state of the system.

---

## Trigger conditions (IMPORTANT)
This skill must run automatically after:

- backend changes (FastAPI routes, models, services)
- frontend changes (pages, hooks, API calls)
- docker changes
- database schema changes
- architectural decisions
- bug fixes

---

## Behavior

When triggered:

1. Update /memory/current-state.md
2. Update /memory/api-contracts.md if APIs changed
3. Update /memory/decisions.md if architecture changed
4. Update /memory/known-issues.md if bugs exist
5. Update /memory/architecture.md if structure changed
6. Keep all files concise and factual

---

## Hard rule

Memory must reflect REAL state of repository, not intended state.

Never omit updates.

Never ask for confirmation.