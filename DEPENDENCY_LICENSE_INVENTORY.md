# Dependency License Inventory

This inventory records the runtime components and optional operational dependencies referenced by `obsura-deploy`. It is a deployment inventory, not a source-code lockfile.

| Component | Example reference | Role in this repo | License notes |
| --- | --- | --- | --- |
| Obsura API image | `ghcr.io/obsura/obsura-api:<tag>` or `@sha256:<digest>` | Primary application service consumed from published releases | Follow the license published by the Obsura source repository and release artifacts for the exact image you deploy. |
| PostgreSQL image | `postgres:17-alpine` | Database runtime | PostgreSQL server uses the PostgreSQL License. The container image also includes Alpine Linux userland packages under their respective licenses. |
| Alpine helper image | `alpine:3.20` | Used by backup and restore helpers for tar-based volume archive operations | Alpine packages carry their own package-level licenses. Review the exact image contents you approve. |
| Docker Engine | Operator installed | Container runtime prerequisite | Review the license terms for the installed engine distribution in your environment. |
| Docker Compose plugin | Operator installed | Compose orchestration prerequisite | Review the license terms for the installed Compose plugin version in your environment. |
| PyInstaller | CI/build dependency | Builds standalone `obsuractl` release binaries in GitHub Actions | PyInstaller uses GPLv2-or-later with a bootloader exception; review the exact project licensing terms for your approved build process. |
| Caddy | Optional external reverse proxy | Example reverse-proxy target supported by the docs and config examples | Apache License 2.0 for the upstream project; verify the exact binary package you deploy. |
| Nginx | Optional external reverse proxy | Example reverse-proxy target supported by the docs and config examples | The upstream open source Nginx project uses a 2-clause BSD-style license; verify the exact package build you deploy. |

## Notes

- This repository does not ship third-party binaries inside the Git tree.
- Container images referenced here should be pinned and reviewed as part of your release approval process.
- Production deployments should prefer immutable image digests so the approved artifact and the running artifact are the same thing.
