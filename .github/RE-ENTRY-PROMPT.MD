You are working inside an EXISTING fullstack hackathon repository.

DO NOT reinitialize the project.
DO NOT recreate existing structure.
DO NOT overwrite working systems unless explicitly required.

Your job is to understand the current state, align with the existing architecture, and continue development safely using the established patterns.

---

# 1. CONTEXT FIRST (MANDATORY)

Before making any changes:

1. Inspect repository structure
2. Read:
   - AGENTS.md
   - .github/copilot-instructions.md
   - .github/instructions/*
   - .github/skills/*
   - /memory/* (CRITICAL)
3. Identify current:
   - backend state
   - frontend state
   - API contracts
   - docker setup
   - known issues
   - active development focus

Summarize internally (do not output unless asked):
- current system state
- what is implemented
- what is missing
- what is broken

---

# 2. SOURCE OF TRUTH RULE

The repository already has a memory system.

YOU MUST FOLLOW IT.

Primary sources of truth:

1. /memory/current-state.md
2. /memory/api-contracts.md
3. /memory/decisions.md
4. actual codebase state

If memory and code disagree:
→ code wins, then update memory.

---

# 3. ARCHITECTURE CONSTRAINTS

You MUST respect:

Frontend:
- React + Vite + TypeScript
- TailwindCSS
- shadcn/ui
- React Router
- TanStack Query

Backend:
- FastAPI
- SQLAlchemy async
- SQLite (default)
- Alembic migrations

Infra:
- Docker Compose only
- no external infrastructure

---

# 4. DEVELOPMENT RULES

- Do NOT introduce new frameworks
- Do NOT refactor architecture unless requested
- Keep changes incremental and safe
- Maintain compatibility with Docker setup
- Prefer editing over rewriting

---

# 5. MEMORY SYSTEM (MANDATORY BEHAVIOR)

After ANY change:

YOU MUST RUN MEMORY SYNC LOGIC:

Update:

- /memory/current-state.md → always
- /memory/api-contracts.md → if API changes
- /memory/decisions.md → if architecture changes
- /memory/known-issues.md → if bugs appear
- /memory/architecture.md → if structure changes

Memory must always reflect REAL repo state.

No exceptions.

---

# 6. SKILLS SYSTEM

If a skill applies, use it.

Available skills are located in:
.github/skills/

You should prefer skills over ad-hoc implementation when possible.

Especially:

- fullstack-feature
- fastapi-crud
- react-page
- dockerize-service
- debug
- memory-sync

---

# 7. CURRENT WORK MODE

You are in CONTINUATION MODE.

Your goal is:
- extend existing system
- fix issues
- implement features
- improve consistency
- maintain working Docker setup

NOT to scaffold or restart the project.

---

# 8. OUTPUT RULES

When asked to implement something:

1. Plan briefly
2. Implement incrementally
3. Ensure compatibility
4. Update memory system
5. Verify Docker consistency

---

# 9. SAFETY RULE

If unsure about current architecture:
→ STOP and inspect repo before proceeding

Never assume structure.

---

# 10. FINAL OBJECTIVE

Maintain a stable, fast-moving hackathon codebase where:
- frontend and backend stay aligned
- memory is always updated
- Docker always works
- features are incremental and safe