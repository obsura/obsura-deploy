#!/usr/bin/env bash
set -euo pipefail

obsura_repo_root() {
  local script_path="$1"
  local script_dir
  script_dir="$(cd "$(dirname "$script_path")" && pwd)"
  cd "$script_dir/.." && pwd
}

obsura_require_environment() {
  local environment="$1"
  case "$environment" in
    local|production) ;;
    *)
      echo "Unsupported environment: $environment" >&2
      echo "Expected one of: local, production" >&2
      exit 1
      ;;
  esac
}

obsura_require_command() {
  local command_name="$1"
  if ! command -v "$command_name" > /dev/null 2>&1; then
    echo "Required command not found: $command_name" >&2
    exit 1
  fi
}

obsura_require_docker() {
  obsura_require_command docker
  if ! docker compose version > /dev/null 2>&1; then
    echo "Docker Compose v2 plugin is required." >&2
    exit 1
  fi
}

obsura_require_files() {
  local file
  for file in "$@"; do
    if [[ ! -f "$file" ]]; then
      echo "Missing required file: $file" >&2
      exit 1
    fi
  done
}

obsura_env_value() {
  local file="$1"
  local key="$2"
  local line value

  line="$(grep -E "^${key}=" "$file" | tail -n 1 || true)"
  if [[ -z "$line" ]]; then
    return 1
  fi

  value="${line#*=}"
  if [[ "$value" == \"*\" && "$value" == *\" ]]; then
    value="${value:1:-1}"
  elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
    value="${value:1:-1}"
  fi

  printf '%s\n' "$value"
}

obsura_require_real_image_reference() {
  local image_ref="$1"
  if [[ -z "$image_ref" || "$image_ref" == *"replace-with-"* ]]; then
    echo "Set OBSURA_API_IMAGE in env/global.env to a real published tag or digest before continuing." >&2
    exit 1
  fi
}

obsura_require_confirmation() {
  local confirmed="${1:-}"
  if [[ "$confirmed" != "--yes" ]]; then
    echo "This action is destructive. Re-run with --yes after you confirm the target backup set and environment." >&2
    exit 1
  fi
}

obsura_print_stack_context() {
  local environment="$1"
  local compose_file="$2"
  local global_env="$3"
  local api_env="$4"
  local postgres_env="$5"
  local image_ref="${6:-}"

  echo "Environment: $environment"
  echo "Compose file: $compose_file"
  echo "Env files:"
  echo "  - $global_env"
  echo "  - $api_env"
  echo "  - $postgres_env"
  if [[ -n "$image_ref" ]]; then
    echo "API image: $image_ref"
  fi
}

obsura_set_env_value() {
  local file="$1"
  local key="$2"
  local value="$3"
  local temp_file

  temp_file="${file}.tmp"
  awk -v key="$key" -v value="$value" '
    BEGIN { updated = 0 }
    $0 ~ ("^" key "=") { print key "=" value; updated = 1; next }
    { print }
    END { if (!updated) print key "=" value }
  ' "$file" > "$temp_file"

  mv "$temp_file" "$file"
}

obsura_compose() {
  local compose_file="$1"
  local global_env="$2"
  local postgres_env="$3"
  local api_env="$4"
  shift 4

  docker compose \
    --env-file "$global_env" \
    --env-file "$postgres_env" \
    --env-file "$api_env" \
    -f "$compose_file" \
    "$@"
}
