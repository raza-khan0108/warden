# Docker Compose Setup

This document describes the local development environment setup using Docker Compose.

## Prerequisites

- Docker Desktop (or Docker + Docker Compose)
- Git

## Services

The `docker-compose.yml` defines three core services for V1:

### 1. PostgreSQL with pgvector (Port 5432)

- **Image**: `pgvector/pgvector:pg16`
- **Purpose**: Main database with vector extension for embeddings
- **Initialization**: Runs `db/init.sql` on first start (creates vector extension)
- **Volumes**: `pgdata` (persistent)
- **Healthcheck**: Enabled — waits for DB to be ready before other services

### 2. Redis (Port 6379)

- **Image**: `redis:7-alpine`
- **Purpose**: Message queue for Celery, caching
- **Volumes**: In-memory (ephemeral)
- **Healthcheck**: Enabled — verifies Redis is responding to PING

### 3. MinIO (Ports 9000, 9001)

- **Image**: `minio/minio:latest`
- **Purpose**: S3-compatible object storage (for code chunks, embeddings exports)
- **Console**: Available at `http://localhost:9001` (browser UI)
- **Volumes**: `miniodata` (persistent)
- **Healthcheck**: Enabled — checks health endpoint

## Quick Start

### 1. Create `.env` from the example

```bash
cp .env.example .env
```

Update the file with your GitHub token and any other secrets if needed. For local development, defaults should work fine.

### 2. Start all services

```bash
docker-compose up -d
```

This starts all three services in the background. The `-d` flag detaches from the console.

### 3. Verify services are running

```bash
docker-compose ps
```

You should see all three services with status `Up` and no warnings in the health column.

### 4. Check logs

```bash
# View logs for all services
docker-compose logs

# Follow logs in real-time
docker-compose logs -f

# View logs for a specific service
docker-compose logs db
docker-compose logs redis
docker-compose logs minio
```

## Connecting to Services

### PostgreSQL

From host machine (for debugging):
```bash
psql -U warden -d warden -h localhost
```

Connection string for apps:
```
postgresql+psycopg://warden:warden@db:5432/warden
```

### Redis

Using `redis-cli`:
```bash
redis-cli -h localhost
```

Connection string for apps:
```
redis://redis:6379
```

### MinIO

Browser console: `http://localhost:9001`
- Username: `minioadmin`
- Password: `minioadmin`

S3 endpoint for apps:
```
http://minio:9000
```

## Stopping Services

```bash
# Stop all services (containers remain)
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop, remove containers AND delete volumes (WARNING: data loss)
docker-compose down -v
```

## Database Migrations

Alembic migrations should run from the root directory:

```bash
# From project root, after db service is running
alembic upgrade head
```

The alembic/env.py is configured to find models from `apps/api/app/models.py`.

## Troubleshooting

### "Cannot connect to Docker daemon"

Ensure Docker Desktop is running, or Docker daemon is started on Linux.

### PostgreSQL won't start: "pgdata" permission denied

On Linux, you may need to ensure proper permissions:
```bash
sudo chown -R 999:999 pgdata
```

### MinIO console won't load

MinIO console is on port 9001. If blocked, check firewall or try:
```bash
docker-compose logs minio
```

### Database not initialized with vector extension

Check if `db/init.sql` exists and the `pgdata` volume was properly created:
```bash
docker-compose down -v  # Remove old data
docker-compose up -d db # Restart fresh
docker-compose logs db  # Check initialization
```

## Environment Variables

All services pull configuration from `.env` file. Key variables:

- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` — DB credentials
- `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` — MinIO credentials
- `DATABASE_URL` — Full PostgreSQL connection string for apps
- `REDIS_URL` — Redis connection for Celery
- `MINIO_ENDPOINT` — MinIO S3 endpoint
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` — Celery configuration

For production, store secrets securely (e.g., Docker secrets, environment management).

## Next Steps

Once services are running and healthy:

1. Run Alembic migrations: `alembic upgrade head`
2. Start the FastAPI backend: `cd apps/api && python -m uvicorn app.main:app --reload`
3. Start the Next.js frontend: `cd apps/web && npm install && npm run dev`
4. Start Celery workers: `cd apps/worker && celery -A worker.tasks worker --loglevel=info`
