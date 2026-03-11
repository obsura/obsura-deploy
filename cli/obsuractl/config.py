from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

VALID_ENVIRONMENTS = ("local", "production")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_DIR = PROJECT_ROOT / "env"
COMPOSE_DIR = PROJECT_ROOT / "compose"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

EXAMPLE_ENV_FILES = {
    "global.env.example": "global.env",
    "api.env.example": "api.env",
    "postgres.env.example": "postgres.env",
}


@dataclass(frozen=True)
class StackPaths:
    environment: str
    compose_file: Path
    global_env: Path
    api_env: Path
    postgres_env: Path

    @property
    def env_files(self) -> tuple[Path, Path, Path]:
        return (self.global_env, self.api_env, self.postgres_env)


def resolve_stack(environment: str) -> StackPaths:
    if environment not in VALID_ENVIRONMENTS:
        raise ValueError(f"unsupported environment: {environment}")

    return StackPaths(
        environment=environment,
        compose_file=COMPOSE_DIR / environment / "docker-compose.yaml",
        global_env=ENV_DIR / "global.env",
        api_env=ENV_DIR / "api.env",
        postgres_env=ENV_DIR / "postgres.env",
    )
