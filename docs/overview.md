# Overview

`obsura-deploy` exists to run released Obsura services from published container images. It is the deployment and operations repository. It is not the application implementation repository.

## Ownership Boundary

`obsura-api` owns:

- source code
- application Dockerfile and build logic
- database initialization or migration behavior
- application internals
- product features

`obsura-deploy` owns:

- consumption of released images
- Docker Compose orchestration
- runtime environment wiring
- persistent volume setup
- reverse proxy examples
- helper scripts
- the `obsuractl` operator CLI
- deployment and operations documentation

That split matters. If the application image contract changes, update `obsura-deploy` to match it. Do not start copying app code here.

## Deployment Philosophy

- secure by default
- least privilege where practical
- reproducible image references
- understandable by a solo maintainer
- Docker Compose before heavier orchestration
- localhost-bound application exposure by default
- reverse proxy at the public edge

## Why The CLI Exists

`obsuractl` exists because operators benefit from a small, consistent command surface for the workflows this repository already documents. It helps with validation, stack targeting, logs, updates, backup, restore, and rollback.

It is intentionally thin:

- it wraps the same env files the compose files use
- it wraps the same scripts the repository exposes directly
- it shells out to `docker compose` for inspection commands
- it keeps the manual path valid and documented

That thinness is deliberate. If the CLI became a hidden platform with its own state model, the repository would become harder to reason about and harder to recover manually.

## Current Runtime Model

Today the primary stack is:

- `obsura-api`
- PostgreSQL
- persistent app storage
- optional reverse proxy in front

The compose files assume:

- a health endpoint at `/api/v1/health`
- a writable application storage root at `/var/lib/obsura`
- a non-root runtime user inside the published image
- PostgreSQL connectivity provided through `DATABASE_URL`

The `volume-init` service exists because least-privilege app runtimes often cannot safely initialize named volume permissions on their own.
