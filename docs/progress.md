# Warden — Progress

Read this file first in every Claude Code session. Pick the next unchecked item,
do that one task, check it off, stop.

## Week 1 — Foundations
- [x] Monorepo layout (apps/web, apps/api, apps/worker, packages/)
- [x] Docker Compose: Postgres (pgvector), Redis, MinIO
- [x] GitHub login + orgs + roles
- [x] GitHub App creation and install flow
- [ ] CI pipeline (lint, type-check, test on push)

## Week 2 — Ingestion
- [ ] Repo fetch/clone on install
- [ ] Code-aware chunking (tree-sitter)
- [ ] Issue/PR ingestion
- [ ] Embedding generation into pgvector
- [ ] Celery job queue + status tracking
- [ ] Job status UI
- [ ] GitHub webhook handling for incremental updates

## Week 3 — Retrieval and chat
- [ ] Hybrid search (pgvector + full-text, rank fusion)
- [ ] Streaming chat endpoint
- [ ] Citation UI (opens file at specific lines)
- [ ] Langfuse/OTel tracing

## Week 4 — MCP gateway and policy
- [ ] GitHub MCP server integration
- [ ] Risk classification (read vs write tools)
- [ ] tool_calls + audit_logs wired to every call
- [ ] LangGraph agent loop with interrupt-on-write

## Week 5 — PR agent and approvals
- [ ] Webhook-triggered PR review
- [ ] Approval inbox UI
- [ ] Approve → post PR comment via gateway
- [ ] Issue summarization + duplicate detection

## Week 6 — Evals and hardening
- [ ] Eval set (30-50 cases) + dashboard
- [ ] Rate limiting, retries on job failures
- [ ] Test coverage pass
- [ ] Docs pass
- [ ] Deploy, demo against a real public repo

## Notes / deviations from plan.md

- 2026-10-02: Reorganized backend/ → apps/api/, moved alembic to root, added Docker services (Redis, MinIO) to docker-compose.yml
- 2026-10-02: Completed Docker Compose setup: fixed healthchecks, added comprehensive .env.example, created DOCKER_SETUP.md guide
- 2026-10-02: GitHub login implemented with SQLAlchemy models, JWT auth, GitHub OAuth callback, and token validation. All DB queries filter by org_id per non-negotiable convention
- 2026-10-02: GitHub App install flow: added integrations table migration, encrypted credential storage (Fernet), GET /integrations/github/install-url, POST /integrations/github/install webhook, list/get integration endpoints, frontend component to trigger install
