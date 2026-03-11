from __future__ import annotations

import argparse

from .. import config
from ..helpers import ensure_stack_access, print_script_manual_equivalent, print_stack_context, run, script_command
from ..ui import add_command_parser, key_label


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = add_command_parser(
        subparsers,
        "backup",
        summary="Run the documented backup workflow.",
        purpose=(
            "Create a backup set for PostgreSQL and persistent app data for the selected environment.",
            "The backup remains local to the host unless you move it elsewhere yourself.",
        ),
        wraps=("scripts/backup.sh <environment> [output-dir]", "scripts/backup.ps1 -Environment <environment> [-OutputDir PATH]"),
        examples=(
            "obsuractl backup local",
            "obsuractl backup production --output-dir /srv/backups/obsura/manual-test",
        ),
        notes=(
            "This is not a full backup platform. It creates the documented local backup artifacts only.",
            "Verify the backup contents before relying on it.",
        ),
    )
    parser.add_argument(
        "environment",
        choices=config.VALID_ENVIRONMENTS,
        metavar="{local|production}",
        help="Target stack environment.",
    )
    parser.add_argument("--output-dir", help="optional target directory for the backup set")
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    stack = ensure_stack_access(args.environment)
    print_stack_context(stack, action="backup", backup_path=args.output_dir)
    if args.output_dir:
        print(f"{key_label('Requested backup output:')} {args.output_dir}")
    manual_args = [args.environment]
    if args.output_dir:
        manual_args.append(args.output_dir)
    print_script_manual_equivalent("backup", *manual_args)
    command = script_command("backup", args.environment)
    if args.output_dir:
        command.append(args.output_dir)
    run(command)
    return 0
