from __future__ import annotations

import os
import shlex
import shutil
import socket
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

from . import config
from . import ui


class UserError(RuntimeError):
    pass


@dataclass
class DoctorResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    infos: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def format_command(command: Sequence[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(list(command))
    return shlex.join(command)


def run(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    capture_output: bool = False,
    check: bool = True,
    echo: bool = True,
) -> subprocess.CompletedProcess[str]:
    if echo:
        print(ui.command_text(f"$ {format_command(command)}"))
    completed = subprocess.run(
        list(command),
        cwd=str(cwd or config.repo_root()),
        text=True,
        capture_output=capture_output,
        check=False,
    )

    if check and completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        if detail:
            raise UserError(detail)
        raise UserError(f"command failed with exit code {completed.returncode}: {format_command(command)}")

    return completed


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key.strip()] = value
    return values


def merge_env_files(paths: Iterable[Path]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for path in paths:
        merged.update(parse_env_file(path))
    return merged


def stack_env_values(stack: config.StackPaths) -> dict[str, str]:
    existing = [path for path in stack.env_files if path.exists()]
    if not existing:
        return {}
    return merge_env_files(existing)


def compose_command(stack: config.StackPaths, *compose_args: str) -> list[str]:
    command = [
        "docker",
        "compose",
        "--env-file",
        str(stack.global_env),
        "--env-file",
        str(stack.postgres_env),
        "--env-file",
        str(stack.api_env),
        "-f",
        str(stack.compose_file),
    ]
    command.extend(compose_args)
    return command


def script_command(script_name: str, *script_args: str) -> list[str]:
    scripts_dir = config.scripts_dir()
    if os.name == "nt":
        script = scripts_dir / f"{script_name}.ps1"
        command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)]
    else:
        script = scripts_dir / f"{script_name}.sh"
        command = ["bash", str(script)]
    command.extend(script_args)
    return command


def placeholder_like(value: str) -> bool:
    lowered = value.lower()
    markers = (
        "replace-with",
        "change-me",
        "example",
        "placeholder",
    )
    return any(marker in lowered for marker in markers)


def require_real_image_reference(image_ref: str, *, label: str = "image reference") -> None:
    if not image_ref or placeholder_like(image_ref):
        raise UserError(f"{label} must be a real published tag or digest, not a placeholder value")


def port_check(bind_address: str, port_text: str) -> tuple[bool, str]:
    try:
        port = int(port_text)
    except ValueError:
        return False, f"OBSURA_API_HOST_PORT must be an integer, got {port_text!r}."

    if port < 1 or port > 65535:
        return False, f"OBSURA_API_HOST_PORT must be between 1 and 65535, got {port}."

    try:
        family = socket.AF_INET6 if ":" in bind_address else socket.AF_INET
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((bind_address, port))
    except OSError:
        return False, f"{bind_address}:{port} is already in use or cannot be bound."

    return True, f"{bind_address}:{port} is available."


def collect_stack_access_result(environment: str) -> DoctorResult:
    stack = config.resolve_stack(environment)
    result = DoctorResult()

    docker_path = shutil.which("docker")
    if not docker_path:
        result.errors.append("Docker was not found on PATH.")
    else:
        result.infos.append(f"Docker executable found at {docker_path}.")
        compose_version = run(["docker", "compose", "version"], capture_output=True, check=False, echo=False)
        if compose_version.returncode != 0:
            result.errors.append("Docker Compose v2 plugin is required.")
        else:
            version_text = (compose_version.stdout or compose_version.stderr).strip()
            result.infos.append(version_text or "Docker Compose is available.")

    if not stack.compose_file.exists():
        result.errors.append(f"Compose file missing: {stack.compose_file}")
    else:
        result.infos.append(f"Compose file found: {stack.compose_file}")

    missing_env_files = [path for path in stack.env_files if not path.exists()]
    if missing_env_files:
        for missing in missing_env_files:
            result.errors.append(f"Missing env file: {missing}")
        result.warnings.append(
            "Run "
            f"`{suggested_init_command(stack)}` "
            "to create env files from the examples."
        )
        return result

    if docker_path and stack.compose_file.exists():
        compose_config = run(compose_command(stack, "config"), capture_output=True, check=False, echo=False)
        if compose_config.returncode != 0:
            detail = (compose_config.stderr or compose_config.stdout).strip()
            result.errors.append(f"docker compose config failed: {detail}")
        else:
            result.infos.append("docker compose config completed successfully.")

    return result


