from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def sha256_for_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Write SHA256 checksums for release zip archives.")
    parser.add_argument("--input-dir", required=True, help="directory containing release archives")
    parser.add_argument("--output", default="checksums.txt", help="output checksum file path")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    archives = sorted(input_dir.glob("obsuractl_*.zip"))
    if not archives:
        raise SystemExit(f"No release archives found under {input_dir}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for archive in archives:
            handle.write(f"{sha256_for_file(archive)}  {archive.name}\n")

    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
