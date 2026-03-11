# obsura-deploy

`obsura-deploy` is the deployment and operations repository for released Obsura container images. It does not contain application source code. It exists to run published services such as `ghcr.io/obsura/obsura-api:<tag>` in a professional, self-hosted, production-minded way with Docker Compose.

This repository also publishes standalone `obsuractl` binaries through GitHub Releases.

## Repo Purpose

This repository is the source of truth for:

- local deployment of released Obsura images
- production deployment of released Obsura images
- runtime wiring for PostgreSQL and persistent storage
- localhost-first service exposure
- reverse proxy examples
- upgrade, rollback, backup, and restore procedures
- helper scripts and the `obsuractl` operator CLI

`obsura-deploy` does not own:

- application source code
- application Dockerfiles
- application internals
- product features
- release build pipelines for `obsura-api`

Those concerns belong in the application repositories such as `obsura-api`.

## Supported Services Today

- `ghcr.io/obsura/obsura-api`
- PostgreSQL
- persistent Docker volumes for database and app storage
- optional Caddy or Nginx in front of the API

The structure is designed so `obsura-web` can be added later without changing the purpose of this repository.

## Quick Start

1. Create local env files from the templates.

```bash
cp env/global.env.example env/global.env
cp env/api.env.example env/api.env
cp env/postgres.env.example env/postgres.env
```

```powershell
Copy-Item env/global.env.example env/global.env
Copy-Item env/api.env.example env/api.env
Copy-Item env/postgres.env.example env/postgres.env
```

2. Edit `env/global.env` and `env/postgres.env`.

- Set `OBSURA_API_IMAGE` to a real published image reference.
- Replace `POSTGRES_PASSWORD` with a strong random value.
- Leave `OBSURA_API_BIND_ADDRESS=127.0.0.1` unless you have a deliberate reason to expose the API differently.

3. Optional but recommended: install the operator CLI.

```bash
python -m pip install -e .
```

4. Validate the stack.

```bash
obsuractl doctor local
```

5. Start the local stack.

```bash
obsuractl up local
```

Without the CLI, the repository stays fully operable through the helper scripts and direct Compose commands:

```bash
bash scripts/deploy.sh local
```

```powershell
./scripts/deploy.ps1 -Environment local
```

6. Verify the API health endpoint.

```text
http://127.0.0.1:8000/api/v1/health
```

Change the port if you changed `OBSURA_API_HOST_PORT`.

## Local vs Production Compose

| Stack | File | Intended use |
| --- | --- | --- |
| Local | `compose/local/docker-compose.yaml` | localhost-bound evaluation, testing, and operator bring-up with released images |
| Production | `compose/production/docker-compose.yaml` | single-host production deployment behind Caddy or Nginx |
| Example | `compose/examples/docker-compose.single-node.yaml` | small readable reference stack for operators who want one file to study first |

Both primary stacks:

- keep PostgreSQL internal only
- use named volumes for PostgreSQL and Obsura storage
- initialize writable app storage for a non-root runtime
- include healthchecks
- publish the API only on localhost by default

## Environment Files

Real operator-managed env files live under `env/` and are gitignored:

- `env/global.env`
- `env/api.env`
- `env/postgres.env`

The compose files depend on these env files both for container runtime values and for Compose interpolation. Manual `docker compose` usage must pass all three env files, not just one of them.

## Tags vs Digests

Use release tags for local evaluation when readability matters. For production, prefer immutable digests:

```text
ghcr.io/obsura/obsura-api@sha256:<published-digest>
```

Tags are easier to read. Digests are safer because they pin the exact image you validated.

## What Must Be Customized Before Production

- `OBSURA_API_IMAGE`
- `POSTGRES_PASSWORD`
- hostname and certificate settings in your reverse proxy config
- any storage volume naming needed for the target host
- any backup target location policy you need beyond the local default

## obsuractl

`obsuractl` is a thin operator tool over the documented Compose and script workflows. It is optional, it does not replace Docker, and it does not create hidden deployment state.

It exists to:

- reduce operator mistakes
- make environment targeting explicit
- wrap supported workflows consistently
- expose the exact files and commands being used

It is not:

- a deployment platform
- a monitoring backend
- a metrics or logging system
- a secret manager
- a configuration management platform
- a replacement for Docker Compose

Common commands:

```bash
obsuractl init
obsuractl doctor production
obsuractl up production
obsuractl status production
obsuractl logs production api --follow
obsuractl update production
obsuractl rollback production --to-image ghcr.io/obsura/obsura-api@sha256:<published-digest>
obsuractl backup production
obsuractl restore production backups/production/<timestamp> --yes
```

Manual equivalents remain first-class and documented. The CLI wraps those workflows; it does not define a parallel deployment architecture.

## GitHub Release Model

`obsuractl` binaries follow a two-branch release model:

- `dev`
  Integration branch. Pushes build prerelease binaries and publish a GitHub prerelease tagged `dev-<shortsha>`.
- `main`
  Stable branch. Pushes build stable binaries and publish a GitHub Release tagged `vX.Y.Z`.

Pull requests targeting `dev` or `main` run CI only. They do not publish releases.

Version source:

- stable release version source: [cli/obsuractl/version.py](cli/obsuractl/version.py)
- stable GitHub release tag format: `vX.Y.Z`
- dev prerelease tag format: `dev-<shortsha>`

Supported binary assets today:

- `linux-amd64`
- `windows-amd64`

Asset naming:

- `obsuractl_<version>_<os>_<arch>.zip`
- `checksums.txt`

Examples:

- `obsuractl_v0.1.0_linux_amd64.zip`
- `obsuractl_v0.1.0_windows_amd64.zip`
- `obsuractl_dev-a921b32_linux_amd64.zip`

GitHub handles the latest stable release through release metadata. This repository does not use a mutable Git tag named `latest`.

To cut a new stable release from `main`, bump `__version__` in [cli/obsuractl/version.py](cli/obsuractl/version.py) before merging.

## Repository Structure

```text
obsura-deploy/
|-- README.md
|-- pyproject.toml
|-- compose/
|   |-- local/
|   |-- production/
|   `-- examples/
|-- env/
|-- scripts/
|-- cli/
|   `-- obsuractl/
|-- docs/
|-- proxy/
|   |-- caddy/
|   `-- nginx/
|-- THIRD_PARTY_NOTICES.md
`-- DEPENDENCY_LICENSE_INVENTORY.md
```

## Documentation

- [docs/overview.md](docs/overview.md)
- [docs/local.md](docs/local.md)
- [docs/production.md](docs/production.md)
- [docs/configuration.md](docs/configuration.md)
- [docs/security.md](docs/security.md)
- [docs/cli.md](docs/cli.md)
- [docs/upgrades.md](docs/upgrades.md)
- [docs/rollback.md](docs/rollback.md)
- [docs/backups.md](docs/backups.md)
- [docs/releases.md](docs/releases.md)
