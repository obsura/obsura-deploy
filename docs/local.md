# Local Deployment

The local stack uses released container images. That keeps testing and operator workflows aligned with what will run in production.

`obsuractl`, the helper scripts, and direct Compose commands all operate on the same local stack definition. The CLI is optional.

If you are using a standalone `obsuractl` binary, run it from inside the `obsura-deploy` checkout or pass `--repo-root /path/to/obsura-deploy`.

The local stack uses fixed container names such as `obsura-local-api`. That makes `docker ps` and log inspection simpler, but it also means you should not run duplicate copies of the local stack on the same host.

## Prerequisites

- Docker Engine
- Docker Compose v2 plugin
- access to pull `ghcr.io/obsura/obsura-api`
- either:
  - `obsuractl` available for the quickstart path
  - or a plan to copy `env/*.env.example` into `env/*.env` manually

## Environment Setup

Fastest local bootstrap:

```bash
obsuractl init --quickstart-local --image ghcr.io/obsura/obsura-api:<published-tag-or-digest>
```

That command:

- creates the local `env/*.env` files
- writes the local api image into `compose/local/docker-compose.yaml`
- generates a strong `POSTGRES_PASSWORD`
- keeps the default localhost-only API binding

If you prefer a guided prompt, run plain `obsuractl init` from an interactive terminal and accept the local quickstart prompt.

Template-only bootstrap with `obsuractl`:

```bash
obsuractl init --template-only
```

Manual equivalent:

```bash
cp env/global.env.example env/global.env
cp env/api.env.example env/api.env
cp env/postgres.env.example env/postgres.env
```

Set at minimum:

- the `api` and `volume-init` image lines in `compose/local/docker-compose.yaml`
- `POSTGRES_PASSWORD` in `env/postgres.env`

Keep the default bind address unless you have a specific reason not to:

```text
OBSURA_API_BIND_ADDRESS=127.0.0.1
```

## Start

Recommended:

```bash
obsuractl up local
```

`obsuractl up local` waits for the API container healthcheck before returning success.

Optional standalone preflight:

```bash
obsuractl doctor local
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

`obsuractl status local` also prints the running API image reference and image id when the container exists.

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
- Missing `env/*.env` files: run `obsuractl init --quickstart-local --image ghcr.io/obsura/obsura-api:<published-tag-or-digest>` for the fastest path, or run `obsuractl init` for template-only setup.
- Placeholder image reference: replace the local compose-file image with a real published tag.
- Placeholder password: replace `POSTGRES_PASSWORD` before starting.
- Storage permission failure: inspect `volume-init` logs and confirm the published image still exposes the expected runtime user.
- Compose interpolation failure: ensure all three env files were passed to `docker compose`.
