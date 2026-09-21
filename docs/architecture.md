# Warden Architecture (V1)

## Goal

Connect a GitHub repository, index its code, then answer questions about it and review its pull requests.

## Components

| Component | Tech | Job |
|-----------|------|-----|
| Frontend | Next.js | Add repos, trigger sync, show status (later: chat, PR reviews) |
| Backend API | FastAPI | REST endpoints, GitHub access, indexing logic |
| Database | Postgres 16 + pgvector | Stores repos, files, and (later) code chunks with embeddings |
| GitHub | REST API | Source of repo metadata, file trees, file contents, PRs |
| LLM / embeddings | TBD (Week 2) | Turns chunks into vectors; answers questions |

## Data flow

1. **Add repo:** UI sends `owner/name`. Backend calls GitHub, saves a `repositories` row (`status = pending`).
2. **Sync:** Backend fetches the repo's file tree, drops junk (binaries, lockfiles, `node_modules`, huge files), and saves the rest to `repo_files`. Status goes `syncing` then `ready` or `failed`.
3. **Index (Week 2):** Backend fetches file contents, splits them into chunks, embeds each chunk, and saves to `chunks`.
4. **Ask (later):** Question is embedded, nearest chunks are found in pgvector, and the LLM answers using them.
5. **PR review (later):** Backend fetches a PR diff, retrieves related chunks, and the LLM writes review comments.

```
UI ──► FastAPI ──► GitHub API
          │
          ▼
   Postgres + pgvector
   repositories → repo_files → chunks
```

## Tables

### repositories (Week 1)

| Column | Type | Notes |
|--------|------|-------|
| id | int PK | |
| full_name | varchar, unique | `owner/name` |
| owner, name | varchar | |
| default_branch | varchar | |
| description | text, null | |
| html_url | varchar | |
| status | varchar | `pending`, `syncing`, `ready`, `failed` |
| last_synced_at | timestamptz, null | |
| created_at | timestamptz | |

### repo_files (Week 1)

| Column | Type | Notes |
|--------|------|-------|
| id | int PK | |
| repository_id | FK → repositories, cascade delete | |
| path | text | unique with repository_id |
| sha | varchar(40) | Git blob SHA; lets us skip unchanged files on re-sync |
| size | int | bytes |
| language | varchar, null | from file extension |

### chunks (planned, Week 2)

| Column | Type | Notes |
|--------|------|-------|
| id | int PK | |
| repo_file_id | FK → repo_files, cascade delete | |
| chunk_index | int | order within the file |
| start_line, end_line | int | for citing sources |
| content | text | |
| embedding | vector(N) | N depends on the embedding model chosen in Week 2 |

## Decisions

- **Postgres + pgvector** instead of a separate vector DB: one database, simple ops, enough for V1.
- **Sync stores metadata only.** Contents are fetched at index time, so sync stays fast.
- **Blob SHA stored per file** to make re-indexing incremental later.

## Out of scope for V1

Auth and multi-user, private-repo OAuth flow, webhooks, background workers.
