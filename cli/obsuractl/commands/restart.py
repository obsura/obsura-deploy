from __future__ import annotations

import argparse

from .. import config
from ..helpers import compose_command, ensure_stack_access, print_compose_manual_equivalent, print_stack_context, run
from ..ui import add_command_parser


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = add_command_parser(
        subparsers,
        "restart",
        summary="Restart one or more services in a named environment stack.",
        purpose=(
            "Restart the whole stack or specific services without changing image references.",
            "This is useful after editing runtime config that does not require a full update workflow.",
        ),
        wraps=("docker compose restart [services...]",),
        examples=(
            "obsuractl restart local",
            "obsuractl restart production api",
            "obsuractl restart production api postgres",
        ),
        notes=("If you need to change images, use obsuractl update or obsuractl rollback instead.",),
    )
    parser.add_argument(
        "environment",
        choices=config.VALID_ENVIRONMENTS,
        metavar="{local|production}",
        help="Target stack environment.",
    )
    parser.add_argument("services", nargs="*", help="optional service names to restart")
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    stack = ensure_stack_access(args.environment)
    print_stack_context(stack, action="restart", services=args.services)
    command = compose_command(stack, "restart", *args.services)
    print_compose_manual_equivalent(stack, "restart", *args.services)
    run(command)
    return 0
