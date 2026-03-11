from __future__ import annotations

import argparse

from .. import config
from ..helpers import ensure_stack_access, print_script_manual_equivalent, print_stack_context, run, script_command


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("backup", help="run the documented backup workflow")
    parser.add_argument("environment", choices=config.VALID_ENVIRONMENTS)
    parser.add_argument("--output-dir", help="optional target directory for the backup set")
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    stack = ensure_stack_access(args.environment)
    print_stack_context(stack, action="backup", backup_path=args.output_dir)
    if args.output_dir:
        print(f"Requested backup output: {args.output_dir}")
    manual_args = [args.environment]
    if args.output_dir:
        manual_args.append(args.output_dir)
    print_script_manual_equivalent("backup", *manual_args)
    command = script_command("backup", args.environment)
    if args.output_dir:
        command.append(args.output_dir)
    run(command)
    return 0
