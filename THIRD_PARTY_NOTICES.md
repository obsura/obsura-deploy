# Third-Party Notices

`obsura-deploy` references and orchestrates third-party runtime components. This repository does not vendor or redistribute those binaries directly. Operators pull and run them in their own environments.

## Docker Engine and Docker Compose

- Purpose: local container runtime and Compose orchestration prerequisite
- Distribution model: operator-installed prerequisite, not bundled in this repository
- Upstream: https://www.docker.com/
- License context: review the Docker Engine and Compose licenses for the versions you install in your environment

## PostgreSQL Container Image

- Component: `postgres:17-alpine`
- Purpose: database runtime for the Obsura API stack
- Distribution model: pulled from the Docker Official Images registry namespace at deployment time
- Upstream image documentation: https://hub.docker.com/_/postgres
- Upstream project: https://www.postgresql.org/

## Alpine Linux Container Image

- Component: `alpine:3.20`
- Purpose: lightweight helper image used by the backup and restore scripts to archive and extract Docker volumes
- Distribution model: pulled at operation time when backup or restore helpers run
- Upstream: https://hub.docker.com/_/alpine

## Caddy

- Component: example reverse-proxy configuration only
- Purpose: optional TLS-terminating reverse proxy in front of localhost-bound Obsura services
- Distribution model: not bundled; operators install and manage Caddy separately
- Upstream: https://caddyserver.com/

## Nginx

- Component: example reverse-proxy configuration only
- Purpose: optional TLS-terminating reverse proxy in front of localhost-bound Obsura services
- Distribution model: not bundled; operators install and manage Nginx separately
- Upstream: https://nginx.org/

## Obsura Published Images

- Component: `ghcr.io/obsura/obsura-api`
- Purpose: released Obsura API image consumed by this deployment repository
- Distribution model: pulled from the Obsura GitHub Container Registry namespace at deployment time
- Upstream: https://github.com/obsura

## PyInstaller

- Component: `pyinstaller`
- Purpose: build-time dependency used in GitHub Actions to produce standalone `obsuractl` binaries
- Distribution model: installed in CI/build environments only, not shipped as an operator runtime component
- Upstream: https://pyinstaller.org/

Operators are responsible for validating the licenses, notices, and support status of the exact image tags or digests they deploy.
