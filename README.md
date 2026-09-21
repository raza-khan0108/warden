warden/
├── .github/workflows/ci.yml
├── backend/
│   ├── alembic/ (env.py, versions/0001_init.py)
│   ├── app/
│   │   ├── main.py, config.py, db.py, models.py, schemas.py
│   │   ├── api/ (health.py, repos.py, deps.py)
│   │   └── services/ (github.py, files.py)
│   ├── tests/
│   ├── Dockerfile, requirements.txt, pyproject.toml
├── frontend/ (Next.js: app/page.tsx, lib/api.ts)
├── docs/architecture.md
├── docker-compose.yml, .env.example, README.md
