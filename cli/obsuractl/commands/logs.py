from __future__ import annotations

import argparse

from .. import config
from ..helpers import compose_command, ensure_stack_access, print_compose_manual_equivalent, print_stack_context, run
from ..ui import add_command_parser


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = add_command_parser(
        subparsers,
        "logs",
        summary="Show logs for a named environment and optional services.",
        purpose=(
            "Stream or inspect recent logs from the Compose-managed services in the selected environment.",
            "When no service is specified, logs covers the full stack.",
        ),
        wraps=("docker compose logs [services...]",),
        examples=(
            "obsuractl logs local",
            "obsuractl logs local api --follow",
            "obsuractl logs production api --tail 500",
        ),
        notes=("Service names must match the Compose service names in the selected stack.",),
    )
    parser.add_argument(
        "environment",
        choices=config.VALID_ENVIRONMENTS,
        metavar="{local|production}",
        help="Target stack environment.",
    )
    parser.add_argument("services", nargs="*", help="optional service names")
    parser.add_argument("--follow", "-f", action="store_true", help="stream logs")
    parser.add_argument("--tail", default="200", help="number of lines to show before streaming")
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    stack = ensure_stack_access(args.environment)
    print_stack_context(stack, action="logs", services=args.services)
    compose_args = ["logs", "--tail", str(args.tail)]
    if args.follow:
        compose_args.append("--follow")
    compose_args.extend(args.services)
    print_compose_manual_equivalent(stack, *compose_args)
    run(compose_command(stack, *compose_args))
    return 0
