from __future__ import annotations

from pathlib import Path

import pytest

from obsuractl import config
from obsuractl.helpers import suggested_init_command


def make_fake_repo(root: Path) -> Path:
    (root / "compose" / "local").mkdir(parents=True)
    (root / "compose" / "production").mkdir(parents=True)
    (root / "env").mkdir(parents=True)
    (root / "scripts").mkdir(parents=True)
    (root / "README.md").write_text("# test\n", encoding="utf-8")
    (root / "compose" / "local" / "docker-compose.yaml").write_text("services: {}\n", encoding="utf-8")
    (root / "compose" / "production" / "docker-compose.yaml").write_text("services: {}\n", encoding="utf-8")
    (root / "env" / "global.env.example").write_text("A=B\n", encoding="utf-8")
    (root / "env" / "api.env.example").write_text("A=B\n", encoding="utf-8")
    (root / "env" / "postgres.env.example").write_text("A=B\n", encoding="utf-8")
    return root


def test_repo_root_is_discovered_from_current_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = make_fake_repo(tmp_path / "obsura-deploy")
    work_dir = repo / "docs"
    work_dir.mkdir()

    config.set_runtime_repo_root(None)
    monkeypatch.chdir(work_dir)

    assert config.repo_root() == repo
    stack = config.resolve_stack("local")
    assert stack.repo_root == repo
    assert stack.compose_file == repo / "compose" / "local" / "docker-compose.yaml"


def test_runtime_repo_root_override_is_used(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = make_fake_repo(tmp_path / "obsura-deploy")
    other_dir = tmp_path / "somewhere-else"
    other_dir.mkdir()

    monkeypatch.chdir(other_dir)
    config.set_runtime_repo_root(repo)

    assert config.repo_root() == repo

    config.set_runtime_repo_root(None)


def test_invalid_runtime_repo_root_is_an_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    bad_root = tmp_path / "not-a-repo"
    bad_root.mkdir()
    monkeypatch.chdir(tmp_path)
    config.set_runtime_repo_root(bad_root)

    with pytest.raises(config.RepoRootError):
        config.repo_root()

    config.set_runtime_repo_root(None)


def test_repo_root_env_var_override_is_used(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = make_fake_repo(tmp_path / "obsura-deploy")
    other_dir = tmp_path / "somewhere-else"
    other_dir.mkdir()

    config.set_runtime_repo_root(None)
    monkeypatch.chdir(other_dir)
    monkeypatch.setenv(config.REPO_ROOT_ENV_VAR, str(repo))

    assert config.repo_root() == repo


def test_suggested_init_command_uses_repo_root_override_when_outside_checkout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = make_fake_repo(tmp_path / "obsura-deploy")
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()

    config.set_runtime_repo_root(repo)
    monkeypatch.chdir(outside_dir)
    stack = config.resolve_stack("local")

    assert suggested_init_command(stack) == f"obsuractl --repo-root {repo} init"

    config.set_runtime_repo_root(None)


def test_suggested_init_command_is_short_inside_checkout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = make_fake_repo(tmp_path / "obsura-deploy")
    docs_dir = repo / "docs"
    docs_dir.mkdir()

    config.set_runtime_repo_root(None)
    monkeypatch.chdir(docs_dir)
    stack = config.resolve_stack("local")

    assert suggested_init_command(stack) == "obsuractl init"
