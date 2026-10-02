# Warden — Data Model

Every table below that holds tenant data has an `org_id` column. Every query must
filter by it — this is the #1 rule in CLAUDE.md for a reason.

## Tenancy

- **organizations** — id, name, created_at
- **users** — id, email, github_id, created_at
- **memberships** — org_id, user_id, role (owner | member)
- **integrations** — org_id, type (github_app | slack | jira, V1 = github_app only),
  installation_id, encrypted_creds, created_at

## Content

- **repositories** — org_id, github_repo_id, full_name, last_indexed_sha,
  index_status (pending | indexing | ready | failed)
- **documents** — org_id, repo_id, source_type (code | issue | pr | doc),
  path, url, commit_sha, content_hash, version
- **chunks** — document_id, text, symbol, start_line, end_line, embedding (vector),
  tsv (tsvector, for full-text search), metadata (jsonb)

## Jobs

- **ingestion_jobs** — org_id, repo_id, kind (clone | chunk | embed | webhook_update),
  status, attempts, error, created_at, finished_at

## Chat

- **conversations** — org_id, user_id, created_at
- **messages** — conversation_id, role, content, citations (jsonb), trace_id, created_at

## Agents

- **agents** — org_id, name, prompt, model, allowed_tools (jsonb array), version
- **agent_runs** — agent_id, trigger (chat | pr_webhook | manual), status,
  tokens_used, cost, started_at, finished_at
- **tool_calls** — agent_run_id, tool, args (jsonb), risk (read | write),
  status (auto_allowed | pending_approval | approved | rejected | executed), result

## Governance

- **tool_policies** — org_id, tool, risk, requires_approval (bool)
- **approvals** — tool_call_id, decided_by (user_id), decision (approve | reject),
  reason, decided_at
- **audit_logs** — org_id, actor, action, target, metadata (jsonb), ts
  — append-only, never updated or deleted

## Evals

- **eval_sets** — org_id, name, description
- **eval_cases** — eval_set_id, question, expected_citations, expected_answer_notes
- **eval_runs** — eval_set_id, model, started_at, finished_at
- **eval_results** — eval_run_id, eval_case_id, retrieved_citations, answer,
  hit_rate, faithfulness_score

## Indexing notes

- Index `org_id` on every tenant table.
- Index `chunks.embedding` with an IVFFlat or HNSW index (pgvector) once there's
  enough data to tune it — don't bother in week 2, revisit in week 3.
- Index `chunks.tsv` with GIN for full-text search.
- `audit_logs` should be append-only at the application layer (no UPDATE/DELETE
  grants on that table for the app's DB role, if you want to enforce it at the DB level).
