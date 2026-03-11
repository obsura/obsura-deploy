# obsuractl

`obsuractl` is an operator tool for `obsura-deploy`. It is a convenience and safety layer over the repository's documented deployment model. It does not replace Docker, Docker Compose, or the Compose files in this repository.

## Purpose

Use `obsuractl` when you want:

- one clear command surface for common operator tasks
- validation before running into obvious mistakes
- readable wrappers around the supported scripts and Compose commands
- quick access to logs, status, updates, backups, restores, and rollback

The same CLI is also shipped as standalone GitHub Release binaries for supported platforms. That distribution model exists for operator convenience; it does not change the deployment architecture.

Do not think of `obsuractl` as a platform. It is not a control plane, not a monitoring system, and not a hidden orchestration layer.

## Design Philosophy

`obsuractl` is intentionally thin:

- it shells out to Docker Compose and the repository scripts
- it uses the same `env/*.env` files documented elsewhere
- it prints the compose file, env files, and image references it is acting on
- it keeps the underlying deployment behavior visible to the operator

If you remove the CLI, the repository still works. That is a design requirement, not an accident.

## Release Distribution

`obsuractl` binaries are published from GitHub branches using a conservative release model:

- `dev` push -> prerelease binaries tagged `dev-<shortsha>`
- `main` push -> stable binaries tagged `vX.Y.Z`

Version source for stable releases:

- [cli/obsuractl/version.py](../cli/obsuractl/version.py)

Supported binary assets today:

- `linux-amd64`
- `windows-amd64`

Archive naming:

- `obsuractl_<version>_<os>_<arch>.zip`
- `checksums.txt`

Binary branding assets:

- source artwork lives under [../cli/assets](../cli/assets)
- Windows builds generate an `.ico` from those assets and embed it in `obsuractl.exe`

## What It Wraps

- `compose/local/docker-compose.yaml`
- `compose/production/docker-compose.yaml`
- `env/global.env`
- `env/api.env`
- `env/postgres.env`
- `scripts/deploy.*`
- `scripts/update.*`
- `scripts/rollback.*`
- `scripts/backup.*`
- `scripts/restore.*`
- direct `docker compose` inspection commands for logs, restart, status, and shutdown

## Supported v1 Commands

- `obsuractl init`
- `obsuractl doctor <local|production>`
- `obsuractl up <local|production>`
- `obsuractl down <local|production>`
- `obsuractl restart <local|production> [services...]`
- `obsuractl status <local|production>`
- `obsuractl logs <local|production> [services...] [--follow] [--tail N]`
- `obsuractl update <local|production>`
- `obsuractl rollback <local|production> --to-image <published-tag-or-digest>`
- `obsuractl backup <local|production> [--output-dir PATH]`
- `obsuractl restore <local|production> <backup_dir> --yes`

## What Each Command Does

- `init`
  Copies missing env files from the committed examples. It does not invent environment state outside `env/`.
- `doctor`
  Validates Docker, Docker Compose, env files, placeholder values, port assumptions, and `docker compose config`.
- `up`
  Runs the deploy script for the selected environment.
- `down`
  Runs `docker compose down --remove-orphans` for the selected environment.
- `restart`
  Runs `docker compose restart` for the selected environment, optionally scoped to services.
- `status`
  Runs `docker compose ps`.
- `logs`
  Runs `docker compose logs` against the selected environment and optional services.
- `update`
  Runs the update script using the current `OBSURA_API_IMAGE` in `env/global.env`.
- `rollback`
  Writes a previously approved image reference into `env/global.env`, then runs the update script.
- `backup`
  Runs the backup script and reports the output location.
- `restore`
  Runs the restore script and requires explicit `--yes` confirmation.

## Manual Equivalents

Every CLI operation has a manual path.

- Deploy:
  `bash scripts/deploy.sh production`
- Update:
  `bash scripts/update.sh production`
- Rollback:
  `bash scripts/rollback.sh production ghcr.io/obsura/obsura-api@sha256:<previous-digest>`
- Backup:
  `bash scripts/backup.sh production`
- Restore:
  `bash scripts/restore.sh production backups/production/<timestamp> --yes`
- Status:
  `docker compose --env-file env/global.env --env-file env/postgres.env --env-file env/api.env -f compose/production/docker-compose.yaml ps`

The CLI exists because operators should not have to reconstruct those commands from memory every time. It does not replace them.

Underneath that script-level rollback path, the deployment model is still the same: set `OBSURA_API_IMAGE` to the desired previous image and recreate the stack.

## Examples

```bash
obsuractl init
obsuractl doctor local
obsuractl up local
obsuractl logs local api --follow
obsuractl doctor production
obsuractl update production
obsuractl rollback production --to-image ghcr.io/obsura/obsura-api@sha256:<published-digest>
obsuractl backup production --output-dir backups/production/manual-test
obsuractl restore production backups/production/20260311-210000 --yes
```

## Operator Safety Notes

- `restore` is destructive and requires `--yes`.
- `rollback` changes `OBSURA_API_IMAGE` in `env/global.env` and then recreates services.
- `update` and `rollback` use whatever image reference is written in `env/global.env`.
- `doctor` warns when production is using a tag instead of a digest.
- `backup` and `restore` print the backup path and storage volume they touch.

## Out Of Scope

`obsuractl` does not implement:

- metrics storage
- dashboarding
- alerting backends
- log indexing platforms
- secret management
- background daemons
- internal state databases
- infrastructure provisioning
- cluster orchestration

Use external observability, secret, and infrastructure tooling for those concerns.
