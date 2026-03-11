from __future__ import annotations

import argparse

from .. import config
from ..helpers import compose_command, ensure_stack_access, print_compose_manual_equivalent, print_stack_context, run


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("restart", help="restart services in a named environment stack")
    parser.add_argument("environment", choices=config.VALID_ENVIRONMENTS)
    parser.add_argument("services", nargs="*", help="optional service names to restart")
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    stack = ensure_stack_access(args.environment)
    print_stack_context(stack, action="restart", services=args.services)
    command = compose_command(stack, "restart", *args.services)
    print_compose_manual_equivalent(stack, "restart", *args.services)
    run(command)
    return 0
