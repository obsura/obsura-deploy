# Production Deployment

The production stack is a single-host Docker Compose deployment intended to sit behind a reverse proxy such as Caddy or Nginx.

## Production Expectations

- `obsura-api` stays bound to localhost by default
- PostgreSQL is internal only and is not published to the host
- the public edge is a reverse proxy handling TLS and external exposure
- persistent data lives in named Docker volumes
- image references should be pinned to immutable digests when available

## Prepare Environment Files

Create these files from the examples:

- `env/global.env`
- `env/api.env`
- `env/postgres.env`

Set at minimum:

- `OBSURA_API_IMAGE`
- `POSTGRES_PASSWORD`
- optional volume names if you want host-specific naming
- `OBSURA_API_HOST_PORT` if the proxy should target a port other than `8000`

## Image Reference Guidance

Preferred production form:

```text
OBSURA_API_IMAGE=ghcr.io/obsura/obsura-api@sha256:<published-digest>
```

Readable but less strict form:

```text
OBSURA_API_IMAGE=ghcr.io/obsura/obsura-api:<release-tag>
```

Use tags during evaluation if needed, but promote a tested digest into production once you know the exact image you want to keep.

## Deploy

```bash
./scripts/deploy.sh production
```

```powershell
./scripts/deploy.ps1 -Environment production
```

Equivalent manual command:

```bash
docker compose \
  --env-file env/global.env \
  --env-file env/postgres.env \
  --env-file env/api.env \
  -f compose/production/docker-compose.yaml \
  up -d
```

## Startup Order

1. `volume-init` prepares the application data volume permissions.
2. `postgres` starts and must pass its healthcheck.
3. `api` starts only after storage initialization and PostgreSQL health succeed.

## Reverse Proxy Expectation

Keep the API bound to `127.0.0.1`. Point Caddy or Nginx to:

```text
http://127.0.0.1:8000
```

`8000` is the default host port from `env/global.env`. If you change `OBSURA_API_HOST_PORT`, update the proxy target to match.

Example configs live in:

- `proxy/caddy/Caddyfile.example`
- `proxy/nginx/nginx.conf.example`

## Verification After Deploy

- `docker compose --env-file env/global.env --env-file env/postgres.env --env-file env/api.env -f compose/production/docker-compose.yaml ps`
- `curl http://127.0.0.1:8000/api/v1/health` if you kept the default host port
- verify the proxy can reach the local API target
- inspect recent logs if healthchecks do not pass

## Notes

This repository cannot guarantee that every future image will preserve the same runtime UID, writable paths, or schema behavior. When the published image contract changes, update this repository and validate the deployment flow before rolling forward.
