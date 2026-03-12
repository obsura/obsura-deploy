from __future__ import annotations

import argparse

from .. import config
from ..helpers import ensure_stack_ready, print_script_manual_equivalent, print_stack_context, run, script_command
from ..ui import add_command_parser


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = add_command_parser(
        subparsers,
        "update",
        summary="Pull newer images and recreate the selected environment.",
        purpose=(
            "Run the documented update workflow using the current api image from the selected compose file.",
            "This command does not invent image state. It uses the image reference already written in the repo checkout.",
        ),
        wraps=("scripts/update.sh <environment>", "scripts/update.ps1 -Environment <environment>"),
        examples=(
            "obsuractl update local",
            "obsuractl update production",
        ),
        notes=(
            "Set the api image in the selected compose file to a reviewed tag or digest before updating.",
            "For production, prefer an immutable digest over a mutable tag.",
            "The wrapped update script waits for API health and prints the running image summary.",
        ),
    )
    parser.add_argument(
        "environment",
        choices=config.VALID_ENVIRONMENTS,
        metavar="{local|production}",
        help="Target stack environment.",
    )
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    stack = ensure_stack_ready(args.environment)
    print_stack_context(stack, action="update")
    print_script_manual_equivalent("update", args.environment)
    run(script_command("update", args.environment))
    return 0
