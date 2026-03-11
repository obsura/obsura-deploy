from __future__ import annotations

import argparse

from .. import config
from ..helpers import compose_command, ensure_stack_access, print_compose_manual_equivalent, print_stack_context, run
from ..ui import add_command_parser


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = add_command_parser(
        subparsers,
        "down",
        summary="Stop a named environment stack safely.",
        purpose=(
            "Stop the selected Compose stack and remove orphaned containers.",
            "This is the normal operator path for a clean shutdown.",
        ),
        wraps=("docker compose down --remove-orphans",),
        examples=(
            "obsuractl down local",
            "obsuractl down production",
        ),
        notes=("This does not remove the named database or app-data volumes.",),
    )
    parser.add_argument(
        "environment",
        choices=config.VALID_ENVIRONMENTS,
        metavar="{local|production}",
        help="Target stack environment.",
    )
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    stack = ensure_stack_access(args.environment)
    print_stack_context(stack, action="down")
    print_compose_manual_equivalent(stack, "down", "--remove-orphans")
    run(compose_command(stack, "down", "--remove-orphans"))
    return 0
