from __future__ import annotations

import argparse

from .. import config
from ..helpers import compose_command, ensure_stack_access, print_compose_manual_equivalent, print_stack_context, run


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("logs", help="show logs for a named environment")
    parser.add_argument("environment", choices=config.VALID_ENVIRONMENTS)
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
