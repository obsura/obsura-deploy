from __future__ import annotations

import argparse

from obsuractl.main import build_parser


def test_cli_exposes_supported_v1_commands() -> None:
    parser = build_parser()
    subparsers_action = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )
    commands = set(subparsers_action.choices.keys())

    assert commands == {
        "init",
        "doctor",
        "up",
        "down",
        "restart",
        "status",
        "logs",
        "update",
        "rollback",
        "backup",
        "restore",
    }


def test_rollback_command_accepts_image_target() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "rollback",
            "production",
            "--to-image",
            "ghcr.io/obsura/obsura-api@sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        ]
    )

    assert args.command == "rollback"
    assert args.environment == "production"
