# Rollback

Rollback means returning to a previously known-good image reference and, if necessary, restoring data captured before the failed upgrade.

## Basic Rollback

1. Set `OBSURA_API_IMAGE` in `env/global.env` back to the prior tested tag or digest.
2. Run:

   ```bash
   ./scripts/update.sh production
   ```

3. Verify the API health endpoint and logs.

## When Image Reversion Is Not Enough

If the failed version changed database schema or wrote incompatible persistent data, image rollback alone may not be sufficient. In that case:

1. stop the API
2. restore the pre-upgrade backup
3. start the stack again

Example:

```bash
./scripts/restore.sh production backups/production/<timestamp>
```

## What To Preserve Before Rolling Back

- the failing image reference
- the previously known-good image reference
- logs around the failure window
- the latest backup set used for recovery

Rollbacks are safest when every production promotion starts with a backup and an explicitly recorded prior image digest.
