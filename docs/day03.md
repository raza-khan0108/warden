# Warden: Day 3 Study Guide

**Topic:** Database layer (SQLAlchemy 2.0 models, sessions, Alembic migrations, pgvector wiring)
**Time:** about 3 hours (1.5 hrs reading, 1.5 hrs hands-on)
**Goal:** understand every line of `db.py`, `models.py`, `alembic/env.py`, and the first migration — and be able to explain what happens, in order, when you run `alembic upgrade head`.

---

## Study plan

| Block | Topic | Time |
|-------|-------|------|
| 1 | ORMs and SQLAlchemy 2.0 style | 30 min |
| 2 | Engine, Session, and the request lifecycle | 30 min |
| 3 | Declarative models: `Mapped`, columns, relationships | 40 min |
| 4 | Migrations and Alembic | 40 min |
| 5 | Wiring pgvector through SQLAlchemy | 15 min |
| 6 | Hands-on labs | 40 min |
| 7 | Self-check | 15 min |

---

## 1. ORMs and SQLAlchemy 2.0 style

### What an ORM is
An Object-Relational Mapper lets you work with database rows as Python objects instead of writing raw SQL strings everywhere. `Repository` and `RepoFile` in `models.py` are Python classes; SQLAlchemy translates operations on them into SQL.

### Why not just write raw SQL?
You still can (and sometimes should — see `text("SELECT 1")` in `health.py`), but for everyday work an ORM gives you:
- Autocomplete and type checking on columns
- Automatic handling of relationships (joins) and cascades
- One place (`models.py`) that describes your whole schema, which Alembic can read

### 2.0-style vs "legacy" SQLAlchemy
SQLAlchemy 2.0 (released 2023) introduced fully-typed models using Python's type hints:
```python
id: Mapped[int] = mapped_column(Integer, primary_key=True)
```
Older code (and a lot of tutorials online) still shows the pre-2.0 style:
```python
id = Column(Integer, primary_key=True)
```
Both still work, but `Mapped[...]` is now the recommended style because your editor and type checker understand the column's Python type. Warden uses 2.0-style throughout — if you search for examples online, prefer ones showing `Mapped`.

### Resource
- SQLAlchemy docs, "ORM Quick Start" (official tutorial, uses 2.0 style — 15 min).

---

## 2. Engine, Session, and the request lifecycle

### The three layers
```python
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, ...)
```

| Layer | What it is | Lifetime |
|-------|-----------|----------|
| **Engine** | Manages a pool of actual database connections | Created once, lives for the app's lifetime |
| **Session** | A workspace for a set of operations (add, query, commit) | Created per request, then closed |
| **Connection** | The raw TCP link to Postgres | Borrowed from the engine's pool, returned when the session closes |

### Why `pool_pre_ping=True`
Before handing out a pooled connection, SQLAlchemy runs a cheap `SELECT 1` to check it's still alive. Without this, a connection that Postgres silently dropped (say, after your `docker compose restart`) would surface as a confusing error on the *next* request instead of being quietly replaced.

### The `get_db` dependency
```python
def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```
This is a **generator function** used as a FastAPI dependency. The pattern:
1. FastAPI calls `get_db()`, gets a generator.
2. It runs up to `yield db`, and hands `db` to your endpoint (`Session = Depends(get_db)` in `health_db`).
3. Your endpoint runs, using `db` to query.
4. After the endpoint returns (success or exception), FastAPI resumes the generator past `yield`, running `db.close()`.

This guarantees the session is closed even if your endpoint raises an error — the `finally` runs regardless. This exact function is what Day 5's `repos.py` will use for every database-touching endpoint.

