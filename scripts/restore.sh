#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT="${1:-production}"
BACKUP_DIR="${2:-}"

case "$ENVIRONMENT" in
  local|production) ;;
  *)
    echo "Usage: $0 [local|production] <backup-dir>" >&2
    exit 1
    ;;
esac

if [[ -z "$BACKUP_DIR" ]]; then
  echo "Usage: $0 [local|production] <backup-dir>" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/compose/$ENVIRONMENT/docker-compose.yaml"
GLOBAL_ENV="$ROOT_DIR/env/global.env"
API_ENV="$ROOT_DIR/env/api.env"
POSTGRES_ENV="$ROOT_DIR/env/postgres.env"

for file in "$COMPOSE_FILE" "$GLOBAL_ENV" "$API_ENV" "$POSTGRES_ENV"; do
  if [[ ! -f "$file" ]]; then
    echo "Missing required file: $file" >&2
    exit 1
  fi
done

BACKUP_DIR_ABS="$(cd "$BACKUP_DIR" && pwd)"

if [[ ! -f "$BACKUP_DIR_ABS/postgres.sql" ]]; then
  echo "Missing $BACKUP_DIR_ABS/postgres.sql" >&2
  exit 1
fi

if [[ ! -f "$BACKUP_DIR_ABS/obsura-data.tgz" ]]; then
  echo "Missing $BACKUP_DIR_ABS/obsura-data.tgz" >&2
  exit 1
fi

set -a
. "$GLOBAL_ENV"
. "$POSTGRES_ENV"
set +a

compose() {
  docker compose \
    --env-file "$GLOBAL_ENV" \
    --env-file "$POSTGRES_ENV" \
    --env-file "$API_ENV" \
    -f "$COMPOSE_FILE" \
    "$@"
}

echo "Stopping API before restore..."
compose stop api || true

echo "Starting postgres for restore..."
compose up -d postgres

echo "Waiting for postgres readiness..."
for _ in {1..30}; do
  if compose exec -T postgres pg_isready -U "$POSTGRES_USER" -d postgres > /dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! compose exec -T postgres pg_isready -U "$POSTGRES_USER" -d postgres > /dev/null 2>&1; then
  echo "Postgres did not become ready in time." >&2
  exit 1
fi

echo "Restoring Obsura storage volume..."
docker run --rm \
  --mount "type=volume,source=${OBSURA_STORAGE_VOLUME:-obsura-storage},target=/target" \
  --mount "type=bind,source=$BACKUP_DIR_ABS,target=/backup,readonly" \
  alpine:3.20 \
  sh -ec 'find /target -mindepth 1 -maxdepth 1 -exec rm -rf {} + && tar -xzf /backup/obsura-data.tgz -C /target'

echo "Resetting database..."
compose exec -T postgres psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 \
  -c "DROP DATABASE IF EXISTS \"$POSTGRES_DB\";"
compose exec -T postgres psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 \
  -c "CREATE DATABASE \"$POSTGRES_DB\";"

echo "Loading PostgreSQL dump..."
compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 < "$BACKUP_DIR_ABS/postgres.sql"

echo "Re-applying storage permissions..."
compose run --rm --no-deps volume-init

echo "Starting full stack..."
compose up -d

echo "Restore complete."
