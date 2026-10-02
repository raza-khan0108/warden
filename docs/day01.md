# Warden: Day 1 Study Guide

**Topic:** Repo and database setup (Docker Compose, Postgres, pgvector, env config, architecture doc)
**Time:** about 3 hours (1.5 hrs reading, 1.5 hrs hands-on)
**Goal:** understand every line of `docker-compose.yml`, know what pgvector does, and be able to defend the architecture choices.

---

## Study plan

| Block | Topic | Time |
|-------|-------|------|
| 1 | Docker Compose | 40 min |
| 2 | Postgres in Docker + psql | 30 min |
| 3 | Embeddings and pgvector | 50 min |
| 4 | Env files, secrets, .gitignore | 15 min |
| 5 | Monorepo and architecture docs | 20 min |
| 6 | Hands-on labs | 40 min |
| 7 | Self-check | 15 min |

---

## 1. Docker Compose

### What it is
Compose describes a set of containers in one YAML file, so `docker compose up` starts your whole dev environment the same way on any machine.

### Concepts to learn

| Concept | Meaning | In our file |
|---------|---------|-------------|
| **Image** | Read-only template a container is built from | `pgvector/pgvector:pg16` (Postgres 16 with pgvector preinstalled) |
| **Container** | A running instance of an image | `warden-db` |
| **Service** | One named entry under `services:` | `db` |
| **Port mapping** | `HOST:CONTAINER` | `"5432:5432"` exposes the DB on `localhost:5432` |
| **Named volume** | Docker-managed storage that outlives the container | `pgdata` |
| **Bind mount** | Maps a file or folder from your machine into the container | `./db/init.sql:/docker-entrypoint-initdb.d/init.sql:ro` |
| **Environment** | Variables passed into the container | `POSTGRES_USER`, etc. |
| **Healthcheck** | A command Docker runs to decide if the service is ready | `pg_isready` |
| **Restart policy** | What happens if the container stops | `unless-stopped` |
| **Default network** | Compose creates one; services reach each other by service name | `warden_default` (you saw it created) |

### Read the file line by line

```yaml
image: pgvector/pgvector:pg16
```
Pull this image from Docker Hub. The tag `pg16` pins the Postgres major version.

```yaml
POSTGRES_USER: ${POSTGRES_USER:-warden}
```
`${VAR:-default}` reads `VAR` from your shell or `.env` file. If it is unset or empty, it uses `warden`. Compose automatically loads a `.env` file sitting next to `docker-compose.yml`.

```yaml
volumes:
  - pgdata:/var/lib/postgresql/data
```
Postgres stores its files in `/var/lib/postgresql/data`. Mounting a named volume there means data survives container restarts and removal.

```yaml
- ./db/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
```
Any `.sql` file in that folder runs when the database is first created. `:ro` means read-only inside the container.

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-warden} -d ${POSTGRES_DB:-warden}"]
  interval: 5s
  timeout: 3s
  retries: 10
```
Every 5 seconds Docker runs `pg_isready`. The status goes `starting` → `healthy`. After 10 failures in a row it becomes `unhealthy`. Later, the API service will wait for `healthy` using `depends_on: condition: service_healthy`.

### Commands to know

| Command | What it does |
|---------|--------------|
| `docker compose up -d db` | Start the `db` service in the background |
| `docker compose ps` | Show service status |
| `docker compose logs -f db` | Follow logs |
| `docker compose exec db <cmd>` | Run a command inside the running container |
| `docker compose stop` | Stop containers, keep them and their data |
| `docker compose down` | Remove containers and network, **keep volumes** |
| `docker compose down -v` | Remove containers, network **and volumes (data is deleted)** |
| `docker compose config` | Print the file with variables resolved (great for debugging) |
| `docker volume ls` | List volumes |

### Key gotcha
`down` keeps your data. `down -v` wipes it. Init scripts only run on an **empty** data directory, so after changing `init.sql` you need `down -v` for it to run again.

### Resources
- Docker docs: Compose file reference and "Interpolation" section (docs.docker.com/compose)
- Docker docs: Volumes (docs.docker.com/engine/storage/volumes)

---

## 2. Postgres in Docker

### What the official image does on first start
1. Sees an empty data directory.
2. Creates the user, password, and database from `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.
3. Runs every script in `/docker-entrypoint-initdb.d/` in alphabetical order.
4. Starts the server.

