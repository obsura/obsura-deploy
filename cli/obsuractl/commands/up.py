from __future__ import annotations

import argparse

from .. import config
from ..helpers import ensure_stack_ready, print_script_manual_equivalent, print_stack_context, run, script_command
from ..ui import add_command_parser


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = add_command_parser(
        subparsers,
        "up",
        summary="Start a named environment stack.",
        purpose=(
            "Run the documented deploy workflow for the selected environment.",
            "This command validates the env files first, then shells out to scripts/deploy.*.",
        ),
        wraps=("scripts/deploy.sh <environment>", "scripts/deploy.ps1 -Environment <environment>"),
        examples=(
            "obsuractl up local",
            "obsuractl up production",
            "obsuractl --repo-root /srv/obsura-deploy up production",
        ),
        notes=(
            "Run obsuractl init and obsuractl doctor before the first start.",
            "The production stack still binds the API to localhost by default.",
            "The wrapped deploy script waits for the API container health check before completing.",
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
    print_stack_context(stack, action="up")
    print_script_manual_equivalent("deploy", args.environment)
    run(script_command("deploy", args.environment))
    return 0
