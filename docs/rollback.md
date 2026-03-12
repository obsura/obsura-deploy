# Rollback

Rollback means returning to a previously known-good image reference and, if needed, restoring data from a backup taken before the failed upgrade.

## Basic Rollback

CLI form:

```bash
obsuractl rollback production --to-image ghcr.io/obsura/obsura-api@sha256:<previous-digest>
```

Script form:

```bash
bash scripts/rollback.sh production ghcr.io/obsura/obsura-api@sha256:<previous-digest>
```

The rollback scripts update `env/global.env`, recreate the stack, wait for API health, and restore the previous `OBSURA_API_IMAGE` value if the recreate step fails.

Manual equivalent:

1. Set `OBSURA_API_IMAGE` in `env/global.env` back to the previously approved image.
2. Run:

```bash
bash scripts/update.sh production
```

3. Verify:

- `obsuractl status production`
- `curl http://127.0.0.1:8000/api/v1/health`
- `obsuractl logs production api --tail 200`

`obsuractl status production` prints the running API image reference and image id so you can verify that the previous release is actually back in service.

## When Image Reversion Is Not Enough

If the failed version changed database schema or wrote incompatible persistent data, image rollback alone may not be sufficient. In that case restore the pre-upgrade backup:

```bash
obsuractl restore production backups/production/<timestamp> --yes
```

The restore workflow replaces the current database and app volume contents. Use it deliberately.

## What To Record

- the failing image reference
- the previously good image reference
- the backup set used for recovery
- logs captured during failure and rollback