def collect_doctor_result(environment: str) -> DoctorResult:
    stack = config.resolve_stack(environment)
    result = collect_stack_access_result(environment)
    if result.errors:
        return result

    merged = merge_env_files(stack.env_files)

    required_vars = (
        "OBSURA_API_IMAGE",
        "OBSURA_API_BIND_ADDRESS",
        "OBSURA_API_HOST_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    )

    for key in required_vars:
        if not merged.get(key):
            result.errors.append(f"Required variable is missing or empty: {key}")

    api_image = merged.get("OBSURA_API_IMAGE", "")
    if api_image and placeholder_like(api_image):
        result.errors.append("OBSURA_API_IMAGE still contains a placeholder value.")
    elif api_image and environment == "production" and "@sha256:" not in api_image:
        result.warnings.append("Production is using a tag instead of an immutable digest for OBSURA_API_IMAGE.")

    postgres_password = merged.get("POSTGRES_PASSWORD", "")
    if postgres_password and placeholder_like(postgres_password):
        result.errors.append("POSTGRES_PASSWORD still contains a placeholder value.")
    elif postgres_password and len(postgres_password) < 16:
        result.warnings.append("POSTGRES_PASSWORD is shorter than 16 characters.")

    bind_address = merged.get("OBSURA_API_BIND_ADDRESS", "")
    if bind_address and environment == "production" and bind_address not in {"127.0.0.1", "::1", "localhost"}:
        result.warnings.append("Production API binding is not localhost-only.")

    if bind_address and merged.get("OBSURA_API_HOST_PORT"):
        ok, message = port_check(bind_address, merged["OBSURA_API_HOST_PORT"])
        if ok:
            result.infos.append(message)
        else:
            result.warnings.append(message)

    return result


def print_doctor_result(result: DoctorResult, *, include_infos: bool = True) -> None:
    if include_infos:
        for line in result.infos:
            print(f"{ui.status_label('ok')} {line}")
    for line in result.warnings:
        print(f"{ui.status_label('warn')} {line}")
    for line in result.errors:
        print(f"{ui.status_label('error')} {line}")


def print_stack_context(
    stack: config.StackPaths,
    *,
    action: str,
    services: Sequence[str] | None = None,
    backup_path: str | None = None,
    target_image: str | None = None,
) -> None:
    values = stack_env_values(stack)
    current_image = values.get("OBSURA_API_IMAGE")
    bind_address = values.get("OBSURA_API_BIND_ADDRESS")
    host_port = values.get("OBSURA_API_HOST_PORT")

    print(f"{ui.key_label('Action:')} {action}")
    print(f"{ui.key_label('Repository root:')} {stack.repo_root}")
    print(f"{ui.key_label('Environment:')} {stack.environment}")
    print(f"{ui.key_label('Compose file:')} {stack.compose_file}")
    print(ui.key_label("Env files:"))
    for path in stack.env_files:
        print(f"  - {path}")
    if current_image:
        print(f"{ui.key_label('Configured API image:')} {current_image}")
    if target_image:
        print(f"{ui.key_label('Requested API image:')} {target_image}")
    if bind_address and host_port:
        print(f"{ui.key_label('Published API target:')} {bind_address}:{host_port}")
    if services:
        print(f"{ui.key_label('Services:')} {', '.join(services)}")
    if backup_path:
        print(f"{ui.key_label('Backup path:')} {backup_path}")


def print_compose_manual_equivalent(stack: config.StackPaths, *compose_args: str) -> None:
    command = compose_command(stack, *compose_args)
    print(ui.key_label("Manual equivalent:"))
    print(f"  {ui.command_text(format_command(command))}")


def print_script_manual_equivalent(script_name: str, *script_args: str) -> None:
    command = script_command(script_name, *script_args)
    print(ui.key_label("Wrapped command:"))
    print(f"  {ui.command_text(format_command(command))}")


def print_doctor_target(environment: str) -> None:
    stack = config.resolve_stack(environment)
    print(f"{ui.key_label('Repository root:')} {stack.repo_root}")
    print(f"{ui.key_label('Doctor target:')} {stack.environment}")
    print(f"{ui.key_label('Compose file:')} {stack.compose_file}")
    print(ui.key_label("Expected env files:"))
    for path in stack.env_files:
        print(f"  - {path}")


def ensure_stack_ready(environment: str) -> config.StackPaths:
    stack = config.resolve_stack(environment)
    result = collect_doctor_result(environment)
    print_doctor_result(result, include_infos=False)
    if not result.ok:
        missing_env_files = [path for path in stack.env_files if not path.exists()]
        if missing_env_files:
            raise UserError(
                f"missing env files for {environment}; run `{suggested_init_command(stack)}` and then edit "
                f"`{stack.global_env}` and `{stack.postgres_env}`"
            )
        raise UserError(f"doctor checks failed for {environment}")
    return stack


def ensure_stack_access(environment: str) -> config.StackPaths:
    stack = config.resolve_stack(environment)
    result = collect_stack_access_result(environment)
    print_doctor_result(result, include_infos=False)
    if not result.ok:
        missing_env_files = [path for path in stack.env_files if not path.exists()]
        if missing_env_files:
            raise UserError(
                f"missing env files for {environment}; run `{suggested_init_command(stack)}` before retrying"
            )
        raise UserError(f"stack access checks failed for {environment}")
    return stack


def suggested_init_command(stack: config.StackPaths) -> str:
    current_dir = Path.cwd().resolve()
    if current_dir == stack.repo_root or stack.repo_root in current_dir.parents:
        return "obsuractl init"
    return f"obsuractl --repo-root {stack.repo_root} init"
