from __future__ import annotations

import argparse

from .. import config
from ..helpers import (
    ensure_stack_access,
    print_script_manual_equivalent,
    print_stack_context,
    require_real_image_reference,
    run,
    script_command,
)
from ..ui import add_command_parser


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = add_command_parser(
        subparsers,
        "rollback",
        summary="Set a previously approved image reference and recreate the selected environment.",
        purpose=(
            "Write a reviewed tag or digest into the selected compose file, then run the documented update workflow.",
            "Rollback is explicit. You must provide the exact target image reference.",
        ),
        wraps=("scripts/rollback.sh <environment> <image>", "scripts/rollback.ps1 -Environment <environment> -ToImage <image>"),
        examples=(
            "obsuractl rollback production --to-image ghcr.io/obsura/obsura-api@sha256:<digest>",
            "obsuractl rollback local --to-image ghcr.io/obsura/obsura-api:0.1.1",
        ),
        notes=(
            "Rollback changes the compose file for the selected checkout.",
            "Use a previously validated tag or digest. Do not guess.",
            "If the recreate fails, the rollback script restores the previous image in the compose file.",
        ),
    )
    parser.add_argument(
        "environment",
        choices=config.VALID_ENVIRONMENTS,
        metavar="{local|production}",
        help="Target stack environment.",
    )
    parser.add_argument(
        "--to-image",
        required=True,
        help="published tag or digest to write into the selected compose file before recreating services",
    )
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    require_real_image_reference(args.to_image, label="rollback target image")
    stack = ensure_stack_access(args.environment)
    print_stack_context(stack, action="rollback", target_image=args.to_image)
    print_script_manual_equivalent("rollback", args.environment, args.to_image)
    run(script_command("rollback", args.environment, args.to_image))
    return 0
