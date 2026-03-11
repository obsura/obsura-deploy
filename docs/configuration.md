# Configuration

Configuration is intentionally split by concern.

## Env File Layout

- `env/global.env`
  Shared Compose interpolation values such as image references, bind address, published port, volume names, and backup root.
- `env/api.env`
  Non-secret application runtime settings passed to the `obsura-api` container.
- `env/postgres.env`
  PostgreSQL database name, user, password, and init arguments.

## Interpolation Expectations

The compose files build `DATABASE_URL` from values stored in `env/postgres.env`. That means manual Compose commands must pass all three env files:

```bash
docker compose \
  --env-file env/global.env \
  --env-file env/postgres.env \
  --env-file env/api.env \
  -f compose/production/docker-compose.yaml \
  config
```

If you pass only one env file, Compose interpolation can fail even though the container-level `env_file` entries look correct.

## App Settings vs Database Settings

Application settings belong in `env/api.env`. Database settings belong in `env/postgres.env`. Shared deployment and Compose settings belong in `env/global.env`.

Current important wiring:

- `OBSURA_ENV` is set by the compose file, not by `env/api.env`
- `OBSURA_STORAGE_ROOT` is set by the compose file to `/var/lib/obsura`
- `DATABASE_URL` is assembled by the compose file from PostgreSQL env values

## Secrets Placement

- Keep real `env/*.env` files out of version control.
- Put real database credentials in `env/postgres.env`.
- Treat backup artifacts as sensitive because they contain live data.
- If you have a stronger secret distribution process, adapt this repository around it rather than committing secrets here.

## Practical Rules

- Keep env files in plain `KEY=value` form.
- Replace every placeholder before production use.
- Prefer image digests over tags in production.
- Change volume names only if the host needs naming isolation.