On later starts, steps 1 to 3 are skipped because the data already exists.

### Essential tools
- `pg_isready`: checks whether the server accepts connections (used by the healthcheck).
- `psql`: the command-line client.

### psql cheat sheet

Open a shell:
```powershell
docker compose exec db psql -U warden -d warden
```

| Command | Meaning |
|---------|---------|
| `\l` | List databases |
| `\dt` | List tables |
| `\d tablename` | Describe a table |
| `\dx` | List installed extensions |
| `\du` | List roles |
| `\x` | Toggle expanded output |
| `\q` | Quit |

Run one statement without opening a shell (use one `-c` per statement, and PowerShell needs the quotes):
```powershell
docker compose exec db psql -U warden -d warden -c "SELECT version();"
```

### Concepts to understand
- **Connection string:** `postgresql+psycopg://warden:warden@localhost:5432/warden`
  Format: `driver://user:password@host:port/database`. The `+psycopg` part tells SQLAlchemy which Python driver to use (Day 3).
- **Host name:** from your machine it is `localhost`. From another container on the same Compose network it is `db` (the service name).
- **Extension:** an add-on installed per database with `CREATE EXTENSION`. The pgvector image ships the files, but each database must enable it.

---

## 3. Embeddings and pgvector

This block matters most. Everything in Warden's search and chat features depends on it.

### 3.1 What is an embedding?
An embedding turns text (or code) into a list of numbers, called a vector, so that **similar meaning gives nearby vectors**.

Example (real embeddings have hundreds or thousands of dimensions; this uses 3):

| Text | Vector |
|------|--------|
| "open a file" | [0.9, 0.1, 0.2] |
| "read a document" | [0.8, 0.2, 0.3] |
| "bake a cake" | [0.1, 0.9, 0.7] |

The first two are close together; the third is far away. Search then becomes: embed the question, find the nearest stored vectors.

### 3.2 Where this fits in Warden (RAG)
RAG means Retrieval-Augmented Generation.

1. **Index (offline):** split code into chunks, embed each chunk, store in Postgres.
2. **Retrieve (per question):** embed the question, fetch the closest chunks.
3. **Generate:** give those chunks plus the question to an LLM, which writes the answer.

The LLM never sees your whole repo, only the relevant chunks. That is why retrieval quality matters.

### 3.3 Distance measures

| Measure | pgvector operator | Idea |
|---------|-------------------|------|
| Euclidean (L2) | `<->` | Straight-line distance |
| Cosine distance | `<=>` | Angle between vectors, ignores length |
| Negative inner product | `<#>` | Dot product, negated so smaller is closer |

- Cosine distance = `1 - cosine similarity`. Distance 0 means identical direction.
- Most text embedding models work well with **cosine**. Check your chosen model's docs in Week 2.
- For every operator, **smaller value means more similar**, so queries use `ORDER BY ... ASC`.

### 3.4 pgvector basics

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE items (
  id bigserial PRIMARY KEY,
  content text,
  embedding vector(3)          -- the number is the dimension
);

INSERT INTO items (content, embedding) VALUES
  ('open a file',     '[0.9, 0.1, 0.2]'),
  ('read a document', '[0.8, 0.2, 0.3]'),
  ('bake a cake',     '[0.1, 0.9, 0.7]');

