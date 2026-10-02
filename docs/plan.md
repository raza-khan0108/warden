# Warden — V1 Plan

## Goal

Connect a GitHub org, index its repos/issues/PRs, answer questions with citations,
review PRs, and propose actions that need human approval before anything is written
back to GitHub.

## In scope for V1

- GitHub login, orgs, roles (owner/member), GitHub App install
- Ingestion: code, docs, issues, PRs. Background jobs, incremental updates via webhooks
- Hybrid search (pgvector + Postgres full-text), code-aware chunking
- Chat with citations (`file@commit:lines`, PR/issue links)
- PR review agent: bugs, security, missing tests — posted as a draft comment
- Issue summarization and duplicate detection
- Approval-gated actions: post PR comment, create issue. No merges, no code writes.
- Audit log (append-only)
- Small eval set (30-50 Q&A pairs) with retrieval hit rate + faithfulness scoring
- Docker Compose deploy

## Explicitly out of scope for V1

Slack/Jira integration, SQL analyst agent, multi-agent workflows, agent marketplace,
billing, dependency graph, local/offline models. These are V2+.

## Definition of done for V1

- Questions about the indexed repo return correct citations
- A new PR produces a review draft within a couple of minutes of being opened
- Nothing writes to GitHub without a recorded approval

## Architecture

```text
Next.js UI ──► FastAPI API ──► Postgres (pgvector, FTS)
                 │  ▲            Redis · S3/MinIO
   GitHub        │  │
   webhooks ─────┤  └── Celery workers (clone, chunk, embed)
                 ▼
          Agent service (LangGraph)
                 ▼
          MCP gateway ── policy engine ──► GitHub MCP server
                 │
                 └─ read: auto-allow · write: create approval, wait

Tracing: Langfuse / OpenTelemetry
```

Key decisions:
- GitHub App (not just OAuth) for repo access — gives webhooks and fine-grained permissions
- Postgres only in V1, no separate search engine
- LangGraph interrupts pause the agent at write tools until a human approves
- Every tool call goes through the gateway — this is the product's differentiator

See `docs/schema.md` for the full data model.

## 6-week build plan

### Week 1 — Foundations
- Monorepo layout (apps/web, apps/api, apps/worker, packages/)
- Docker Compose: Postgres (with pgvector), Redis, MinIO
- GitHub login + orgs + roles
- GitHub App creation and install flow
- CI pipeline (lint, type-check, test on push)

### Week 2 — Ingestion
- Repo fetch/clone on install
- Code-aware chunking (tree-sitter)
- Issue/PR ingestion
- Embedding generation, stored in pgvector
- Celery job queue + status tracking
- Job status UI
- GitHub webhook handling for incremental updates

### Week 3 — Retrieval and chat
- Hybrid search: pgvector + Postgres full-text, rank fusion
- Streaming chat endpoint
- Citation UI (opens file at specific lines)
- Langfuse/OTel tracing wired in

### Week 4 — MCP gateway and policy
- GitHub MCP server integration
- Risk classification (read vs write tools)
- `tool_calls` + `audit_logs` tables wired to every call
- LangGraph agent loop with interrupt-on-write

### Week 5 — PR agent and approvals
- Webhook-triggered PR review (bugs, security, missing tests)
- Approval inbox UI
- Approve → post PR comment via gateway
- Issue summarization + duplicate detection

### Week 6 — Evals and hardening
- Eval set (30-50 cases) + dashboard (retrieval hit rate, faithfulness)
- Rate limiting, retries on job failures
- Test coverage pass
- Docs pass (README, setup instructions)
- Deploy, demo against a real public repo

If a week slips: cut duplicate detection first, then turn the eval dashboard into a
CLI script instead of a UI. Protect weeks 4-5 — the gateway and approval flow are the
point of the project.

## Reference repos (study order)

1. **stacklok/toolhive** — secure MCP server management, isolation, permissions.
   Shapes the gateway and sandbox design. Study first.
2. **aipotheosis-labs/aci** — tool-calling platform, tool auth patterns, direct
   calls vs MCP.
3. **apisec-inc/AI-Surface** — PR-time analysis, closest existing match to the
   PR review flow.
4. **deepset-ai/haystack** — hybrid retrieval and evaluation patterns. Read for
   ideas, don't adopt as the framework.
5. **nuwax-ai/nuwax** — agent platform structure (skills, workflows, sandbox).
   Skim architecture only.

Skip for now (useful later for V2 multi-tenancy): agentset, private-gpt, wanwu,
53AIHub, OpenDerisk.
