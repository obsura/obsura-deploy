from __future__ import annotations

import argparse

from .. import config
from ..helpers import compose_command, ensure_stack_access, print_compose_manual_equivalent, print_stack_context, run
from ..ui import add_command_parser


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = add_command_parser(
        subparsers,
        "status",
        summary="Show service and container status for a named environment.",
        purpose=(
            "Inspect the current Compose state without changing the stack.",
            "Status is the quickest way to confirm container names, health, and restart state.",
        ),
        wraps=("docker compose ps",),
        examples=(
            "obsuractl status local",
            "obsuractl status production",
        ),
        notes=("Use obsuractl logs when you need detailed service output.",),
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
    print_stack_context(stack, action="status")
    print_compose_manual_equivalent(stack, "ps")
    run(compose_command(stack, "ps"))
    return 0
