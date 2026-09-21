# Warden

AI software engineering command center: index GitHub repos, chat over code, review PRs.

## Quick start

```bash
cp .env.example .env
docker compose up -d db
docker compose ps        # db should be "healthy"
```

Check pgvector is installed:

```bash
docker compose exec db psql -U warden -d warden -c "SELECT extname, extversion FROM pg_extension;"
```

You should see a `vector` row.

## Common commands

| Task | Command |
|------|---------|
| Start DB | `docker compose up -d db` |
| Stop DB | `docker compose down` |
| Open psql | `docker compose exec db psql -U warden -d warden` |
| View logs | `docker compose logs -f db` |
| Wipe all data | `docker compose down -v` |

## Docs

- [Architecture](docs/architecture.md)

## License

Apache 2.0
