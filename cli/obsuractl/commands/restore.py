from __future__ import annotations

import argparse

from .. import config
from ..helpers import ensure_stack_ready, print_script_manual_equivalent, print_stack_context, run, script_command, UserError


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("restore", help="run the documented restore workflow")
    parser.add_argument("environment", choices=config.VALID_ENVIRONMENTS)
    parser.add_argument("backup_dir", help="path to a backup set containing postgres.sql and obsura-data.tgz")
    parser.add_argument("--yes", action="store_true", help="confirm the destructive restore operation")
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    if not args.yes:
        raise UserError("restore requires --yes because it replaces the current database and app data volume")

    stack = ensure_stack_ready(args.environment)
    print_stack_context(stack, action="restore", backup_path=args.backup_dir)
    print_script_manual_equivalent("restore", args.environment, args.backup_dir, "--yes")
    run(script_command("restore", args.environment, args.backup_dir, "--yes"))
    return 0
