# Production Deployment

The production stack is a single-host Docker Compose deployment intended to run behind a reverse proxy such as Caddy or Nginx.

`obsuractl` is an operator convenience layer for this model, not a separate platform. Direct Compose and helper-script workflows remain supported.

## Production Assumptions

- `obsura-api` binds to localhost only by default
- PostgreSQL stays internal to the Compose network
- TLS termination happens at the reverse proxy
- persistent data is stored in named Docker volumes
- operators pin tested images, preferably by digest

This repository does not claim to be a full hardening solution. It provides a production-minded baseline.

## Prepare Env Files

Create:

- `env/global.env`
- `env/api.env`
- `env/postgres.env`

Required production edits:

- set `OBSURA_API_IMAGE` to the exact image you intend to deploy
- replace `POSTGRES_PASSWORD`
- keep `OBSURA_API_BIND_ADDRESS=127.0.0.1` unless you deliberately want host-wide exposure

## Image References

Preferred:

```text
OBSURA_API_IMAGE=ghcr.io/obsura/obsura-api@sha256:<published-digest>
```

Acceptable for evaluation but weaker:

```text
OBSURA_API_IMAGE=ghcr.io/obsura/obsura-api:<release-tag>
```

Do not do blind production updates against mutable tags if you care about reproducibility.

## Deploy

Recommended:

```bash
obsuractl doctor production
obsuractl up production
```

`obsuractl up production` waits for the API container healthcheck before it reports success.

Helper script:

```bash
bash scripts/deploy.sh production
```

Manual Compose:

```bash
docker compose \
  --env-file env/global.env \
  --env-file env/postgres.env \
  --env-file env/api.env \
  -f compose/production/docker-compose.yaml \
  up -d
```

## Why Localhost Binding Is Used

The API is published to the host on `127.0.0.1:<port>` by default so the reverse proxy is the only Internet-facing component. That makes TLS policy, headers, logging, and future rate-limiting an explicit edge concern instead of an accidental property of the application container.

## Reverse Proxy Expectation

Both example proxy configs assume the API target is:

```text
http://127.0.0.1:8000
```

If you change `OBSURA_API_HOST_PORT`, update the proxy target to match.

Example configs:

- `proxy/caddy/Caddyfile.example`
- `proxy/nginx/nginx.conf.example`

## Verification

- `obsuractl status production`
- `curl http://127.0.0.1:8000/api/v1/health`
- verify proxy reachability through the public hostname
- inspect recent container logs

`obsuractl status production` also prints the running API image reference and image id when the container exists. Use that output to confirm the image you meant to deploy is the image that is actually running.

## Operational Caveats

- If the image runtime user changes, update the `volume-init` logic before rollout.
- If the release changes schema or storage behavior, treat the upgrade as data-affecting.
- If you change `POSTGRES_PASSWORD` in `env/postgres.env`, make sure the running PostgreSQL instance is updated through your database administration process. The env file alone does not rotate the live password.
- Compose is a solid single-host choice here, but it is not a replacement for host hardening, patching, monitoring, or off-host backups.
