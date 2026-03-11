from __future__ import annotations

import argparse
import os
import shutil
import sys
from typing import Iterable, Sequence

COLOR_ENV_VAR = "OBSURACTL_COLOR"
VALID_COLOR_MODES = ("auto", "always", "never")
_color_mode = "auto"

ANSI_RESET = "\033[0m"
ANSI_STYLES = {
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "cyan": "\033[36m",
}


class ObsuraHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def __init__(self, prog: str) -> None:
        width = min(max(shutil.get_terminal_size((100, 24)).columns, 92), 120)
        super().__init__(prog, max_help_position=32, width=width)


def normalize_color_mode(mode: str | None) -> str:
    if mode is None:
        return "auto"
    normalized = mode.strip().lower()
    if normalized not in VALID_COLOR_MODES:
        return "auto"
    return normalized


def requested_color_mode(argv: Sequence[str]) -> str | None:
    requested: str | None = None
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--no-color":
            requested = "never"
        elif token.startswith("--color="):
            requested = token.split("=", 1)[1]
        elif token == "--color" and index + 1 < len(argv):
            requested = argv[index + 1]
            index += 1
        index += 1
    return requested


def set_color_mode(mode: str | None) -> None:
    global _color_mode
    _color_mode = normalize_color_mode(mode or os.environ.get(COLOR_ENV_VAR))


def colors_enabled(*, stream: object | None = None) -> bool:
    mode = normalize_color_mode(_color_mode)
    if mode == "always":
        return True
    if mode == "never":
        return False
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("CLICOLOR_FORCE") == "1":
        return True
    if os.environ.get("TERM", "").lower() == "dumb":
        return False
    target = stream if stream is not None else sys.stdout
    isatty = getattr(target, "isatty", None)
    return bool(isatty and isatty())


def style(
    text: str,
    *,
    fg: str | None = None,
    bold: bool = False,
    dim: bool = False,
    stream: object | None = None,
) -> str:
    if not colors_enabled(stream=stream):
        return text

    codes: list[str] = []
    if bold:
        codes.append(ANSI_STYLES["bold"])
    if dim:
        codes.append(ANSI_STYLES["dim"])
    if fg:
        codes.append(ANSI_STYLES[fg])
    if not codes:
        return text
    return f"{''.join(codes)}{text}{ANSI_RESET}"


def heading(title: str) -> str:
    return style(title, fg="cyan", bold=True)


def command_example(command: str) -> str:
    return style(f"$ {command}", fg="blue", bold=True)


def status_label(level: str, *, stream: object | None = None) -> str:
    palette = {
        "ok": "green",
        "warn": "yellow",
        "error": "red",
        "info": "cyan",
    }
    return style(f"[{level}]", fg=palette[level], bold=True, stream=stream)


def key_label(label: str, *, stream: object | None = None) -> str:
    return style(label, fg="cyan", bold=True, stream=stream)


def command_text(text: str, *, stream: object | None = None) -> str:
    return style(text, fg="blue", dim=True, stream=stream)


def error_text(text: str) -> str:
    return style(text, fg="red", bold=True, stream=sys.stderr)


def render_help_sections(
    *sections: tuple[str, Sequence[str]] | Iterable[tuple[str, Sequence[str]]]
) -> str:
    if len(sections) == 1 and not isinstance(sections[0], tuple):
        section_items = list(sections[0])
    else:
        section_items = [section for section in sections if isinstance(section, tuple)]

    blocks: list[str] = []
    for title, lines in section_items:
        visible_lines = [line for line in lines if line]
        if not visible_lines:
            continue
        block = [heading(title)]
        block.extend(visible_lines)
        blocks.append("\n".join(block))
    return "\n\n".join(blocks)


def add_command_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    name: str,
    *,
    summary: str,
    purpose: Sequence[str],
    examples: Sequence[str],
    wraps: Sequence[str] = (),
    notes: Sequence[str] = (),
) -> argparse.ArgumentParser:
    sections = [("Purpose", list(purpose))]
    if wraps:
        sections.append(("Wraps", list(wraps)))
    sections.append(("Examples", [command_example(example) for example in examples]))
    if notes:
        sections.append(("Notes", list(notes)))

    return subparsers.add_parser(
        name,
        help=summary,
        description=summary,
        epilog=render_help_sections(sections),
        formatter_class=ObsuraHelpFormatter,
        allow_abbrev=False,
    )