-- 2 nearest neighbours to a query vector
SELECT content, embedding <=> '[0.85, 0.15, 0.25]' AS distance
FROM items
ORDER BY embedding <=> '[0.85, 0.15, 0.25]'
LIMIT 2;
```

Rules to remember:
- Every vector in a column must have the same dimension as declared.
- The dimension is fixed by the **embedding model** you pick. Changing model later means re-embedding everything. This is why the `chunks` table's `N` is decided in Week 2.

### 3.5 Indexes: HNSW vs IVFFlat
Without an index, Postgres compares against every row (exact but slow at scale). Vector indexes give **approximate** nearest neighbour search: much faster, tiny accuracy loss.

| | HNSW | IVFFlat |
|---|------|---------|
| Speed and recall | Better | Good |
| Build time and memory | Higher | Lower |
| Needs data before building | No | Yes (learns cluster centres from existing rows) |
| Typical choice | Default recommendation | Very large or memory-tight setups |

```sql
CREATE INDEX ON items USING hnsw (embedding vector_cosine_ops);
```
The operator class must match your query operator: `vector_cosine_ops` for `<=>`, `vector_l2_ops` for `<->`, `vector_ip_ops` for `<#>`.

For a single repo's worth of chunks, you may not need an index at all. Know it exists.

### 3.6 Limits worth knowing
- A `vector` column supports up to 16,000 dimensions, but HNSW and IVFFlat indexes on it support up to 2,000. Common embedding sizes (384 to 1536) are fine; very large models may need reduced dimensions.

### 3.7 Why pgvector and not a dedicated vector database?

| pgvector (our choice) | Dedicated (Qdrant, Pinecone, etc.) |
|---|---|
| One database for relational data and vectors | Second system to run and sync |
| Joins, transactions, filters in plain SQL | Own query language and API |
| Fine up to millions of vectors | Better at very large scale and special features |
| Simple ops | More moving parts |

For V1 the simplicity wins. Be able to say that in one sentence.

### Resources
- pgvector README (github.com/pgvector/pgvector): read "Getting Started", "Querying", "Indexing".
- Search for a short "what are embeddings" explainer and read one (any reputable one, 15 min).

---

## 4. Env files, secrets, .gitignore

### Why this matters
Config that changes between environments (passwords, tokens, URLs) should live outside the code. Secrets in Git history are hard to fully remove and are a common cause of leaks.

### The pattern we use

| File | Committed? | Purpose |
|------|-----------|---------|
| `.env.example` | Yes | Template with safe placeholder values, shows what is needed |
| `.env` | **No** | Your real values |

Your `.gitignore` handles it:
```
.env
.env.*
!.env.example      # the ! re-includes the example file
```

### Commands to know
```powershell
git check-ignore -v .env           # prints the rule that ignores it
git status                         # .env must NOT appear
git ls-files | Select-String env   # only .env.example should be tracked
```

### If you ever commit a secret by accident
1. Treat it as compromised and **revoke or rotate it immediately** (deleting the commit is not enough).
2. Then clean up history if needed.

Relevant later: `GITHUB_TOKEN` (Day 4) must never be committed.

### Resource
- 12factor.net, section III "Config" (5 min read).

---

## 5. Monorepo and architecture docs

### Monorepo
One Git repo holds `backend/`, `frontend/`, `docs/`, and infra files. Benefits for a solo project: one clone, one CI file, one PR can touch API and UI together. Trade-off: tooling for each part must be kept separate (its own dependencies and lint config).

### Reading your `docs/architecture.md`
Be able to explain each section out loud:
- **Components:** who does what.
- **Data flow:** the numbered path from "add repo" to "answer a question".
- **Tables:** why each column exists (for example, why we store the blob `sha`: to skip unchanged files when re-syncing).
- **Decisions:** the reasoning you would give in an interview.

### Writing a good architecture doc
- One page, plain language.
- Say what you chose **and what you rejected**, with the reason.
- List what is out of scope so the project stays small.
- Update it when the design changes. An outdated doc is worse than none.

---

## 6. Hands-on labs

Do these in order with your running database.

### Lab 1: Read the resolved config
```powershell
docker compose config
```
Find where `${POSTGRES_USER:-warden}` became a real value. Then edit `.env` to set `POSTGRES_USER=test`, run it again, and see the change. Set it back to `warden`.

