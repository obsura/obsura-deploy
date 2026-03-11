from __future__ import annotations

import re
import tomllib
from pathlib import Path

from obsuractl.version import __version__


def test_version_is_semver_core() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)


def test_pyproject_uses_version_module_as_source_of_truth() -> None:
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    assert pyproject["project"]["dynamic"] == ["version"]
    assert pyproject["tool"]["setuptools"]["dynamic"]["version"]["attr"] == "obsuractl.version.__version__"
