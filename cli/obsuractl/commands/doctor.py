from __future__ import annotations

import argparse

from .. import config
from ..helpers import collect_doctor_result, print_doctor_result, print_doctor_target, UserError


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("doctor", help="validate docker, env files, and compose wiring")
    parser.add_argument("environment", choices=config.VALID_ENVIRONMENTS)
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    print_doctor_target(args.environment)
    result = collect_doctor_result(args.environment)
    print_doctor_result(result)
    if result.errors:
        raise UserError(f"{len(result.errors)} validation issue(s) detected for {args.environment}")
    return 0
