from __future__ import annotations

import argparse

from .. import config
from ..helpers import ensure_stack_ready, print_script_manual_equivalent, print_stack_context, run, script_command


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("up", help="start a named environment stack")
    parser.add_argument("environment", choices=config.VALID_ENVIRONMENTS)
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    stack = ensure_stack_ready(args.environment)
    print_stack_context(stack, action="up")
    print_script_manual_equivalent("deploy", args.environment)
    run(script_command("deploy", args.environment))
    return 0