### Why `expire_on_commit=False`
By default, after `session.commit()`, SQLAlchemy marks all objects "expired" so the next access re-fetches from the database. That's often wasteful for a simple API that just wants to return the object it just created. Setting `expire_on_commit=False` lets you keep using an object's attributes right after commit without an extra query. (Day 5's `add_repo` endpoint does exactly this: commit, then read `repo.id`.)

### Resource
- SQLAlchemy docs, "Session Basics" — read just "What does the Session do?" (10 min).

---

## 3. Declarative models

### Base class
```python
class Base(DeclarativeBase):
    pass
```
Every model inherits from this. Its `.metadata` attribute accumulates a registry of every table defined — that's what `Base.metadata.tables` printed in the verification step (`repositories`, `repo_files`). Alembic's `env.py` reads this same metadata to know your target schema.

### Reading a column definition
```python
full_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
```
- `Mapped[str]` — the Python-side type (used for type checking and to infer NOT NULL by default).
- `mapped_column(String(255), ...)` — the SQL-side type and constraints.
- `unique=True` — a database-level uniqueness constraint (Day 5's "already added" 409 check relies on the app-level check, but this is the safety net at the DB layer).
- `index=True` — creates a database index, so lookups by `full_name` stay fast as the table grows.

### Nullable columns
```python
description: Mapped[str | None] = mapped_column(Text, nullable=True)
```
The `| None` in the type hint and `nullable=True` in the column must agree — SQLAlchemy 2.0 style ties them together so type checkers catch a mismatch.

### Server-side defaults
```python
created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```
`server_default=func.now()` means **Postgres itself** fills this in (via `NOW()`) when a row is inserted, not your Python code. This matters if multiple services ever insert rows directly, or if you insert via raw SQL — the timestamp is still correct.

### Relationships and cascades
```python
files: Mapped[list["RepoFile"]] = relationship(
    back_populates="repository", cascade="all, delete-orphan", passive_deletes=True
)
```
- `relationship(...)` isn't a real column — it's a Python-side convenience so `some_repo.files` gives you the list of related `RepoFile` objects without writing a join yourself.
- `back_populates="repository"` links this to the matching `relationship` on `RepoFile`, so both sides stay in sync in Python.
- `cascade="all, delete-orphan"` — if you delete a `Repository` object through SQLAlchemy, its `RepoFile` rows are deleted too.
- `passive_deletes=True` — tells SQLAlchemy "don't bother loading and deleting the children yourself, the database's `ON DELETE CASCADE` (in the foreign key) will handle it." This is faster: one DB-level cascade instead of SQLAlchemy issuing a DELETE per row.

### The foreign key itself
```python
repository_id: Mapped[int] = mapped_column(
    ForeignKey("repositories.id", ondelete="CASCADE"), index=True
)
```
`ondelete="CASCADE"` is the actual database-level rule that `passive_deletes` relies on: Postgres deletes matching `repo_files` rows automatically when their `repository` row is deleted.

### The `UniqueConstraint`
```python
__table_args__ = (UniqueConstraint("repository_id", "path", name="uq_repo_file_path"),)
```
A single-column `unique=True` (like on `full_name`) can't express "unique *combination* of two columns." `__table_args__` is where multi-column constraints and composite indexes go. This one ensures the same file path can't be stored twice for the same repository, but the same path *can* exist across different repositories.

### Resource
- SQLAlchemy docs, "Relationship Configuration" — skim just the "Cascades" section (10 min).

---

## 4. Migrations and Alembic

### The problem migrations solve
`models.py` describes what your schema *should* look like. But your actual Postgres database needs SQL commands (`CREATE TABLE`, `ALTER TABLE`, ...) to get there — and needs a *record* of which changes have already been applied, so the same commands aren't run twice, and so the schema can evolve safely over time as you add features.

### The pieces

| File | Job |
|------|-----|
| `alembic.ini` | Points Alembic at the `alembic/` folder; logging config |
| `alembic/env.py` | The script Alembic actually runs: connects to your DB, figures out the target schema, applies migrations |
| `alembic/script.py.mako` | A template — every new migration file is generated from this |
| `alembic/versions/0001_init.py` | Your first migration: an `upgrade()` and a `downgrade()` |

### Reading `env.py`
```python
import app.models  # noqa: F401  (registers tables on Base.metadata)
```
This import looks unused (hence the `# noqa: F401` telling ruff not to flag it), but it's essential: importing `app.models` is what causes `Repository` and `RepoFile` to register themselves on `Base.metadata`. Without this line, `target_metadata` would be empty and `alembic revision --autogenerate` would think no tables should exist.

```python
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
```
Rather than hardcoding a connection string in `alembic.ini`, we pull it from our own `Settings` — one source of truth. The `%` → `%%` replace is needed because Python's `configparser` (which Alembic uses under the hood) treats `%` as a special interpolation character.

```python
target_metadata = Base.metadata
```
This is what `--autogenerate` diffs your database against, to figure out what changed.

### Reading `0001_init.py`
```python
def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table("repositories", ...)
    op.create_index(...)
    op.create_table("repo_files", ...)
    op.create_index(...)

def downgrade() -> None:
    op.drop_table("repo_files")
    op.drop_table("repositories")
```
- `upgrade()` — what to run to move the schema *forward*.
- `downgrade()` — what to run to undo it (roll back). Note tables are dropped in **reverse** order of creation — `repo_files` first, since it has a foreign key pointing at `repositories`.
- `revision = "0001"` / `down_revision = None` — this is the *first* migration, so it has no parent. Every future migration will set `down_revision` to the ID of the one before it, forming a chain Alembic can walk in either direction.

**Why is `CREATE EXTENSION` inside a migration instead of only in `db/init.sql` from Day 1?** `init.sql` only runs once, when the Docker volume is first created — it won't run again on a database that already exists (e.g., a teammate's existing dev DB, or a staging environment created differently). Putting it in the migration means `alembic upgrade head` alone is enough to get a correct database from a blank Postgres, regardless of how it was provisioned. `IF NOT EXISTS` makes it safe to run even if `init.sql` already did it.

### The commands

| Command | What it does |
|---------|--------------|
| `alembic upgrade head` | Apply all migrations up to the latest ("head") |
| `alembic downgrade -1` | Undo the most recent migration |
| `alembic current` | Show which migration the database is currently at |
| `alembic history` | List all migrations in order |
| `alembic revision --autogenerate -m "message"` | Generate a new migration by diffing `models.py` against the live database (you'll use this from Day 5 onward when the schema changes) |

**Important habit:** always read an autogenerated migration before running it. Alembic is good but not perfect — it can miss some changes (like renaming a column, which it sees as "drop one, add another" and would lose data) and occasionally gets index/constraint naming wrong.

### Resource
- Alembic docs, "Tutorial" page — read up through "Running our First Migration" (15 min).

---

## 5. Wiring pgvector through SQLAlchemy

We haven't added a `vector` column yet (that's Week 2's `chunks` table), but it's worth previewing since the extension is already being installed today.

The Python side uses the `pgvector` package (added to `requirements.txt` today) alongside SQLAlchemy:
```python
from pgvector.sqlalchemy import Vector

class Chunk(Base):
    ...
    embedding: Mapped[list[float]] = mapped_column(Vector(384))  # dimension from the model you pick
```
`Vector(384)` maps to Postgres's `vector(384)` column type from Day 1's study guide — same concept, just declared from the Python/SQLAlchemy side instead of raw SQL. This is why `CREATE EXTENSION IF NOT EXISTS vector` has to run *before* any migration that creates a table with a `Vector(...)` column — the type doesn't exist in Postgres until the extension is installed.

### Resource
- pgvector-python README (github.com/pgvector/pgvector-python) — skim the SQLAlchemy section only (5 min). Nothing to run today; just recognize the pattern for Week 2.

---

## 6. Hands-on labs

Do these with `docker compose up -d db` running and your venv activated in `backend/`.

### Lab 1: Run the migration and inspect the result
```powershell
alembic upgrade head
docker compose exec db psql -U warden -d warden -c "\dt"
docker compose exec db psql -U warden -d warden -c "\d repositories"
docker compose exec db psql -U warden -d warden -c "\d repo_files"
```
Read the `\d` output for `repo_files` carefully — find the foreign key constraint and confirm it says `ON DELETE CASCADE`.

### Lab 2: Check Alembic's own bookkeeping
```powershell
docker compose exec db psql -U warden -d warden -c "SELECT * FROM alembic_version;"
alembic current
alembic history
```
Alembic creates this one-row table itself, to track which migration was last applied.

### Lab 3: Hit the new endpoint
With `uvicorn app.main:app --reload` running, open `/docs` and try `GET /health/db`. You should get:
```json
{"database": "ok", "pgvector": true}
```
If `pgvector` is `false`, the extension didn't get created — check the migration actually ran (Lab 1).

### Lab 4: Downgrade and re-upgrade
```powershell
alembic downgrade -1
docker compose exec db psql -U warden -d warden -c "\dt"
```
Tables should be gone (extension stays, since `downgrade()` doesn't drop it — that's intentional, dropping extensions is rarely what you want). Then:
```powershell
alembic upgrade head
```
Tables come back.

### Lab 5: Insert a row by hand, then query it through the ORM
```powershell
docker compose exec db psql -U warden -d warden -c "INSERT INTO repositories (full_name, owner, name, default_branch, html_url, status) VALUES ('octocat/Hello-World', 'octocat', 'Hello-World', 'master', 'https://github.com/octocat/Hello-World', 'pending');"
```
Then in a Python shell (venv active, inside `backend/`):
```python
python
>>> from app.db import SessionLocal
>>> from app.models import Repository
>>> db = SessionLocal()
>>> db.query(Repository).all()
>>> repo = db.query(Repository).first()
>>> repo.full_name, repo.status
>>> db.close()
>>> exit()
```
Then clean up:
```powershell
docker compose exec db psql -U warden -d warden -c "DELETE FROM repositories;"
```

### Lab 6: Break a model on purpose
Comment out the `index=True` on `full_name` in `models.py`. Nothing breaks yet — models.py alone doesn't touch the database. Try `alembic revision --autogenerate -m "test"` and look at the generated file in `alembic/versions/` — it should propose dropping the index. **Don't run `upgrade` on it.** Delete that generated file and uncomment `index=True`. This demonstrates the "diff `models.py` against the live DB" mechanism without actually changing anything.

### Lab 7: Confirm ruff still passes on the whole backend
```powershell
ruff check .
```
Should be clean — this is worth running after every day from now on, as a habit.

---

## 7. Self-check

Answer without looking. Answers are at the bottom.

1. What are the three layers between your Python code and the actual database rows?
2. What does `pool_pre_ping=True` protect against?
3. Walk through what happens, in order, when a request comes in to `GET /health/db`, using `get_db`.
4. Why does `get_db` use `try/finally` instead of just `db.close()` at the end?
5. What does `Mapped[str | None]` combined with `nullable=True` communicate, and why must they agree?
6. What is `server_default=func.now()` doing, and why is it different from setting a Python default?
7. What's the difference between `relationship(...)` and a real column like `repository_id`?
8. What does `passive_deletes=True` let the database do that SQLAlchemy would otherwise do itself?
9. Why is `UniqueConstraint` on `__table_args__` needed instead of just `unique=True` on one column?
10. What does `Base.metadata` contain, and what reads it?
11. Why is `import app.models` in `env.py` necessary even though nothing in `env.py` calls it directly?
12. Why is `CREATE EXTENSION IF NOT EXISTS vector` in the migration instead of relying only on Day 1's `init.sql`?
13. What does `alembic downgrade -1` do, and does it drop the `vector` extension?
14. What command would you use to generate a new migration after adding a column to `models.py`, and what should you always do before running it?

### Answers
1. Engine (connection pool) → Session (per-request workspace) → Connection (the raw link the Session borrows from the Engine's pool).
2. A stale/dropped pooled connection being handed to your code and failing with a confusing error — SQLAlchemy checks it's alive first and replaces it if not.
3. FastAPI calls `get_db()` → runs it up to `yield db`, creating a `Session` → passes that session into `health_db` as `db` → the endpoint runs its queries → after the endpoint returns, FastAPI resumes `get_db` past the `yield`, running `db.close()` in the `finally` block.
4. So the session is always closed even if the endpoint raises an exception — `finally` runs regardless of how the `try` block exits.
5. That the column can be `NULL` in the database and `None` in Python. They must agree because SQLAlchemy 2.0 infers nullability from the Python type hint, so a mismatch would be a bug.
6. Postgres itself fills in the current time on insert (via `NOW()`), rather than Python computing it — correct even for rows inserted outside your app, e.g. via raw SQL.
7. `repository_id` is a real database column (a foreign key). `relationship(...)` is a Python-only convenience that lets you access related objects (`repo.files`) without manually writing a join — it doesn't create a column.
8. Lets Postgres's own `ON DELETE CASCADE` (on the foreign key) delete child rows, instead of SQLAlchemy loading and deleting each child object itself — faster, one DB-level operation.
9. `unique=True` only enforces uniqueness on a single column. Preventing duplicate `(repository_id, path)` *combinations* needs a multi-column constraint, which goes in `__table_args__`.
10. A registry of every table defined by classes inheriting from `Base`. Alembic's `env.py` reads it as `target_metadata` to know the target schema (used especially by `--autogenerate`).
11. Importing the module is what causes `Repository` and `RepoFile` to register themselves onto `Base.metadata` as a side effect of being defined — without the import, `target_metadata` would be empty.
12. `init.sql` only runs once, on a brand-new Docker volume. Putting the extension creation in the migration (with `IF NOT EXISTS`) means `alembic upgrade head` alone gives a correct database regardless of how or where it was provisioned.
13. Runs the current migration's `downgrade()`, undoing the most recent migration (here: drops `repo_files` and `repositories`). It does not drop the `vector` extension — that's left in place intentionally.
14. `alembic revision --autogenerate -m "message"`. Always read the generated migration file before running `upgrade`, since autogenerate can miss things (like column renames) or get details wrong.

---

## You are ready for Day 4 if you can

- [ ] Explain the Engine → Session → Connection chain and what `get_db` does with it
- [ ] Read any column definition in `models.py` and explain every argument
- [ ] Explain cascade delete, both the SQLAlchemy side (`cascade=`, `passive_deletes`) and the DB side (`ondelete=`)
- [ ] Explain what `alembic upgrade head` actually does, step by step
- [ ] Explain why `import app.models` matters in `env.py`
- [ ] Run `alembic downgrade -1` and `alembic upgrade head` and predict what changes in the database each time
