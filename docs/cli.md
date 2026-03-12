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

## Repository Checkout Requirement

`obsuractl` operates on an `obsura-deploy` repository checkout. The binary and the repository are separate things:

- the binary provides the command
- the repository checkout provides `compose/`, `env/`, `scripts/`, and docs

By default `obsuractl` searches from the current working directory upward until it finds an `obsura-deploy` checkout.

Explicit override options:

- `obsuractl --repo-root /path/to/obsura-deploy ...`
- `OBSURA_DEPLOY_ROOT=/path/to/obsura-deploy`

If env files are missing after discovery, run:

```bash
obsuractl init --quickstart-local --image ghcr.io/obsura/obsura-api:<published-tag-or-digest>
```

Template-only fallback:

```bash
obsuractl init --template-only
```

If you are running the standalone binary from outside the checkout, use:

```bash
obsuractl --repo-root /path/to/obsura-deploy init --quickstart-local --image ghcr.io/obsura/obsura-api:<published-tag-or-digest>
```

## Fastest Local Path

The shortest supported local flow is now:

```bash
obsuractl init --quickstart-local --image ghcr.io/obsura/obsura-api:<published-tag-or-digest>
obsuractl up local
```

That quickstart mode:

- creates `env/global.env`, `env/api.env`, and `env/postgres.env`
- writes the local api image into `compose/local/docker-compose.yaml`
- generates a strong `POSTGRES_PASSWORD`
- keeps the default localhost-only API binding

On interactive terminals, plain `obsuractl init` can offer the same quickstart and ask you for the image reference instead of requiring `--image` on the command line.

If you want template files only, use:

```bash
obsuractl init --template-only
```

## Built-In Help

`obsuractl` now treats terminal help as a first-class operator surface, not just a flag dump.

- top-level help: `obsuractl --help`
- command help: `obsuractl <command> --help`
- version: `obsuractl --version`

The built-in help includes:

- quick-start examples
- per-command examples
- notes about what each command wraps
- repo discovery guidance
- Linux man-page hints

## Color Output

On interactive terminals, `obsuractl` uses ANSI color for:

- success, warning, and error markers
- command hints and wrapped command output
- help headings and examples

Controls:

- auto: `obsuractl --color auto`
- force: `obsuractl --color always`
- disable: `obsuractl --color never`
- shortcut disable: `obsuractl --no-color`
- environment disable: `NO_COLOR=1`

For Linux operators, `--color always` is useful when piping through tools that preserve ANSI escapes.

## Linux Man Page

This repository now ships a man page at [../man/obsuractl.1](../man/obsuractl.1).

Quick use from the repository:

```bash
man ./man/obsuractl.1
```

Optional install on a Linux host:

```bash
install -Dm644 man/obsuractl.1 /usr/local/share/man/man1/obsuractl.1
mandb
man obsuractl
```

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
  Copies missing env files from the committed examples. It can also prepare a local quickstart by writing the image into `compose/local/docker-compose.yaml` and generating `POSTGRES_PASSWORD`. It does not create hidden state outside the checked-in files.
- `doctor`
  Validates Docker, Docker Compose, env files, placeholder values, port assumptions, and `docker compose config`.
- `up`
  Runs the deploy script for the selected environment.
- `down`
  Runs `docker compose down --remove-orphans` for the selected environment.
- `restart`
  Runs `docker compose restart` for the selected environment, optionally scoped to services.
- `status`
  Runs `docker compose ps` and then prints the running API image summary when a container exists.
- `logs`
  Runs `docker compose logs` against the selected environment and optional services.
- `update`
  Runs the update script using the current api image in the selected compose file. The wrapped script waits for API health before reporting success.
- `rollback`
  Writes a previously approved image reference into the selected compose file, then runs the update script. If the recreate step fails, the script restores the previous image value.
- `backup`
  Runs the backup script and reports the output location. Backup fails if the configured storage volume does not exist yet.
- `restore`
  Runs the restore script, prints backup metadata when present, waits for API health, and requires explicit `--yes` confirmation.

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

Underneath that script-level rollback path, the deployment model is still the same: set the compose-file image to the desired previous image and recreate the stack.

## Examples

```bash
obsuractl --help
obsuractl up --help
obsuractl init
obsuractl init --template-only
obsuractl init --quickstart-local --image ghcr.io/obsura/obsura-api:<published-tag-or-digest>
obsuractl up local
obsuractl doctor local
obsuractl --repo-root /srv/obsura-deploy doctor production
obsuractl --repo-root /srv/obsura-deploy init
obsuractl logs local api --follow
obsuractl doctor production
obsuractl update production
obsuractl rollback production --to-image ghcr.io/obsura/obsura-api@sha256:<published-digest>
obsuractl backup production --output-dir backups/production/manual-test
obsuractl restore production backups/production/20260311-210000 --yes
```

## Operator Safety Notes

- `restore` is destructive and requires `--yes`.
- `rollback` changes the selected compose file and then recreates services.
- `update` and `rollback` use whatever image reference is written in the selected compose file.
- `doctor` warns when production is using a tag instead of a digest.
- `backup` and `restore` print the backup path and storage volume they touch.
- `doctor`, `up`, and the other stack commands act on the discovered repository checkout, so verify the reported repository root when using a standalone binary.
- If `up` or `status` reports missing `env/*.env` files for local usage, the fastest fix is `obsuractl init --quickstart-local --image ghcr.io/obsura/obsura-api:<published-tag-or-digest>`.
- If you want template files without the quickstart prompt, use `obsuractl init --template-only`.
- If you need plain output for logs or automation, use `--no-color` or `NO_COLOR=1`.

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
