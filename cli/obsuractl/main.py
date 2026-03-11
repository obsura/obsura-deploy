from __future__ import annotations

import argparse
import sys

from .commands import backup, doctor, down, init, logs, restart, restore, rollback, status, up, update
from .helpers import UserError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="obsuractl",
        description="Thin operator CLI for the obsura-deploy repository.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for module in (init, doctor, up, down, restart, status, logs, update, rollback, backup, restore):
        module.register(subparsers)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return args.handler(args)
    except UserError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
