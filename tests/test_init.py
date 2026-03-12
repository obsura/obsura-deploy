from __future__ import annotations

from pathlib import Path

import pytest

from obsuractl import config
from obsuractl.commands import init as init_command
from obsuractl.helpers import (
    UserError,
    compose_service_image,
    parse_env_file,
    placeholder_like,
    stack_configured_api_image,
)
from obsuractl.main import build_parser


def make_bootstrap_repo(root: Path) -> Path:
    (root / "compose" / "local").mkdir(parents=True)
    (root / "compose" / "production").mkdir(parents=True)
    (root / "env").mkdir(parents=True)
    (root / "scripts").mkdir(parents=True)
    (root / "README.md").write_text("# test\n", encoding="utf-8")
    compose_text = (
        "services:\n"
        "  volume-init:\n"
        "    image: ghcr.io/obsura/obsura-api:replace-with-release-tag\n"
        "  api:\n"
        "    image: ghcr.io/obsura/obsura-api:replace-with-release-tag\n"
        "  postgres:\n"
        "    image: postgres:17-alpine\n"
    )
    (root / "compose" / "local" / "docker-compose.yaml").write_text(compose_text, encoding="utf-8")
    (root / "compose" / "production" / "docker-compose.yaml").write_text(compose_text, encoding="utf-8")
    (root / "env" / "global.env.example").write_text(
        "OBSURA_API_BIND_ADDRESS=127.0.0.1\n"
        "OBSURA_API_HOST_PORT=8000\n",
        encoding="utf-8",
    )
    (root / "env" / "api.env.example").write_text("OBSURA_API_V1_PREFIX=/api/v1\n", encoding="utf-8")
    (root / "env" / "postgres.env.example").write_text(
        "POSTGRES_DB=obsura\n"
        "POSTGRES_USER=obsura\n"
        "POSTGRES_PASSWORD=change-me-long-random-password\n",
        encoding="utf-8",
    )
    return root


@pytest.fixture(autouse=True)
def reset_runtime_repo_root() -> None:
    config.set_runtime_repo_root(None)
    yield
    config.set_runtime_repo_root(None)


def test_init_quickstart_local_writes_image_and_password(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = make_bootstrap_repo(tmp_path / "obsura-deploy")
    monkeypatch.chdir(repo)
    monkeypatch.setattr(init_command, "interactive_console_available", lambda: False)

    args = build_parser().parse_args(
        ["init", "--quickstart-local", "--image", "ghcr.io/obsura/obsura-api:0.2.0"]
    )
    assert args.handler(args) == 0

    postgres_values = parse_env_file(repo / "env" / "postgres.env")

    local_stack = config.resolve_stack("local")
    assert stack_configured_api_image(local_stack) == "ghcr.io/obsura/obsura-api:0.2.0"
    assert compose_service_image(local_stack.compose_file, "volume-init") == "ghcr.io/obsura/obsura-api:0.2.0"
    assert postgres_values["POSTGRES_PASSWORD"]
    assert not placeholder_like(postgres_values["POSTGRES_PASSWORD"])
    assert len(postgres_values["POSTGRES_PASSWORD"]) == 48


def test_init_interactive_prompt_can_prepare_local_quickstart(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = make_bootstrap_repo(tmp_path / "obsura-deploy")
    monkeypatch.chdir(repo)
    monkeypatch.setattr(init_command, "interactive_console_available", lambda: True)
    answers = iter(["y", "ghcr.io/obsura/obsura-api:0.3.0"])
    monkeypatch.setattr(init_command, "prompt_text", lambda _message: next(answers))

    args = build_parser().parse_args(["init"])
    assert args.handler(args) == 0

    postgres_values = parse_env_file(repo / "env" / "postgres.env")

    local_stack = config.resolve_stack("local")
    assert stack_configured_api_image(local_stack) == "ghcr.io/obsura/obsura-api:0.3.0"
    assert compose_service_image(local_stack.compose_file, "volume-init") == "ghcr.io/obsura/obsura-api:0.3.0"
    assert not placeholder_like(postgres_values["POSTGRES_PASSWORD"])


def test_init_template_only_keeps_placeholder_values(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = make_bootstrap_repo(tmp_path / "obsura-deploy")
    monkeypatch.chdir(repo)
    monkeypatch.setattr(init_command, "interactive_console_available", lambda: True)

    args = build_parser().parse_args(["init", "--template-only"])
    assert args.handler(args) == 0

    postgres_values = parse_env_file(repo / "env" / "postgres.env")

    assert placeholder_like(stack_configured_api_image(config.resolve_stack("local")) or "")
    assert placeholder_like(postgres_values["POSTGRES_PASSWORD"])


def test_init_rejects_image_without_local_quickstart(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = make_bootstrap_repo(tmp_path / "obsura-deploy")
    monkeypatch.chdir(repo)

    args = build_parser().parse_args(["init", "--image", "ghcr.io/obsura/obsura-api:0.4.0"])

    with pytest.raises(UserError):
        args.handler(args)
