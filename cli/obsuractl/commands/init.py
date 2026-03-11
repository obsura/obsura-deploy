from __future__ import annotations

import argparse
import shutil

from .. import config
from ..helpers import UserError
from ..ui import add_command_parser, key_label


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = add_command_parser(
        subparsers,
        "init",
        summary="Create missing env files from the committed example templates.",
        purpose=(
            "Bootstrap env/global.env, env/api.env, and env/postgres.env from the checked-in examples.",
            "This is the normal first step after downloading obsuractl or cloning obsura-deploy.",
        ),
        wraps=("env/*.env.example -> env/*.env",),
        examples=(
            "obsuractl init",
            "obsuractl init --force",
            "obsuractl --repo-root /srv/obsura-deploy init",
        ),
        notes=(
            "After init, edit env/global.env and env/postgres.env before running doctor or up.",
            "Use --force only when you intend to overwrite existing operator-managed env files.",
        ),
    )
    parser.add_argument("--force", action="store_true", help="overwrite existing env files")
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    created: list[str] = []
    skipped: list[str] = []
    repo_root = config.repo_root()
    env_dir = config.env_dir(repo_root)

    for example_name, target_name in config.EXAMPLE_ENV_FILES.items():
        source = env_dir / example_name
        target = env_dir / target_name

        if not source.exists():
            raise UserError(f"missing example env file: {source}")

        if target.exists() and not args.force:
            skipped.append(target.name)
            continue

        shutil.copyfile(source, target)
        created.append(target.name)

    if created:
        print(f"{key_label('Repository root:')} {repo_root}")
        print(key_label("Created:"))
        for name in created:
            print(f"  - {env_dir / name}")

    if skipped:
        if not created:
            print(f"{key_label('Repository root:')} {repo_root}")
        print(key_label("Left unchanged:"))
        for name in skipped:
            print(f"  - {env_dir / name}")

    print(key_label("Next steps:"))
    print("  1. Edit env/global.env and set OBSURA_API_IMAGE to a published tag or digest.")
    print("  2. Edit env/postgres.env and replace POSTGRES_PASSWORD.")
    print("  3. Run obsuractl doctor production or obsuractl doctor local.")
    print("  4. Start the stack with obsuractl up local or obsuractl up production.")
    return 0
