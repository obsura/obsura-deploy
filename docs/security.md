# Security

This repository follows practical least-privilege defaults. It does not pretend Docker Compose alone makes the stack fully hardened.

## Current Hardening Approach

- API is published on localhost only by default
- PostgreSQL is internal only and not published to the host
- API root filesystem is read-only
- API drops Linux capabilities with `cap_drop: [ALL]`
- API and PostgreSQL set `no-new-privileges:true`
- writable temporary paths use `tmpfs` where practical
- container startup waits on storage initialization and PostgreSQL health

## Why Operational Simplicity Matters

Operational simplicity is part of the security posture here.

- Compose files stay first-class so operators can inspect the real runtime model.
- Scripts stay usable so recovery does not depend on one entrypoint.
- `obsuractl` stays thin so it does not hide behavior behind a private control plane.

That transparency reduces risk. When operators can see which compose file, env files, image reference, and backup path are in use, incident response is faster and mistakes are easier to catch.

## Why PostgreSQL Stays Internal

The application and database are meant to communicate over the internal Compose network. Publishing PostgreSQL to the host adds exposure and operator footguns that this repository does not need for normal operation.

## Reverse Proxy Recommendation

Run Caddy or Nginx in front of the API for:

- TLS termination
- request logging
- header policy
- future edge controls

The API container is not meant to be the public edge by default.

## Storage Permissions

The published image is expected to run as a non-root user while still needing write access to its persistent storage. The `volume-init` helper prepares the named volume accordingly. If the image changes usernames or numeric IDs, revise that init step before rollout.

## Secret Hygiene

- do not commit real env files
- use strong random PostgreSQL passwords
- restrict access to backup directories
- rotate credentials through your normal operator process

## Hardening Limits

- host patching is still your job
- backup encryption and off-host retention are still your job
- reverse proxy tuning is still your job
- container isolation does not replace OS-level hardening
- full monitoring and observability stacks still belong to dedicated external tooling
