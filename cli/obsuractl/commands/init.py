from __future__ import annotations

import argparse
import shutil

from .. import config
from ..helpers import UserError


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("init", help="copy missing env files from the example templates")
    parser.add_argument("--force", action="store_true", help="overwrite existing env files")
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    created: list[str] = []
    skipped: list[str] = []

    for example_name, target_name in config.EXAMPLE_ENV_FILES.items():
        source = config.ENV_DIR / example_name
        target = config.ENV_DIR / target_name

        if not source.exists():
            raise UserError(f"missing example env file: {source}")

        if target.exists() and not args.force:
            skipped.append(target.name)
            continue

        shutil.copyfile(source, target)
        created.append(target.name)

    if created:
        print("Created:")
        for name in created:
            print(f"  - env/{name}")

    if skipped:
        print("Left unchanged:")
        for name in skipped:
            print(f"  - env/{name}")

    print("Next steps:")
    print("  1. Edit env/global.env and set OBSURA_API_IMAGE to a published tag or digest.")
    print("  2. Edit env/postgres.env and replace POSTGRES_PASSWORD.")
    print("  3. Run obsuractl doctor production or obsuractl doctor local.")
    print("  4. Start the stack with obsuractl up local or obsuractl up production.")
    return 0
