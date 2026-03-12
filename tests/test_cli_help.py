from __future__ import annotations

import argparse
from pathlib import Path

from obsuractl.main import build_parser
from obsuractl import ui


def command_parser(name: str) -> argparse.ArgumentParser:
    parser = build_parser()
    subparsers_action = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )
    return subparsers_action.choices[name]


def test_top_level_help_includes_examples_and_manual_hint() -> None:
    ui.set_color_mode("never")

    help_text = build_parser().format_help()

    assert "Fastest Local Start" in help_text
    assert "obsuractl init --quickstart-local --image" in help_text
    assert "obsuractl <command> --help" in help_text
    assert "man ./man/obsuractl.1" in help_text
    assert "--color {auto,always,never}" in help_text


def test_up_help_includes_examples_and_wrapped_workflow() -> None:
    ui.set_color_mode("never")

    help_text = command_parser("up").format_help()

    assert "Purpose" in help_text
    assert "Wraps" in help_text
    assert "Examples" in help_text
    assert "obsuractl up production" in help_text
    assert "scripts/deploy.sh <environment>" in help_text


def test_init_help_includes_quickstart_and_template_only_modes() -> None:
    ui.set_color_mode("never")

    help_text = command_parser("init").format_help()

    assert "--quickstart-local" in help_text
    assert "--template-only" in help_text
    assert "Interactive terminals can offer a local quickstart" in help_text


def test_color_styling_can_be_forced_and_disabled() -> None:
    ui.set_color_mode("always")
    assert "\x1b[" in ui.style("obsuractl", fg="cyan", bold=True)

    ui.set_color_mode("never")
    assert ui.style("obsuractl", fg="cyan", bold=True) == "obsuractl"
    ui.set_color_mode("auto")


def test_linux_man_page_exists() -> None:
    assert Path("man/obsuractl.1").exists()
