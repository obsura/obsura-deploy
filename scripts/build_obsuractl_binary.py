from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

try:
    from scripts.read_obsuractl_version import read_version
except ModuleNotFoundError:
    from read_obsuractl_version import read_version


def asset_dir(repo_root: Path) -> Path:
    return repo_root / "cli" / "assets"


def icon_pngs(repo_root: Path) -> list[Path]:
    assets = asset_dir(repo_root)
    pngs = sorted(assets.glob("obsura-icon-*.png"))
    if not pngs:
        raise FileNotFoundError(f"No icon PNG assets found under {assets}")
    return pngs


def sorted_icon_sizes(pngs: list[Path]) -> list[int]:
    sizes: list[int] = []
    for png in pngs:
        match = re.search(r"obsura-icon-(\d+)\.png$", png.name)
        if match:
            sizes.append(int(match.group(1)))

    if not sizes:
        raise ValueError("Unable to determine icon sizes from asset filenames.")

    return sorted(set(sizes))


def create_windows_icon(repo_root: Path, build_dir: Path) -> Path:
    try:
        from PIL import Image
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Pillow is required to generate the Windows obsuractl icon. "
            'Install build dependencies with `python -m pip install -e ".[build]"`.'
        ) from exc

    pngs = icon_pngs(repo_root)
    sizes = sorted_icon_sizes(pngs)
    largest_png = asset_dir(repo_root) / f"obsura-icon-{sizes[-1]}.png"
    icon_path = build_dir / "windows" / "obsuractl.ico"
    icon_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(largest_png) as image:
        square_image = image.convert("RGBA")
        square_sizes = [(size, size) for size in sizes]
        square_image.save(icon_path, format="ICO", sizes=square_sizes)

    return icon_path


def windows_version_tuple(version: str) -> tuple[int, int, int, int]:
    major, minor, patch = version.split(".")
    return int(major), int(minor), int(patch), 0


def create_windows_version_file(build_dir: Path, version_label: str) -> Path:
    version = read_version()
    version_tuple = windows_version_tuple(version)
    version_file = build_dir / "windows" / "version_info.txt"
    version_file.parent.mkdir(parents=True, exist_ok=True)
    version_file.write_text(
        "\n".join(
            [
                "# UTF-8",
                "VSVersionInfo(",
                "  ffi=FixedFileInfo(",
                f"    filevers={version_tuple},",
                f"    prodvers={version_tuple},",
                "    mask=0x3F,",
                "    flags=0x0,",
                "    OS=0x40004,",
                "    fileType=0x1,",
                "    subtype=0x0,",
                "    date=(0, 0)",
                "  ),",
                "  kids=[",
                "    StringFileInfo([",
                "      StringTable(",
                "        '040904B0',",
                "        [",
                "          StringStruct('CompanyName', 'Obsura'),",
                "          StringStruct('FileDescription', 'obsuractl operator CLI'),",
                f"          StringStruct('FileVersion', '{version_label}'),",
                "          StringStruct('InternalName', 'obsuractl'),",
                "          StringStruct('OriginalFilename', 'obsuractl.exe'),",
                "          StringStruct('ProductName', 'obsuractl'),",
                f"          StringStruct('ProductVersion', '{version_label}')",
                "        ]",
                "      )",
                "    ]),",
                "    VarFileInfo([VarStruct('Translation', [1033, 1200])])",
                "  ]",
                ")",
            ]
        ),
        encoding="utf-8",
    )
    return version_file


def build_binary(version_label: str, target_os: str, target_arch: str, output_dir: Path) -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    build_dir = repo_root / "build"
    dist_dir = repo_root / "dist"
    spec_dir = build_dir / "pyinstaller-spec"

    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir

    if sys.platform.startswith("linux"):
        current_os = "linux"
    elif sys.platform.startswith("win"):
        current_os = "windows"
    else:
        raise RuntimeError(f"Unsupported build host platform: {sys.platform}")

    if current_os != target_os:
        raise RuntimeError(f"Target OS {target_os} does not match build host platform {current_os}")

    for path in (build_dir, dist_dir):
        if path.exists():
            shutil.rmtree(path)

    output_dir.mkdir(parents=True, exist_ok=True)

    entrypoint = repo_root / "cli" / "obsuractl_entry.py"
    pyinstaller_command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        "obsuractl",
        "--specpath",
        str(spec_dir),
        "--paths",
        str(repo_root / "cli"),
        str(entrypoint),
    ]

    if target_os == "windows":
        icon_path = create_windows_icon(repo_root, build_dir)
        version_file = create_windows_version_file(build_dir, version_label)
        pyinstaller_command.extend(["--icon", str(icon_path), "--version-file", str(version_file)])

    subprocess.run(pyinstaller_command, check=True)

    binary_name = "obsuractl.exe" if target_os == "windows" else "obsuractl"
    built_binary = dist_dir / binary_name
    if not built_binary.exists():
        raise FileNotFoundError(f"Expected built binary at {built_binary}")

    subprocess.run([str(built_binary), "--help"], check=True)

    archive_name = f"obsuractl_{version_label}_{target_os}_{target_arch}.zip"
    archive_path = output_dir / archive_name
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(built_binary, arcname=binary_name)

    return archive_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a standalone obsuractl binary archive with PyInstaller.")
    parser.add_argument("--version-label", required=True, help="release label such as v0.1.0 or dev-a921b32")
    parser.add_argument("--target-os", choices=("linux", "windows"), required=True)
    parser.add_argument("--target-arch", choices=("amd64",), required=True)
    parser.add_argument("--output-dir", default="artifacts/release", help="directory to place the built zip archive")
    args = parser.parse_args()

    archive_path = build_binary(
        version_label=args.version_label,
        target_os=args.target_os,
        target_arch=args.target_arch,
        output_dir=Path(args.output_dir),
    )
    print(archive_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
