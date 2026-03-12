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
The backup scripts fail if the configured Obsura storage volume does not exist, which avoids silently creating an empty replacement volume during backup.
Backup and restore use the current PostgreSQL credentials from `env/postgres.env`, so those values must still match the live database.

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
8. waits for API health before reporting success

Recommended command:

```bash
obsuractl restore production backups/production/<timestamp> --yes
```

Before it overwrites anything, the restore workflow prints the backup metadata when `metadata.txt` is present. That gives the operator one last check of the source environment, image reference, and storage volume name.

## What This Repo Automates

- creating a logical PostgreSQL dump
- archiving the app data volume
- restoring those artifacts back into the Compose-managed volumes
- recording simple backup metadata such as environment, image reference, storage volume, and database name

## What This Repo Does Not Automate

- off-host backup shipping
- backup encryption
- retention policy
- point-in-time recovery
- cross-host disaster recovery testing
- PostgreSQL password rotation inside an already-initialized database cluster
