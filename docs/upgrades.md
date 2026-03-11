# Upgrades

Upgrade by changing the image reference, validating the deployment, and recreating services against the new image.

## Recommended Procedure

1. Read the release notes for the target `obsura-api` image.
2. Record the currently deployed tag or digest.
3. Take a backup.
4. Change `OBSURA_API_IMAGE` in `env/global.env`.
5. Run the update workflow.
6. Verify health, logs, and expected behavior.

Recommended commands:

```bash
obsuractl backup production
obsuractl update production
obsuractl status production
```

`obsuractl update production` uses the image reference currently written in `env/global.env`. It does not discover or select an image for you.

Script form:

```bash
bash scripts/backup.sh production
bash scripts/update.sh production
```

Direct manual Compose is still supported if you prefer not to use the CLI or scripts.

## Tags vs Digests

Prefer promoting a tested digest into production rather than following a mutable tag indefinitely.

Good:

```text
OBSURA_API_IMAGE=ghcr.io/obsura/obsura-api@sha256:<published-digest>
```

Weaker:

```text
OBSURA_API_IMAGE=ghcr.io/obsura/obsura-api:<release-tag>
```

## Verify After Upgrade

- `obsuractl doctor production`
- `obsuractl status production`
- `curl http://127.0.0.1:8000/api/v1/health`
- recent `api` and `postgres` logs

If the release can affect schema or stored data, treat rollback as a restore-capable operation, not only an image swap.
