from __future__ import annotations

import argparse
import sys

from .commands import backup, doctor, down, init, logs, restart, restore, rollback, status, up, update
from .config import RepoRootError, set_runtime_repo_root
from .helpers import UserError
from .ui import ObsuraHelpFormatter, command_example, error_text, heading, render_help_sections, requested_color_mode, set_color_mode
from .version import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="obsuractl",
        description="Thin operator CLI for an obsura-deploy checkout.",
        epilog=render_help_sections(
            (
                "Quick Start",
                (
                    command_example("obsuractl init"),
                    command_example("obsuractl doctor local"),
                    command_example("obsuractl up local"),
                ),
            ),
            (
                "Common Production Flow",
                (
                    command_example("obsuractl doctor production"),
                    command_example("obsuractl up production"),
                    command_example("obsuractl logs production api --follow"),
                    command_example("obsuractl backup production"),
                ),
            ),
            (
                "Repository Discovery",
                (
                    "Run obsuractl from inside an obsura-deploy checkout, or pass --repo-root /path/to/obsura-deploy.",
                    "You can also export OBSURA_DEPLOY_ROOT=/path/to/obsura-deploy.",
                ),
            ),
            (
                "Help And Manual",
                (
                    command_example("obsuractl <command> --help"),
                    command_example("man ./man/obsuractl.1"),
                    "Disable color with --no-color or NO_COLOR=1.",
                ),
            ),
        ),
        formatter_class=ObsuraHelpFormatter,
        allow_abbrev=False,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--repo-root",
        metavar="PATH",
        help="Path to the obsura-deploy repository checkout. Defaults to searching from the current directory upward.",
    )
    parser.add_argument(
        "--color",
        choices=("auto", "always", "never"),
        default=None,
        help="Control ANSI color output. Default: auto.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI color output.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, title=heading("Commands"), metavar="<command>")

    for module in (init, doctor, up, down, restart, status, logs, update, rollback, backup, restore):
        module.register(subparsers)

    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    set_color_mode(requested_color_mode(argv))
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.no_color:
        set_color_mode("never")
    elif args.color:
        set_color_mode(args.color)
    set_runtime_repo_root(args.repo_root)

    try:
        return args.handler(args)
    except (RepoRootError, UserError) as exc:
        print(error_text(f"error: {exc}"), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
