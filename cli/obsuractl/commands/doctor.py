from __future__ import annotations

import argparse

from .. import config
from ..helpers import collect_doctor_result, print_doctor_result, print_doctor_target, UserError
from ..ui import add_command_parser


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = add_command_parser(
        subparsers,
        "doctor",
        summary="Validate Docker, env files, image references, and Compose wiring.",
        purpose=(
            "Run preflight checks before starting, updating, or restoring a stack.",
            "Doctor verifies Docker, Compose, env files, placeholder values, and basic port assumptions.",
        ),
        wraps=("docker compose config",),
        examples=(
            "obsuractl doctor local",
            "obsuractl doctor production",
            "obsuractl --repo-root /srv/obsura-deploy doctor production",
        ),
        notes=(
            "Production warns when the compose file uses a mutable tag instead of an immutable digest.",
            "If local env files are missing, the fastest fix is obsuractl init --quickstart-local --image <published-tag-or-digest>.",
            "Manual setup remains available through obsuractl init.",
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
    print_doctor_target(args.environment)
    result = collect_doctor_result(args.environment)
    print_doctor_result(result)
    if result.errors:
        raise UserError(f"{len(result.errors)} validation issue(s) detected for {args.environment}")
    return 0
