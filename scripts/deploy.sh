#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT="${1:-local}"

case "$ENVIRONMENT" in
  local|production) ;;
  *)
    echo "Usage: $0 [local|production]" >&2
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

if [[ -z "${OBSURA_API_IMAGE:-}" || "${OBSURA_API_IMAGE}" == *"replace-with-"* ]]; then
  echo "Set OBSURA_API_IMAGE in env/global.env to a published tag or digest before deploying." >&2
  exit 1
fi

compose() {
  docker compose \
    --env-file "$GLOBAL_ENV" \
    --env-file "$POSTGRES_ENV" \
    --env-file "$API_ENV" \
    -f "$COMPOSE_FILE" \
    "$@"
}

echo "Validating compose configuration for $ENVIRONMENT..."
compose config > /dev/null

echo "Pulling images..."
compose pull

echo "Starting stack..."
compose up -d --remove-orphans

echo "Current service state:"
compose ps
