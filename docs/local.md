# Local Deployment

The local stack uses released images, not source checkouts. That keeps this repository aligned with its purpose: deploy what was published.

## Prerequisites

- Docker Engine with the Compose plugin
- access to pull `ghcr.io/obsura/obsura-api`
- copied env files:
  - `env/global.env`
  - `env/api.env`
  - `env/postgres.env`

## Recommended Workflow

1. Copy the example env files.
2. Set `OBSURA_API_IMAGE` in `env/global.env` to a real release tag.
3. Set a strong `POSTGRES_PASSWORD` in `env/postgres.env`.
4. Start the stack:

   ```bash
   ./scripts/deploy.sh local
   ```

   ```powershell
   ./scripts/deploy.ps1 -Environment local
   ```

## Manual Compose Command

```bash
docker compose \
  --env-file env/global.env \
  --env-file env/postgres.env \
  --env-file env/api.env \
  -f compose/local/docker-compose.yaml \
  up -d
```

## What The Local Stack Does

- starts PostgreSQL without publishing it to the host
- initializes the Obsura data volume so the non-root API container can write to it
- runs `obsura-api` with PostgreSQL instead of development SQLite
- publishes the API only on the bind address and host port from `env/global.env`

## Verification

- `docker compose --env-file env/global.env --env-file env/postgres.env --env-file env/api.env -f compose/local/docker-compose.yaml ps`
- `curl http://127.0.0.1:8000/api/v1/health` if you kept the default host port
- `docker compose --env-file env/global.env --env-file env/postgres.env --env-file env/api.env -f compose/local/docker-compose.yaml logs -f api`

If the API fails to start, check:

- `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` alignment
- whether `OBSURA_API_IMAGE` points to a real published image
- whether the data volume was initialized successfully by `volume-init`
