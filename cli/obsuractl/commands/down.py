from __future__ import annotations

import argparse

from .. import config
from ..helpers import compose_command, ensure_stack_access, print_compose_manual_equivalent, print_stack_context, run


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("down", help="stop a named environment stack safely")
    parser.add_argument("environment", choices=config.VALID_ENVIRONMENTS)
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    stack = ensure_stack_access(args.environment)
    print_stack_context(stack, action="down")
    print_compose_manual_equivalent(stack, "down", "--remove-orphans")
    run(compose_command(stack, "down", "--remove-orphans"))
    return 0
