from __future__ import annotations

import argparse

from .. import config
from ..helpers import ensure_stack_ready, print_script_manual_equivalent, print_stack_context, run, script_command, UserError
from ..ui import add_command_parser


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = add_command_parser(
        subparsers,
        "restore",
        summary="Run the documented restore workflow.",
        purpose=(
            "Replace the current database and persistent app data with a backup set you provide.",
            "Restore is intentionally explicit and destructive.",
        ),
        wraps=("scripts/restore.sh <environment> <backup-dir> --yes", "scripts/restore.ps1 -Environment <environment> -BackupDir PATH -Yes"),
        examples=(
            "obsuractl restore production backups/production/20260311-210000 --yes",
            "obsuractl restore local backups/local/test-run --yes",
        ),
        notes=(
            "Restore requires --yes because it replaces the current database and app data volume.",
            "Run obsuractl backup first if you need a safety copy of the current state.",
            "The wrapped restore script prints backup metadata, recreates storage permissions, and waits for API health before completing.",
        ),
    )
    parser.add_argument(
        "environment",
        choices=config.VALID_ENVIRONMENTS,
        metavar="{local|production}",
        help="Target stack environment.",
    )
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
