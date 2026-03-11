# Security Notes

This repository aims for practical hardening, not perfect isolation.

## Current Hardening Measures

- `obsura-api` is exposed on localhost only by default
- PostgreSQL is not published to the host
- `obsura-api` uses a read-only root filesystem
- `obsura-api` drops Linux capabilities with `cap_drop: [ALL]`
- `obsura-api` and `postgres` set `no-new-privileges`
- temporary writable paths use `tmpfs` where practical
- service startup waits for storage initialization and database health

## Why Localhost Binding Is The Default

Binding the API to `127.0.0.1` narrows accidental exposure and makes the public edge explicit. TLS, request filtering, and Internet-facing policy should live in a reverse proxy rather than directly on the application container.

## Why A Reverse Proxy Is Recommended

Use Caddy or Nginx in front of the API for:

- TLS termination
- host and header policy
- access logging
- future rate limiting or edge controls

## Volume Permissions

The `volume-init` service exists because the API image runs as a non-root user and still needs a writable data volume. The init step prepares `/var/lib/obsura` for that runtime user. If the image changes its UID, GID, or username, revisit the init command before deploying new images.

## Secrets Hygiene

- keep real env files out of version control
- use strong random database passwords
- restrict backup file access
- prefer digests in production so you know exactly what image you approved

## Public Versus Internal Services

- public edge: reverse proxy only
- local host exposure: `obsura-api`
- internal only: PostgreSQL

Do not publish PostgreSQL ports to the host unless you have a specific operational reason and compensating controls.
