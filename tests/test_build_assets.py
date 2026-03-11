from __future__ import annotations

from pathlib import Path

from scripts.build_obsuractl_binary import create_windows_icon, create_windows_version_file, sorted_icon_sizes
from scripts.read_obsuractl_version import read_version


def test_icon_asset_sizes_are_detected() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    pngs = sorted((repo_root / "cli" / "assets").glob("obsura-icon-*.png"))

    sizes = sorted_icon_sizes(pngs)

    assert sizes == [16, 32, 57, 60, 70, 72, 76, 96]


def test_windows_icon_is_generated_from_assets(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]

    icon_path = create_windows_icon(repo_root, tmp_path)

    assert icon_path.exists()
    assert icon_path.suffix == ".ico"


def test_windows_version_file_uses_repo_version_source(tmp_path: Path) -> None:
    version_file = create_windows_version_file(tmp_path, "v0.1.0")
    contents = version_file.read_text(encoding="utf-8")

    assert read_version() in contents
    assert "obsuractl operator CLI" in contents
    assert "ProductVersion', 'v0.1.0'" in contents
