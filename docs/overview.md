# Overview

`obsura-deploy` exists to run released Obsura services from published container images. It is the deployment and operations repository, not the application development repository.

## Ownership Boundary

`obsura-api` owns:

- source code
- image build and Dockerfile
- application internals
- migrations source
- implementation behavior

`obsura-deploy` owns:

- Compose orchestration
- runtime environment wiring
- persistent volume layout
- reverse-proxy integration examples
- deployment and maintenance scripts
- operator documentation for deployment, upgrades, rollback, and backups

## Deployment Philosophy

- secure by default where practical
- least privilege without pretending Compose is a full hardening solution
- localhost-bound application exposure by default
- reverse proxy at the public edge
- reproducible image references
- simple single-host operations before more complex orchestration
- readable configs that a solo maintainer can operate confidently

## Current Stack

The first supported service is `obsura-api`, backed by PostgreSQL and persistent storage. This repository uses published container images such as `ghcr.io/obsura/obsura-api:<tag>` or, preferably in production, `ghcr.io/obsura/obsura-api@sha256:<digest>`.

## Important Runtime Assumptions

- `obsura-api` exposes its health endpoint at `/api/v1/health`
- production requires a PostgreSQL `DATABASE_URL`
- the published image runs as a non-root `obsura` user
- the application needs writable persistent storage for generated artifacts and uploads
- the volume-init step assumes the image includes both the `obsura` user and a POSIX shell

If the image contract changes, update the compose files and scripts in this repository rather than patching around it ad hoc on hosts.
