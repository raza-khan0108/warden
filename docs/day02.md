# Warden: Day 2 Study Guide

**Topic:** FastAPI skeleton (routers, dependency injection, settings, testing)
**Time:** about 3 hours (1.5 hrs reading, 1.5 hrs hands-on)
**Goal:** understand every line of `main.py`, `config.py`, `api/health.py`, and the test setup — and know why they're structured this way, not just that they work.

---

## Study plan

| Block | Topic | Time |
|-------|-------|------|
| 1 | ASGI, Uvicorn, and what "running a server" means | 20 min |
| 2 | FastAPI core: app, routers, path operations | 40 min |
| 3 | Pydantic and pydantic-settings | 35 min |
| 4 | CORS | 15 min |
| 5 | Testing with TestClient and fixtures | 30 min |
| 6 | Packaging: venv, requirements, ruff | 15 min |
| 7 | Hands-on labs | 35 min |
| 8 | Self-check | 15 min |

---

## 1. ASGI, Uvicorn, and "running a server"

### The pieces
- **FastAPI** is a framework: you write Python functions, it turns them into a web API.
- **ASGI** (Asynchronous Server Gateway Interface) is the standard contract between a Python web framework and a server — it's what lets FastAPI be `async`.
- **Uvicorn** is the actual server that listens on a port and speaks HTTP, calling into your FastAPI app for each request.

So `app = FastAPI(...)` builds the application object, and `uvicorn app.main:app` is "start a server, and for `app.main`, use the object named `app`."

### What `--reload` does
Watches your files and restarts the server on every save. Great for development, never used in production (that's why the Dockerfile's `CMD` also has `--reload` for now, but a real deployment would drop it).

### Reading your terminal output
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Started reloader process [7316] using WatchFiles
INFO:     Started server process [6480]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```
Two processes: one watches files (reloader), one actually serves (server). "Application startup complete" means FastAPI ran its startup hooks (none yet) and is ready.

```
127.0.0.1:56190 - "GET / HTTP/1.1" 404 Not Found
```
This is an **access log line**: client address, the request line, and the status code. A 404 here is correct — you only defined `/health`, so `/` has no handler.

### Resource
- Uvicorn docs, "Settings" page (skim, 5 min) — just to see what `--reload`, `--host`, `--port` control.

---

## 2. FastAPI core

### The app object
```python
app = FastAPI(title=settings.app_name, version="0.1.0")
```
This is your whole application. `title` and `version` show up in the auto-generated docs at `/docs`.

### Path operations
A "path operation" is a function decorated to handle a specific HTTP method and path:
```python
@router.get("")
def health() -> dict:
    return {"status": "ok"}
```
- `@router.get("")` — respond to `GET` requests.
- The return value is automatically converted to JSON.
- The `-> dict` type hint isn't just documentation — FastAPI uses it (and Pydantic models, later) to generate the OpenAPI schema that powers `/docs`.

### Routers
```python
router = APIRouter(prefix="/health", tags=["health"])
```
A router is a mini FastAPI app: a group of related endpoints. `prefix="/health"` means every path inside this file is relative to `/health`, so `@router.get("")` becomes `GET /health`.

```python
app.include_router(health.router)
```
This is how `main.py` "mounts" the router onto the real app. This is the exact pattern Day 5 will repeat for `repos.py` — that's why we're setting it up now even with just one trivial endpoint.

**Why split into routers instead of one big file?** As Warden grows (`/repos`, `/repos/{id}/files`, later `/chat`, `/prs`), one file would get unmanageable. Each router owns one resource.

### Automatic docs
Visit `/docs` (Swagger UI, interactive) and `/redoc` (read-only, cleaner for sharing). Both are generated from your code — you never write them by hand. This is one of FastAPI's biggest selling points.

### `async def` vs `def`
FastAPI supports both. Use `async def` when the function does I/O with an async library (like the `httpx.AsyncClient` we'll likely use for GitHub calls later). Plain `def` is fine for anything else — FastAPI runs it in a thread pool automatically. Don't stress over this yet; Day 4 will make it concrete.

### Resource
- FastAPI docs, "First Steps" and "Path Parameters" pages (official tutorial, docs are excellent — 20 min).

---

## 3. Pydantic and pydantic-settings

### Pydantic in one sentence
A library that validates data against a schema using Python type hints, and raises a clear error if the data doesn't match.

### Why FastAPI is built on it
Every request body, query parameter, and response can be described as a Pydantic model. FastAPI validates automatically — if a client sends bad data, they get a 422 error with details, and you never write that validation code yourself. You'll see this properly on Day 5 with `schemas.py`.

### pydantic-settings: config from the environment
```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    app_name: str = "Warden"
    cors_origins: list[str] = ["http://localhost:3000"]

