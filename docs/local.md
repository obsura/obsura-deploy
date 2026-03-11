# Local Deployment

The local stack uses released container images. That keeps testing and operator workflows aligned with what will run in production.

`obsuractl`, the helper scripts, and direct Compose commands all operate on the same local stack definition. The CLI is optional.

If you are using a standalone `obsuractl` binary, run it from inside the `obsura-deploy` checkout or pass `--repo-root /path/to/obsura-deploy`.

## Prerequisites

- Docker Engine
- Docker Compose v2 plugin
- access to pull `ghcr.io/obsura/obsura-api`
- copied env files:
  - `env/global.env`
  - `env/api.env`
  - `env/postgres.env`

## Environment Setup

Copy the example env files first:

Recommended with `obsuractl`:

```bash
obsuractl init
```

Manual equivalent:

```bash
cp env/global.env.example env/global.env
cp env/api.env.example env/api.env
cp env/postgres.env.example env/postgres.env
```

Set at minimum:

- `OBSURA_API_IMAGE` in `env/global.env`
- `POSTGRES_PASSWORD` in `env/postgres.env`

Keep the default bind address unless you have a specific reason not to:

```text
OBSURA_API_BIND_ADDRESS=127.0.0.1
```

## Start

Recommended:

```bash
obsuractl doctor local
obsuractl up local
```

Manual helper scripts:

```bash
bash scripts/deploy.sh local
```

```powershell
./scripts/deploy.ps1 -Environment local
```

Manual Compose:

```bash
docker compose \
  --env-file env/global.env \
  --env-file env/postgres.env \
  --env-file env/api.env \
  -f compose/local/docker-compose.yaml \
  up -d
```

## Verify

- `curl http://127.0.0.1:8000/api/v1/health`
- `obsuractl status local`
- `obsuractl logs local api --follow`

If you changed `OBSURA_API_HOST_PORT`, use that port instead of `8000`.

## Stop

```bash
obsuractl down local
```

Equivalent manual command:

```bash
docker compose \
  --env-file env/global.env \
  --env-file env/postgres.env \
  --env-file env/api.env \
  -f compose/local/docker-compose.yaml \
  down --remove-orphans
```

## Common Local Issues

- Port conflict on `127.0.0.1:8000`: change `OBSURA_API_HOST_PORT` or stop the other process.
- Missing `env/*.env` files: run `obsuractl init` from the checkout, then edit `env/global.env` and `env/postgres.env`.
- Placeholder image reference: replace `OBSURA_API_IMAGE` with a real published tag.
- Placeholder password: replace `POSTGRES_PASSWORD` before starting.
- Storage permission failure: inspect `volume-init` logs and confirm the published image still exposes the expected runtime user.
- Compose interpolation failure: ensure all three env files were passed to `docker compose`.
