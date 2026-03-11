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


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "rollback",
        help="set a previously approved image reference and recreate the selected environment",
    )
    parser.add_argument("environment", choices=config.VALID_ENVIRONMENTS)
    parser.add_argument(
        "--to-image",
        required=True,
        help="published tag or digest to write into env/global.env before recreating services",
    )
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    require_real_image_reference(args.to_image, label="rollback target image")
    stack = ensure_stack_access(args.environment)
    print_stack_context(stack, action="rollback", target_image=args.to_image)
    print_script_manual_equivalent("rollback", args.environment, args.to_image)
    run(script_command("rollback", args.environment, args.to_image))
    return 0