settings = Settings()
```

What happens when this runs:
1. Pydantic looks for each field as an environment variable (case-insensitive): `APP_NAME`, `CORS_ORIGINS`.
2. If not found in the environment, it checks the `.env` file(s) listed.
3. If not found there either, it uses the Python default.

**Why two paths in `env_file`?** `(".env", "../.env")` — when you run `uvicorn` from inside `backend/`, `.env` (if it existed) would be found via the first path. When pytest or a tool runs from the repo root, `../.env` covers that. Right now no `.env` is required at all, since every field has a default — that's intentional for Day 2, so the skeleton runs with zero configuration. Day 3 will add fields (like `database_url`) that come from your real `.env`.

**Why `extra="ignore"`?** Without it, pydantic-settings errors if your `.env` has variables the `Settings` class doesn't declare. Your Day 1 `.env` already has `POSTGRES_USER`, `DATABASE_URL`, `GITHUB_TOKEN` — none of which `Settings` knows about yet. `ignore` means "don't complain, just skip what you don't recognize."

### `settings = Settings()` at import time
This line runs once, when the module is first imported, and creates a single shared object. Every file that does `from app.config import settings` gets the *same* instance. This is a simple, common pattern for app-wide config (you'll see it used the same way for the database engine in Day 3).

### Resource
- pydantic-settings docs, "Usage" page, just the first section on loading from `.env` (10 min).

---

## 4. CORS

### The problem it solves
Browsers block a page on one origin (say `localhost:3000`) from calling an API on a different origin (`localhost:8000`) unless the API explicitly allows it. This is CORS: Cross-Origin Resource Sharing. It's a browser security feature — tools like `curl`, Postman, or `httpx` never hit this restriction, only browser JavaScript does.

### The fix
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
This tells the browser, via response headers, "requests from `http://localhost:3000` are allowed, with any HTTP method and any headers." Without this, Day 6's Next.js frontend would get its `fetch()` calls silently blocked by the browser, even though the backend itself works fine (you'd see it in the browser console, not in FastAPI's logs — a classic confusing bug).

### What "middleware" means
Code that runs on every request/response, wrapping your actual endpoint logic. CORS is a good first example: it doesn't touch your route functions at all, it just adds headers to every response.

### Resource
- MDN, "Cross-Origin Resource Sharing (CORS)" — just read the "Overview" section (10 min).

---

## 5. Testing with TestClient and fixtures

### `TestClient`
```python
from fastapi.testclient import TestClient
from app.main import app

with TestClient(app) as c:
    ...
```
`TestClient` lets you call your FastAPI app directly in Python, no running server needed. It sends real HTTP-shaped requests internally and gives you back a response object, just like `requests` or `httpx` would against a live server.

