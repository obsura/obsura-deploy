from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


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
