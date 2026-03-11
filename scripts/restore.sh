#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT="${1:-production}"
BACKUP_DIR="${2:-}"
CONFIRM="${3:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/common.sh"

obsura_require_environment "$ENVIRONMENT"
obsura_require_docker

if [[ -z "$BACKUP_DIR" ]]; then
  echo "Usage: $0 [local|production] <backup-dir> [--yes]" >&2
  exit 1
fi

obsura_require_confirmation "$CONFIRM"

ROOT_DIR="$(obsura_repo_root "${BASH_SOURCE[0]}")"
COMPOSE_FILE="$ROOT_DIR/compose/$ENVIRONMENT/docker-compose.yaml"
GLOBAL_ENV="$ROOT_DIR/env/global.env"
API_ENV="$ROOT_DIR/env/api.env"
POSTGRES_ENV="$ROOT_DIR/env/postgres.env"

obsura_require_files "$COMPOSE_FILE" "$GLOBAL_ENV" "$API_ENV" "$POSTGRES_ENV"

BACKUP_DIR_ABS="$(cd "$BACKUP_DIR" && pwd)"
obsura_require_files "$BACKUP_DIR_ABS/postgres.sql" "$BACKUP_DIR_ABS/obsura-data.tgz"

POSTGRES_USER="$(obsura_env_value "$POSTGRES_ENV" POSTGRES_USER || true)"
POSTGRES_DB="$(obsura_env_value "$POSTGRES_ENV" POSTGRES_DB || true)"
OBSURA_STORAGE_VOLUME="$(obsura_env_value "$GLOBAL_ENV" OBSURA_STORAGE_VOLUME || true)"

if [[ -z "$POSTGRES_USER" || -z "$POSTGRES_DB" ]]; then
  echo "POSTGRES_USER and POSTGRES_DB must be set in env/postgres.env." >&2
  exit 1
fi

if [[ -z "$OBSURA_STORAGE_VOLUME" ]]; then
  OBSURA_STORAGE_VOLUME="obsura-storage"
fi

obsura_print_stack_context "$ENVIRONMENT" "$COMPOSE_FILE" "$GLOBAL_ENV" "$API_ENV" "$POSTGRES_ENV"
echo "Restore source: $BACKUP_DIR_ABS"
echo "Storage volume: $OBSURA_STORAGE_VOLUME"

echo "Stopping API before restore..."
obsura_compose "$COMPOSE_FILE" "$GLOBAL_ENV" "$POSTGRES_ENV" "$API_ENV" stop api || true

echo "Starting postgres for restore..."
obsura_compose "$COMPOSE_FILE" "$GLOBAL_ENV" "$POSTGRES_ENV" "$API_ENV" up -d postgres

echo "Waiting for postgres readiness..."
for _ in {1..30}; do
  if obsura_compose "$COMPOSE_FILE" "$GLOBAL_ENV" "$POSTGRES_ENV" "$API_ENV" exec -T postgres pg_isready -U "$POSTGRES_USER" -d postgres > /dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! obsura_compose "$COMPOSE_FILE" "$GLOBAL_ENV" "$POSTGRES_ENV" "$API_ENV" exec -T postgres pg_isready -U "$POSTGRES_USER" -d postgres > /dev/null 2>&1; then
  echo "Postgres did not become ready in time." >&2
  exit 1
fi

echo "Restoring Obsura storage volume..."
docker run --rm \
  --mount "type=volume,source=$OBSURA_STORAGE_VOLUME,target=/target" \
  --mount "type=bind,source=$BACKUP_DIR_ABS,target=/backup,readonly" \
  alpine:3.20 \
  sh -ec 'find /target -mindepth 1 -maxdepth 1 -exec rm -rf {} + && tar -xzf /backup/obsura-data.tgz -C /target'

echo "Resetting database..."
obsura_compose "$COMPOSE_FILE" "$GLOBAL_ENV" "$POSTGRES_ENV" "$API_ENV" exec -T postgres \
  psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS \"$POSTGRES_DB\";"
obsura_compose "$COMPOSE_FILE" "$GLOBAL_ENV" "$POSTGRES_ENV" "$API_ENV" exec -T postgres \
  psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE \"$POSTGRES_DB\";"

echo "Loading PostgreSQL dump..."
obsura_compose "$COMPOSE_FILE" "$GLOBAL_ENV" "$POSTGRES_ENV" "$API_ENV" exec -T postgres \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 < "$BACKUP_DIR_ABS/postgres.sql"

echo "Re-applying storage permissions..."
obsura_compose "$COMPOSE_FILE" "$GLOBAL_ENV" "$POSTGRES_ENV" "$API_ENV" run --rm --no-deps volume-init

echo "Starting full stack..."
obsura_compose "$COMPOSE_FILE" "$GLOBAL_ENV" "$POSTGRES_ENV" "$API_ENV" up -d

echo "Restore complete."
