from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path


def read_version() -> str:
    repo_root = Path(__file__).resolve().parents[1]
    version_path = repo_root / "cli" / "obsuractl" / "version.py"
    spec = importlib.util.spec_from_file_location("obsuractl_version", version_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load version module from {version_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    version = getattr(module, "__version__", None)
    if not version:
        raise RuntimeError(f"No __version__ found in {version_path}")
    return str(version)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read the obsuractl version from the repository source of truth.")
    parser.add_argument("--prefix", default="", help="optional string to prepend to the version")
    args = parser.parse_args()
    print(f"{args.prefix}{read_version()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
