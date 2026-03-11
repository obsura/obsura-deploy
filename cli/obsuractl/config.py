from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

VALID_ENVIRONMENTS = ("local", "production")
REPO_ROOT_ENV_VAR = "OBSURA_DEPLOY_ROOT"
SOURCE_TREE_ROOT = Path(__file__).resolve().parents[2]

REPO_MARKERS = (
    Path("README.md"),
    Path("compose") / "local" / "docker-compose.yaml",
    Path("compose") / "production" / "docker-compose.yaml",
    Path("env") / "global.env.example",
    Path("env") / "api.env.example",
    Path("env") / "postgres.env.example",
    Path("scripts"),
)

_runtime_repo_root: Path | None = None

EXAMPLE_ENV_FILES = {
    "global.env.example": "global.env",
    "api.env.example": "api.env",
    "postgres.env.example": "postgres.env",
}


class RepoRootError(RuntimeError):
    pass


@dataclass(frozen=True)
class StackPaths:
    repo_root: Path
    environment: str
    compose_file: Path
    global_env: Path
    api_env: Path
    postgres_env: Path
    scripts_dir: Path

    @property
    def env_files(self) -> tuple[Path, Path, Path]:
        return (self.global_env, self.api_env, self.postgres_env)


def set_runtime_repo_root(repo_root: str | os.PathLike[str] | None) -> None:
    global _runtime_repo_root
    if repo_root is None:
        _runtime_repo_root = None
        return

    _runtime_repo_root = Path(repo_root).expanduser().resolve()


def is_repo_root(path: Path) -> bool:
    return all((path / marker).exists() for marker in REPO_MARKERS)


def candidate_repo_roots() -> list[Path]:
    candidates: list[Path] = []
    current_working_dir = Path.cwd().resolve()
    for current in (current_working_dir, *current_working_dir.parents):
        candidates.append(current)

    executable_path = Path(sys.executable).resolve()
    candidates.append(executable_path.parent)
    candidates.extend(executable_path.parent.parents)

    if is_repo_root(SOURCE_TREE_ROOT):
        candidates.append(SOURCE_TREE_ROOT)

    seen: set[Path] = set()
    ordered: list[Path] = []
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            ordered.append(candidate)
    return ordered


def repo_root() -> Path:
    if _runtime_repo_root is not None:
        if is_repo_root(_runtime_repo_root):
            return _runtime_repo_root
        raise RepoRootError(f"--repo-root does not point to an obsura-deploy checkout: {_runtime_repo_root}")

    env_repo_root = os.environ.get(REPO_ROOT_ENV_VAR)
    if env_repo_root:
        explicit_env_root = Path(env_repo_root).expanduser().resolve()
        if is_repo_root(explicit_env_root):
            return explicit_env_root
        raise RepoRootError(
            f"{REPO_ROOT_ENV_VAR} does not point to an obsura-deploy checkout: {explicit_env_root}"
        )

    for candidate in candidate_repo_roots():
        if is_repo_root(candidate):
            return candidate

    searched = "\n".join(f"  - {candidate}" for candidate in candidate_repo_roots())
    raise RepoRootError(
        "Unable to locate an obsura-deploy repository checkout. "
        "Run obsuractl from inside the repository, pass --repo-root <path>, "
        f"or set {REPO_ROOT_ENV_VAR}.\nSearched:\n{searched}"
    )


def env_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "env"


def compose_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "compose"


def scripts_dir(root: Path | None = None) -> Path:
    return (root or repo_root()) / "scripts"


def resolve_stack(environment: str) -> StackPaths:
    if environment not in VALID_ENVIRONMENTS:
        raise ValueError(f"unsupported environment: {environment}")

    root = repo_root()
    return StackPaths(
        repo_root=root,
        environment=environment,
        compose_file=compose_dir(root) / environment / "docker-compose.yaml",
        global_env=env_dir(root) / "global.env",
        api_env=env_dir(root) / "api.env",
        postgres_env=env_dir(root) / "postgres.env",
        scripts_dir=scripts_dir(root),
    )
