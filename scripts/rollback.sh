#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT="${1:-}"
TARGET_IMAGE="${2:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/common.sh"

if [[ -z "$ENVIRONMENT" || -z "$TARGET_IMAGE" ]]; then
  echo "Usage: $0 <local|production> <published-tag-or-digest>" >&2
  exit 1
fi

obsura_require_environment "$ENVIRONMENT"
obsura_require_docker
obsura_require_real_image_reference "$TARGET_IMAGE"

ROOT_DIR="$(obsura_repo_root "${BASH_SOURCE[0]}")"
COMPOSE_FILE="$ROOT_DIR/compose/$ENVIRONMENT/docker-compose.yaml"
GLOBAL_ENV="$ROOT_DIR/env/global.env"
API_ENV="$ROOT_DIR/env/api.env"
POSTGRES_ENV="$ROOT_DIR/env/postgres.env"

obsura_require_files "$COMPOSE_FILE" "$GLOBAL_ENV" "$API_ENV" "$POSTGRES_ENV"

CURRENT_IMAGE="$(obsura_env_value "$GLOBAL_ENV" OBSURA_API_IMAGE || true)"
ROLLBACK_UPDATED="0"

restore_original_image() {
  if [[ "$ROLLBACK_UPDATED" == "1" && -n "$CURRENT_IMAGE" ]]; then
    echo "Rollback failed. Restoring OBSURA_API_IMAGE in $GLOBAL_ENV back to $CURRENT_IMAGE..." >&2
    obsura_set_env_value "$GLOBAL_ENV" OBSURA_API_IMAGE "$CURRENT_IMAGE"
  fi
}

trap restore_original_image ERR

obsura_print_stack_context "$ENVIRONMENT" "$COMPOSE_FILE" "$GLOBAL_ENV" "$API_ENV" "$POSTGRES_ENV" "$CURRENT_IMAGE"
echo "Target rollback image: $TARGET_IMAGE"
echo "Updating OBSURA_API_IMAGE in $GLOBAL_ENV..."
obsura_set_env_value "$GLOBAL_ENV" OBSURA_API_IMAGE "$TARGET_IMAGE"
ROLLBACK_UPDATED="1"

echo "Recreating services with the rollback image..."
bash "$SCRIPT_DIR/update.sh" "$ENVIRONMENT"
trap - ERR
echo "Rollback complete."
