# Backups

The backup model in this repository is intentionally simple and readable:

- PostgreSQL logical dump
- tar archive of the Obsura storage volume
- metadata about the image and storage volume used at backup time

This is enough for first-stage self-hosted operations. It is not point-in-time recovery.

## What The Helpers Create

Each backup set contains:

- `postgres.sql`
- `obsura-data.tgz`
- `metadata.txt`

Default location:

```text
backups/<environment>/<timestamp>/
```

## Run A Backup

Recommended:

```bash
obsuractl backup production
```

`obsuractl backup` is a wrapper around the documented backup scripts. It does not implement a separate backup engine.

Scripts:

```bash
bash scripts/backup.sh production
```

```powershell
./scripts/backup.ps1 -Environment production
```

## Restore Expectations

Restore is full replacement, not selective recovery. The documented restore workflow:

1. stops the API
2. starts PostgreSQL if needed
3. replaces the app data volume contents
4. drops and recreates the target database
5. loads the SQL dump
6. re-runs storage initialization
7. starts the full stack

Recommended command:

```bash
obsuractl restore production backups/production/<timestamp> --yes
```

## What This Repo Automates

- creating a logical PostgreSQL dump
- archiving the app data volume
- restoring those artifacts back into the Compose-managed volumes

## What This Repo Does Not Automate

- off-host backup shipping
- backup encryption
- retention policy
- point-in-time recovery
- cross-host disaster recovery testing
