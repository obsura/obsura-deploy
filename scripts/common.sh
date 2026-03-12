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
  if [[ -z "$image_ref" || "$image_ref" == *"replace-with-"* || "$image_ref" == *"change-me"* || "$image_ref" == *"placeholder"* || "$image_ref" == *"example"* ]]; then
    echo "Set the api image in the compose file to a real published tag or digest before continuing." >&2
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

obsura_compose_service_image() {
  local compose_file="$1"
  local service="$2"

  awk -v service="$service" '
    $0 ~ ("^  " service ":$") { in_target = 1; next }
    in_target && $0 ~ "^  [A-Za-z0-9_-]+:$" { exit }
    in_target && $0 ~ "^    image:[[:space:]]*" {
      sub("^    image:[[:space:]]*", "", $0)
      print $0
      exit
    }
  ' "$compose_file"
}

obsura_set_compose_service_image() {
  local compose_file="$1"
  local service="$2"
  local image_ref="$3"
  local temp_file

  temp_file="${compose_file}.tmp"
  awk -v service="$service" -v image_ref="$image_ref" '
    $0 ~ ("^  " service ":$") {
      in_target = 1
      print
      next
    }
    in_target && $0 ~ "^  [A-Za-z0-9_-]+:$" {
      in_target = 0
    }
    in_target && $0 ~ "^    image:[[:space:]]*" {
      print "    image: " image_ref
      updated = 1
      next
    }
    { print }
    END {
      if (!updated) {
        exit 2
      }
    }
  ' "$compose_file" > "$temp_file" || {
    rm -f "$temp_file"
    echo "Failed to update image for service '$service' in $compose_file" >&2
    exit 1
  }

  mv "$temp_file" "$compose_file"
}

obsura_stack_api_image() {
  local compose_file="$1"
  obsura_compose_service_image "$compose_file" api
}

obsura_set_stack_api_image() {
  local compose_file="$1"
  local image_ref="$2"
  obsura_set_compose_service_image "$compose_file" volume-init "$image_ref"
  obsura_set_compose_service_image "$compose_file" api "$image_ref"
}

obsura_compose_service_container_id() {
  local compose_file="$1"
  local global_env="$2"
  local postgres_env="$3"
  local api_env="$4"
  local service="$5"

  obsura_compose "$compose_file" "$global_env" "$postgres_env" "$api_env" ps -q "$service" | tr -d '\r'
}

obsura_wait_for_service_health() {
  local compose_file="$1"
  local global_env="$2"
  local postgres_env="$3"
  local api_env="$4"
  local service="$5"
  local timeout_seconds="${6:-180}"
  local elapsed=0
  local interval=2
  local container_id status health

  while (( elapsed < timeout_seconds )); do
    container_id="$(obsura_compose_service_container_id "$compose_file" "$global_env" "$postgres_env" "$api_env" "$service")"
    if [[ -n "$container_id" ]]; then
      status="$(docker inspect --format '{{.State.Status}}' "$container_id" 2>/dev/null || true)"
      health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container_id" 2>/dev/null || true)"
      if [[ "$health" == "healthy" || ( "$health" == "none" && "$status" == "running" ) ]]; then
        return 0
      fi
    fi
    sleep "$interval"
    elapsed=$(( elapsed + interval ))
  done

  return 1
}

obsura_print_running_service_state() {
  local compose_file="$1"
  local global_env="$2"
  local postgres_env="$3"
  local api_env="$4"
  local service="${5:-api}"
  local container_id config_image image_id state health

  container_id="$(obsura_compose_service_container_id "$compose_file" "$global_env" "$postgres_env" "$api_env" "$service")"
  if [[ -z "$container_id" ]]; then
    echo "Service '$service' does not currently have a container."
    return 1
  fi

  config_image="$(docker inspect --format '{{.Config.Image}}' "$container_id" 2>/dev/null || true)"
  image_id="$(docker inspect --format '{{.Image}}' "$container_id" 2>/dev/null || true)"
  state="$(docker inspect --format '{{.State.Status}}' "$container_id" 2>/dev/null || true)"
  health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container_id" 2>/dev/null || true)"

  echo "Service: $service"
  echo "  Container id: $container_id"
  echo "  State: ${state:-unknown}"
  echo "  Health: ${health:-unknown}"
  if [[ -n "$config_image" ]]; then
    echo "  Configured image: $config_image"
  fi
  if [[ -n "$image_id" ]]; then
    echo "  Image id: $image_id"
  fi
}

obsura_require_docker_volume() {
  local volume_name="$1"
  if ! docker volume inspect "$volume_name" > /dev/null 2>&1; then
    echo "Required Docker volume not found: $volume_name" >&2
    exit 1
  fi
}

obsura_ensure_docker_volume() {
  local volume_name="$1"
  if ! docker volume inspect "$volume_name" > /dev/null 2>&1; then
    echo "Creating Docker volume: $volume_name"
    docker volume create "$volume_name" > /dev/null
  fi
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
