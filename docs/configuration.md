# Configuration

Configuration is split between compose interpolation values, application runtime values, and PostgreSQL runtime values.

## Files

- `env/global.env`
  Shared Compose interpolation values such as image references, bind address, published port, volume names, and backup root.
- `env/api.env`
  Non-secret application settings passed directly to the `obsura-api` container.
- `env/postgres.env`
  PostgreSQL database name, user, password, and init arguments.

## How Values Flow

- The helper scripts pass `env/global.env`, `env/postgres.env`, and `env/api.env` to `docker compose`.
- The compose files use interpolation from the env files for image names, volume names, and the API `DATABASE_URL`.
- The `api` service also loads `env/api.env` as container environment.
- The `postgres` service loads `env/postgres.env` as container environment.

## Important Wiring Detail

`DATABASE_URL` is assembled in the compose files from `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD`. Keep those values correct in `env/postgres.env`.

Example:

```text
DATABASE_URL=postgresql+psycopg://obsura:<password>@postgres:5432/obsura
```

## Override Rules

- Compose `environment` values override `env_file` values for the same variable.
- Local and production compose files force `OBSURA_ENV` to `development` or `production` respectively.
- `OBSURA_STORAGE_ROOT` is set by compose to `/var/lib/obsura` so the container uses the mounted persistent volume.

## Secrets Handling

- do not commit real `env/*.env` files
- keep real passwords out of shell history when possible
- rotate database credentials through your normal operator process
- treat backup artifacts as sensitive because they contain database contents
