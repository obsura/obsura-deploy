#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT="${1:-local}"

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

OBSURA_API_IMAGE="$(obsura_stack_api_image "$COMPOSE_FILE" || true)"
obsura_require_real_image_reference "$OBSURA_API_IMAGE"

obsura_print_stack_context "$ENVIRONMENT" "$COMPOSE_FILE" "$GLOBAL_ENV" "$API_ENV" "$POSTGRES_ENV" "$OBSURA_API_IMAGE"

echo "Validating compose configuration for $ENVIRONMENT..."
obsura_compose "$COMPOSE_FILE" "$GLOBAL_ENV" "$POSTGRES_ENV" "$API_ENV" config > /dev/null

echo "Pulling images..."
obsura_compose "$COMPOSE_FILE" "$GLOBAL_ENV" "$POSTGRES_ENV" "$API_ENV" pull

echo "Starting stack..."
obsura_compose "$COMPOSE_FILE" "$GLOBAL_ENV" "$POSTGRES_ENV" "$API_ENV" up -d --remove-orphans

echo "Waiting for API health..."
if ! obsura_wait_for_service_health "$COMPOSE_FILE" "$GLOBAL_ENV" "$POSTGRES_ENV" "$API_ENV" api 180; then
  echo "API did not become healthy within 180 seconds. Recent logs:" >&2
  obsura_compose "$COMPOSE_FILE" "$GLOBAL_ENV" "$POSTGRES_ENV" "$API_ENV" logs --tail 200 api postgres || true
  exit 1
fi

echo "Current service state:"
obsura_compose "$COMPOSE_FILE" "$GLOBAL_ENV" "$POSTGRES_ENV" "$API_ENV" ps

echo "Running API container:"
obsura_print_running_service_state "$COMPOSE_FILE" "$GLOBAL_ENV" "$POSTGRES_ENV" "$API_ENV" api
