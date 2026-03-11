# Upgrades

Upgrade by changing the image reference in `env/global.env`, validating it, taking a backup, and then running the update workflow.

## Recommended Procedure

1. Read the release notes for the new `obsura-api` image.
2. Record the currently deployed image reference.
3. Run a backup:

   ```bash
   ./scripts/backup.sh production
   ```

4. Change `OBSURA_API_IMAGE` in `env/global.env` to the new tag or digest.
5. Pull and recreate services:

   ```bash
   ./scripts/update.sh production
   ```

6. Verify:
   - `docker compose ... ps`
   - `curl http://127.0.0.1:8000/api/v1/health`
   - application logs

## Tag Versus Digest

Prefer switching production to a digest after validation. A digest lets you prove that the image you tested is the one you deployed.

## Schema And Data Risk

This repository does not own application migrations. If a release changes schema or storage behavior, a rollback may require both reverting the image and restoring a pre-upgrade backup. Treat upgrades as data-affecting operations unless release notes say otherwise.
