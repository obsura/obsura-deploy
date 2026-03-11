# Backups

The current backup model is intentionally simple:

- logical PostgreSQL dump
- tar archive of the Obsura application data volume

This is enough for first-stage operations, but it is not point-in-time recovery.

## What The Scripts Capture

`scripts/backup.sh` and `scripts/backup.ps1` create:

- `postgres.sql`
- `obsura-data.tgz`
- `metadata.txt`

By default these land under `backups/<environment>/<timestamp>/`.

## Run A Backup

```bash
./scripts/backup.sh production
```

```powershell
./scripts/backup.ps1 -Environment production
```

## Restore Expectations

The restore scripts:

- stop the API
- start PostgreSQL if needed
- replace the Obsura data volume contents
- drop and recreate the target database
- load the SQL dump
- re-run `volume-init`
- start the full stack

That means restore is a full replacement of the current database and app data volume, not a selective recovery tool.

## Operational Guidance

- test backups and restores before depending on them
- protect backup files like production data
- take a backup before every production upgrade
- store critical backups off-host if you care about host failure scenarios