### pytest fixtures
```python
@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
```
A fixture is a reusable piece of setup. Any test function that names `client` as a parameter automatically receives whatever this fixture produces:
```python
def test_health(client):
    res = client.get("/health")
    ...
```
pytest sees the parameter name `client`, matches it to the fixture with the same name, runs the fixture first, and passes its `yield`ed value in. The `with` block means cleanup (anything after `yield`, though there's none here) runs automatically after the test finishes.

**Why put it in `conftest.py` instead of the test file?** `conftest.py` is special to pytest — fixtures defined there are automatically available to every test file in the same folder (and subfolders), with no import needed. This is why Day 5's `test_repos.py` can also just ask for `client` without importing anything from `conftest.py`.

### Why test through `TestClient` instead of starting `uvicorn` and testing over real HTTP?
Faster (no real sockets, no network), and reliable in CI (no port conflicts, nothing to start/stop).

### Resource
- FastAPI docs, "Testing" page (15 min) — shows this exact pattern.

---

## 6. Packaging: venv, requirements, ruff

### Virtual environments
A venv is an isolated Python install for one project, so its dependencies don't clash with other projects or your system Python.
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```
Once activated, `pip install` and `python` inside that terminal only affect `.venv`. Your prompt shows `(.venv)` as confirmation — as it did in your last screenshot.

### `requirements.txt`
A plain list of packages to install:
```
fastapi>=0.115
uvicorn[standard]>=0.30
```
`uvicorn[standard]` means "install uvicorn plus its optional extras" (faster event loop, WebSocket support, etc.) — the `[standard]` is called an *extra*.

`>=` pins a minimum version but allows newer ones. Fine for a learning project; larger teams often pin exact versions (`==`) for reproducibility and use a lockfile.

### `pyproject.toml` — ruff and pytest config
```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B"]
ignore = ["B008"]
```
- **ruff** is a linter (and formatter) — it checks your code for style issues and likely bugs, much faster than older tools like flake8.
- `select` chooses rule groups: `E` (pycodestyle errors), `F` (pyflakes — unused imports, undefined names), `I` (import sorting), `B` (bugbear — likely-bug patterns).
- `ignore = ["B008"]` turns off one specific bugbear rule that flags function calls in default arguments — normally a real gotcha in Python, but FastAPI's `Depends(...)` pattern (used from Day 5 onward) relies on exactly that, so we silence it here.

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```
Tells pytest where to look for tests, and adds the current directory to Python's import path so `from app.main import app` resolves correctly when running `pytest` from `backend/`.

### Resource
- ruff docs, "Rules" page — skim the rule code prefixes (E, F, I, B) just to recognize them (5 min).

---

## 7. Hands-on labs

Do these with your server running (`uvicorn app.main:app --reload` in one terminal) and a second terminal free.

### Lab 1: Break something on purpose
In `api/health.py`, temporarily rename the function's return to `return {"status": "ok", "version": 1}`. Save. Watch the reloader restart in your first terminal. Hit `/health` again in `/docs` and see the new field. Revert it.

### Lab 2: Add a second endpoint
Add this to `api/health.py`:
```python
@router.get("/ping")
def ping() -> dict:
    return {"pong": True}
```
Restart isn't needed (reload does it). Confirm `GET /health/ping` works in `/docs`, and notice how `prefix="/health"` applied automatically.

### Lab 3: See validation in action
In `/docs`, try `GET /health/ping` — it takes no parameters, so nothing to break. Instead, open `http://127.0.0.1:8000/openapi.json` in your browser and skim the generated schema. This raw JSON is what powers both `/docs` and `/redoc` — nobody writes it by hand.

### Lab 4: Prove settings defaults work
In a Python shell (venv activated, inside `backend/`):
```python
python
>>> from app.config import settings
>>> settings.app_name
>>> settings.cors_origins
>>> exit()
```
Then set an env var and see it override the default:
```powershell
$env:APP_NAME="TestName"
python -c "from app.config import settings; print(settings.app_name)"
Remove-Item Env:APP_NAME
```

### Lab 5: Run tests two ways
```powershell
pytest
pytest -v
```
`-v` shows each test name instead of just dots. Then break the test on purpose (change the expected JSON in `test_health.py`), run `pytest`, read the failure output carefully, then fix it.

### Lab 6: Lint on purpose-broken code
Add an unused import to the top of `main.py`, e.g. `import os`. Run `ruff check .` and read the error (it should flag `F401 unused import`). Remove it, or run `ruff check . --fix` to auto-fix it.

### Lab 7: Confirm CORS is there
```powershell
curl.exe -I http://127.0.0.1:8000/health -H "Origin: http://localhost:3000"
```
Look for an `access-control-allow-origin` header in the response.

---

## 8. Self-check

Answer without looking. Answers are at the bottom.

1. What's the relationship between Uvicorn and FastAPI?
2. What does `--reload` do, and why should it never be used in production?
3. What does `router = APIRouter(prefix="/health")` combined with `@router.get("")` produce as the final path?
4. Why split endpoints into routers instead of one file?
5. Where do `/docs` and `/redoc` come from?
6. In `Settings`, what order does pydantic-settings check for a value: environment variable, `.env` file, or Python default — and which wins?
7. What does `extra="ignore"` do, and why did we need it given our Day 1 `.env`?
8. What problem does CORS middleware solve, and who enforces it — the browser or the server?
9. What does `TestClient` let you skip that a real HTTP test would need?
10. How does pytest know to hand the `client` fixture to `test_health`?
11. Why does `conftest.py` not need to be imported in test files?
12. What is a venv for?
13. What do the ruff rule codes `E`, `F`, `I`, and `B` roughly mean?
14. Why is `B008` ignored in this project?

### Answers
1. FastAPI is the framework that defines your app and endpoints; Uvicorn is the ASGI server that actually accepts HTTP connections and calls into FastAPI for each request.
2. It restarts the server automatically when files change. It adds overhead and is meant for development convenience, not stability or performance in production.
3. `GET /health` — the router's prefix plus the empty path in the decorator.
4. So each resource (health, repos, files, etc.) has its own file, keeping the app manageable as it grows.
5. FastAPI auto-generates them from your route definitions and type hints/Pydantic models — you never write them by hand.
6. Checked in this order: environment variable first, then `.env` file, then the Python default. Environment variables win if set.
7. It tells pydantic-settings to silently skip unrecognized keys in `.env` instead of raising an error. Needed because our `.env` already has `POSTGRES_USER`, `DATABASE_URL`, `GITHUB_TOKEN`, which `Settings` doesn't declare yet.
8. It solves the browser blocking JavaScript from calling a different-origin API. It's enforced by the browser, not the server — non-browser tools like curl aren't affected.
9. A real running server and network calls — `TestClient` calls the app directly in-process, which is faster and avoids port/networking issues.
10. pytest matches the fixture by name: a fixture function named `client` in scope satisfies any test parameter also named `client`.
11. pytest automatically discovers `conftest.py` files and makes their fixtures available to every test in that folder and its subfolders, with no import needed.
12. It isolates a project's installed packages from the system Python and other projects, avoiding version conflicts.
13. `E` = pycodestyle style errors, `F` = pyflakes (unused imports, undefined names, etc.), `I` = import sorting, `B` = bugbear (likely-bug patterns).
14. Because FastAPI's `Depends(...)` pattern (used starting Day 5) relies on a function call as a default argument, which bugbear's B008 rule normally flags as a mistake.

---

## You are ready for Day 3 if you can

- [ ] Explain what happens between running `uvicorn app.main:app --reload` and a browser showing `{"status": "ok"}`
- [ ] Explain why routers exist and how `include_router` wires one in
- [ ] Explain how `Settings()` resolves a value, and what `extra="ignore"` does
- [ ] Explain CORS in one sentence and who enforces it
- [ ] Explain how the `client` fixture reaches `test_health` with no import
- [ ] Read a `ruff check` failure and fix it
