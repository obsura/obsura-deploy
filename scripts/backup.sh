#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT="${1:-production}"
OUTPUT_DIR="${2:-}"

case "$ENVIRONMENT" in
  local|production) ;;
  *)
    echo "Usage: $0 [local|production] [output-dir]" >&2
    exit 1
    ;;
esac

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

timestamp="$(date +"%Y%m%d-%H%M%S")"
if [[ -z "$OUTPUT_DIR" ]]; then
  backup_root="${BACKUP_ROOT:-$ROOT_DIR/backups}"
  OUTPUT_DIR="$backup_root/$ENVIRONMENT/$timestamp"
fi

mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR_ABS="$(cd "$OUTPUT_DIR" && pwd)"

echo "Ensuring postgres is running..."
compose up -d postgres

echo "Waiting for postgres readiness..."
for _ in {1..30}; do
  if compose exec -T postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! compose exec -T postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null 2>&1; then
  echo "Postgres did not become ready in time." >&2
  exit 1
fi

echo "Writing PostgreSQL logical backup..."
compose exec -T postgres pg_dump \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges > "$OUTPUT_DIR_ABS/postgres.sql"

echo "Archiving Obsura storage volume..."
docker run --rm \
  --mount "type=volume,source=${OBSURA_STORAGE_VOLUME:-obsura-storage},target=/source,readonly" \
  --mount "type=bind,source=$OUTPUT_DIR_ABS,target=/backup" \
  alpine:3.20 \
  sh -ec 'cd /source && tar -czf /backup/obsura-data.tgz .'

printf 'environment=%s\ncreated_at=%s\napi_image=%s\n' \
  "$ENVIRONMENT" \
  "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
  "${OBSURA_API_IMAGE:-unknown}" > "$OUTPUT_DIR_ABS/metadata.txt"

echo "Backup created at $OUTPUT_DIR_ABS"