### Lab 2: Explore Postgres
```powershell
docker compose exec db psql -U warden -d warden
```
Inside psql run: `\l`, `\dx`, `\du`, `SELECT version();`, then `\q`.

### Lab 3: Persistence
```powershell
docker compose exec db psql -U warden -d warden -c "CREATE TABLE t(id int);"
docker compose down
docker compose up -d db
docker compose exec db psql -U warden -d warden -c "\dt"
```
`t` should still exist. Then:
```powershell
docker compose down -v
docker compose up -d db
docker compose exec db psql -U warden -d warden -c "\dt"
```
Now it should be gone (and `vector` still installed, because `init.sql` ran again on the fresh volume).

### Lab 4: Try pgvector by hand
Open psql and run the `items` example from section 3.4. Then:
1. Change the query vector to `[0.1, 0.8, 0.6]`. Which row comes first now?
2. Replace `<=>` with `<->`. Does the order change?
3. Try inserting `'[1,2]'` and read the error.
4. Create the HNSW index from section 3.5.
5. Clean up: `DROP TABLE items;`

### Lab 5: Break the healthcheck (optional)
Change the healthcheck user to `nobody` in the compose file, run `docker compose up -d db`, watch `docker compose ps` become `unhealthy`, then fix it.

### Lab 6: Git hygiene
Run the three commands from section 4. Confirm `.env` is ignored and `.env.example` is tracked.

---

## 7. Self-check

Answer without looking. Answers are at the bottom.

1. What is the difference between `docker compose down` and `docker compose down -v`?
2. What does `${POSTGRES_USER:-warden}` do?
3. Why did `init.sql` not run when you restarted the container?
4. What does `5432:5432` mean, in which order?
5. What is a named volume and why do we use one for Postgres?
6. What does the healthcheck do and what is it used for later?
7. What is an embedding?
8. Which pgvector operator is cosine distance, and does a larger or smaller value mean more similar?
9. Why is the embedding dimension fixed once you pick a model?
10. HNSW or IVFFlat: which would you start with and why?
11. Why not use a separate vector database for V1?
12. Why is `.env.example` committed but `.env` not?
13. What should you do if you accidentally push a token?
14. Why do we store the blob `sha` in `repo_files`?

### Answers
1. `down` removes containers and the network but keeps volumes (data stays). `down -v` also deletes volumes (data is lost).
2. Uses the value of `POSTGRES_USER` from the environment or `.env`; if unset or empty, uses `warden`.
3. Init scripts only run when the data directory is empty. The volume already had data.
4. `HOST:CONTAINER`. Port 5432 on your machine maps to port 5432 in the container.
5. Docker-managed storage that outlives the container. Without it, DB data would vanish when the container is removed.
6. Runs `pg_isready` periodically to report `healthy` or `unhealthy`. Later the API service waits for `healthy` before starting.
7. A list of numbers representing text, where similar meaning gives nearby vectors.
8. `<=>`. Smaller means more similar.
9. The vector column has a declared size and the model outputs a fixed number of numbers. Different models give different sizes, so switching means re-embedding.
10. HNSW: better speed and recall, and it does not need existing data to build.
11. One database is simpler to run and query (joins, filters, transactions in SQL), and it is enough for V1's scale.
12. The example documents required settings with safe placeholders; the real file holds secrets that must not enter Git history.
13. Revoke or rotate it immediately, then clean history if needed.
14. Git's blob SHA changes only when file content changes, so we can skip unchanged files on re-sync.

---

## You are ready for Day 2 if you can

- [ ] Explain every line of `docker-compose.yml`
- [ ] Open psql and inspect the database
- [ ] Explain embeddings and cosine distance in two sentences
- [ ] Say why pgvector fits V1
- [ ] Prove `.env` is not tracked by Git
- [ ] Explain the flow in `docs/architecture.md`
