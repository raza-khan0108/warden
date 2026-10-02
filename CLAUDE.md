# Warden

AI software engineering command center. Connects to GitHub, indexes repos/issues/PRs,
answers questions with citations, reviews PRs, and proposes actions that require
human approval before anything writes back to GitHub.

## Stack

- Frontend: Next.js + TypeScript + Tailwind (apps/web)
- Backend API: FastAPI (apps/api)
- Background jobs: Celery (apps/worker)
- Agent orchestration: LangGraph
- Database: Postgres + pgvector
- Queue/cache: Redis
- Object storage: S3-compatible (MinIO locally)
- Tracing: Langfuse / OpenTelemetry
- Deployment: Docker Compose (V1), Kubernetes later

## Project structure

```text
warden/
  apps/
    web/        # Next.js frontend
    api/        # FastAPI backend
    worker/     # Celery workers (ingestion, embeddings)
  packages/
    mcp-gateway/  # MCP tool gateway + policy engine
    shared/       # shared types/schemas used by api and worker
  alembic/        # DB migrations
  docs/
    plan.md         # V1 scope + 6-week build plan
    schema.md        # Data model reference
    progress.md       # What's done, what's next — READ THIS FIRST each session
  docker-compose.yml
  .env.example
```

## Non-negotiable conventions

- Every DB query that touches tenant data filters by `org_id`. No exceptions.
- No tool call writes to GitHub (or any external system) directly. Every write goes
  through `packages/mcp-gateway`, which classifies risk and creates an `approvals`
  record for anything above read-only before executing.
- Every schema change is an Alembic migration. No manual DDL, no editing migrations
  that have already been applied.
- Agent/tool actions are logged to `audit_logs` (append-only, never update or delete rows).
- Don't add new third-party services (search engines, vector DBs, queues) beyond what's
  in docs/plan.md without flagging it first — V1 is intentionally Postgres-only.

## How to work in this repo

1. Read `docs/progress.md` first. It says what's done and what the next task is.
2. Do ONE task from the current week's checklist per session. Don't jump ahead to
   later weeks even if it seems faster.
3. When a task is done: update `docs/progress.md` (check the box, add a one-line note
   if something deviated from plan.md), then stop — don't auto-start the next task.
4. Write or update tests for anything in apps/api or packages/mcp-gateway.
5. Never commit directly to main. Branch, commit, leave the PR for review.

## Reference docs

- `docs/plan.md` — V1 scope, architecture, and the 6-week plan
- `docs/schema.md` — full data model (tables, relationships, key decisions)
