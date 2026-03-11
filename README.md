# obsura-deploy

Deployment, runtime, and operations stack for Obsura. This repository is the source of truth for running released Obsura services from published container images outside the source repositories.

## What This Repo Is For

`obsura-deploy` owns:

- Docker Compose orchestration
- runtime wiring for released images
- environment templates
- reverse-proxy examples
- deployment, upgrade, backup, and restore scripts
- production and local operator documentation

`obsura-deploy` does not own:

- application source code
- application Dockerfiles
- migrations source
- product features
- backend or frontend implementation logic

## How This Differs From `obsura-api`

`obsura-api` is the application repository. It owns the API source code, image build, application internals, and code-level migrations.

`obsura-deploy` consumes the published `ghcr.io/obsura/obsura-api` image and defines how that image is run with PostgreSQL, persistent storage, localhost binding, and an optional reverse proxy in front.

## Currently Supported Services

- `obsura-api` from GHCR
- PostgreSQL
- example Caddy and Nginx reverse-proxy configs

Future stacks can add `obsura-web`, dedicated proxy containers, and supporting services without changing the purpose of this repository.

## Quick Start

1. Copy the example env files:

   ```powershell
   Copy-Item env/global.env.example env/global.env
   Copy-Item env/api.env.example env/api.env
   Copy-Item env/postgres.env.example env/postgres.env
   ```

   ```bash
   cp env/global.env.example env/global.env
   cp env/api.env.example env/api.env
   cp env/postgres.env.example env/postgres.env
   ```

2. Edit `env/global.env` and `env/postgres.env`:

- set `OBSURA_API_IMAGE` to a real published release tag for local use
- set a strong `POSTGRES_PASSWORD`
- confirm the localhost bind address and port

3. Start the local stack:

   ```bash
   ./scripts/deploy.sh local
   ```

   ```powershell
   ./scripts/deploy.ps1 -Environment local
   ```

4. Verify the API:

   ```text
   http://127.0.0.1:8000/api/v1/health
   ```

   `8000` is the default from `env/global.env`. If you changed `OBSURA_API_HOST_PORT`, use that port instead.

## Repo Structure

```text
obsura-deploy/
├── compose/
│   ├── examples/
│   ├── local/
│   └── production/
├── docs/
├── env/
├── ops/
├── proxy/
│   ├── caddy/
│   └── nginx/
└── scripts/
```

## Supported Deployment Modes

- `compose/local/docker-compose.yaml`
  Uses released images for local bring-up with localhost-bound API access.
- `compose/production/docker-compose.yaml`
  Production-oriented single-host stack for running behind Caddy or Nginx.
- `compose/examples/docker-compose.single-node.yaml`
  Smaller readable reference file for operators who want a simplified example first.

## Environment Files

Place real operator-managed env files under `env/`:

- `env/global.env`
- `env/api.env`
- `env/postgres.env`

These files are gitignored. Only the `*.example` templates should be committed.

## How To Use The Compose Files

Manual Compose usage from the repository root:

```bash
docker compose \
  --env-file env/global.env \
  --env-file env/postgres.env \
  -f compose/local/docker-compose.yaml \
  up -d
```

The helper scripts wrap the same pattern and also perform basic validation.

## Current Limitations

- This repository currently targets `obsura-api` first.
- Production guidance is single-host Compose, not Kubernetes or Swarm.
- Secret management is file-based for now. Use your own secret distribution process.
- Reverse proxy configs are examples, not fully managed edge deployments.

## Tag And Digest Policy

For local and staging use, release tags are acceptable if you need readability and quick iteration.

For production, prefer immutable image digests:

```text
ghcr.io/obsura/obsura-api@sha256:<published-digest>
```

Tags are easier to read but can move. Digests are the safer production reference because they pin the exact image you tested and approved.
