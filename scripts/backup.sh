#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT="${1:-production}"
OUTPUT_DIR="${2:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/common.sh"

obsura_require_environment "$ENVIRONMENT"
obsura_require_docker

ROOT_DIR="$(obsura_repo_root "${BASH_SOURCE[0]}")"
COMPOSE_FILE="$ROOT_DIR/compose/$ENVIRONMENT/docker-compose.yaml"
GLOBAL_ENV="$ROOT_DIR/env/global.env"
API_ENV="$ROOT_DIR/env/api.env"
POSTGRES_ENV="$ROOT_DIR/env/postgres.env"

obsura_require_files "$COMPOSE_FILE" "$GLOBAL_ENV" "$API_ENV" "$POSTGRES_ENV"

POSTGRES_USER="$(obsura_env_value "$POSTGRES_ENV" POSTGRES_USER || true)"
POSTGRES_DB="$(obsura_env_value "$POSTGRES_ENV" POSTGRES_DB || true)"
POSTGRES_PASSWORD="$(obsura_env_value "$POSTGRES_ENV" POSTGRES_PASSWORD || true)"
OBSURA_STORAGE_VOLUME="$(obsura_env_value "$GLOBAL_ENV" OBSURA_STORAGE_VOLUME || true)"
BACKUP_ROOT="$(obsura_env_value "$GLOBAL_ENV" BACKUP_ROOT || true)"
OBSURA_API_IMAGE="$(obsura_env_value "$GLOBAL_ENV" OBSURA_API_IMAGE || true)"

if [[ -z "$POSTGRES_USER" || -z "$POSTGRES_DB" || -z "$POSTGRES_PASSWORD" ]]; then
  echo "POSTGRES_USER, POSTGRES_DB, and POSTGRES_PASSWORD must be set in env/postgres.env." >&2
  exit 1
fi

if [[ -z "$OBSURA_STORAGE_VOLUME" ]]; then
  OBSURA_STORAGE_VOLUME="obsura-storage"
fi

if [[ -z "$BACKUP_ROOT" ]]; then
  BACKUP_ROOT="./backups"
fi

if [[ -z "$OUTPUT_DIR" ]]; then
  timestamp="$(date +"%Y%m%d-%H%M%S")"
  if [[ "$BACKUP_ROOT" = /* ]]; then
    backup_base="$BACKUP_ROOT"
  else
    backup_base="$ROOT_DIR/${BACKUP_ROOT#./}"
  fi
  OUTPUT_DIR="$backup_base/$ENVIRONMENT/$timestamp"
fi

mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR_ABS="$(cd "$OUTPUT_DIR" && pwd)"

obsura_print_stack_context "$ENVIRONMENT" "$COMPOSE_FILE" "$GLOBAL_ENV" "$API_ENV" "$POSTGRES_ENV" "$OBSURA_API_IMAGE"
echo "Backup output: $OUTPUT_DIR_ABS"
echo "Storage volume: $OBSURA_STORAGE_VOLUME"

obsura_require_docker_volume "$OBSURA_STORAGE_VOLUME"

echo "Ensuring postgres is running..."
obsura_compose "$COMPOSE_FILE" "$GLOBAL_ENV" "$POSTGRES_ENV" "$API_ENV" up -d postgres

echo "Waiting for postgres readiness..."
for _ in {1..30}; do
  if obsura_compose "$COMPOSE_FILE" "$GLOBAL_ENV" "$POSTGRES_ENV" "$API_ENV" exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! obsura_compose "$COMPOSE_FILE" "$GLOBAL_ENV" "$POSTGRES_ENV" "$API_ENV" exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null 2>&1; then
  echo "Postgres did not become ready in time." >&2
  exit 1
fi

echo "Writing PostgreSQL logical backup..."
obsura_compose "$COMPOSE_FILE" "$GLOBAL_ENV" "$POSTGRES_ENV" "$API_ENV" exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres pg_dump \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges > "$OUTPUT_DIR_ABS/postgres.sql"

echo "Archiving Obsura storage volume..."
docker run --rm \
  --mount "type=volume,source=$OBSURA_STORAGE_VOLUME,target=/source,readonly" \
  --mount "type=bind,source=$OUTPUT_DIR_ABS,target=/backup" \
  alpine:3.20 \
  sh -ec 'cd /source && tar -czf /backup/obsura-data.tgz .'

printf 'environment=%s\ncreated_at=%s\napi_image=%s\nstorage_volume=%s\n' \
  "$ENVIRONMENT" \
  "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
  "${OBSURA_API_IMAGE:-unknown}" \
  "$OBSURA_STORAGE_VOLUME" > "$OUTPUT_DIR_ABS/metadata.txt"

printf 'postgres_db=%s\npostgres_user=%s\ncompose_file=%s\n' \
  "$POSTGRES_DB" \
  "$POSTGRES_USER" \
  "$COMPOSE_FILE" >> "$OUTPUT_DIR_ABS/metadata.txt"

echo "Backup created at $OUTPUT_DIR_ABS"
