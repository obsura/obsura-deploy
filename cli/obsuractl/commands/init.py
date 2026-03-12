from __future__ import annotations

import argparse
import secrets
import shutil
import sys
from pathlib import Path

from .. import config
from ..helpers import (
    UserError,
    parse_env_file,
    placeholder_like,
    require_real_image_reference,
    set_stack_api_image,
    stack_configured_api_image,
)
from ..ui import add_command_parser, key_label


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = add_command_parser(
        subparsers,
        "init",
        summary="Create missing env files from the committed example templates.",
        purpose=(
            "Bootstrap env/global.env, env/api.env, and env/postgres.env from the checked-in examples.",
            "This is the normal first step after downloading obsuractl or cloning obsura-deploy.",
        ),
        wraps=("env/*.env.example -> env/*.env",),
        examples=(
            "obsuractl init",
            "obsuractl init --quickstart-local --image ghcr.io/obsura/obsura-api:<tag>",
            "obsuractl init --template-only",
            "obsuractl init --force",
            "obsuractl --repo-root /srv/obsura-deploy init",
        ),
        notes=(
            "Interactive terminals can offer a local quickstart after copying the env files.",
            "For a non-interactive local bootstrap, use --quickstart-local --image <published-tag-or-digest>.",
            "Use --force only when you intend to overwrite existing operator-managed env files.",
        ),
    )
    parser.add_argument(
        "--image",
        help="published obsura-api tag or digest to write into compose/local/docker-compose.yaml",
    )
    parser.add_argument(
        "--quickstart-local",
        action="store_true",
        help="prepare a local-first setup by setting --image and generating a strong POSTGRES_PASSWORD",
    )
    parser.add_argument(
        "--template-only",
        action="store_true",
        help="copy env files only and skip the interactive local quickstart prompt",
    )
    parser.add_argument("--force", action="store_true", help="overwrite existing env files")
    parser.set_defaults(handler=handle)


def interactive_console_available() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def prompt_text(message: str) -> str:
    try:
        return input(message)
    except (EOFError, KeyboardInterrupt) as exc:
        raise UserError("interactive init was cancelled") from exc


def prompt_yes_no(message: str, *, default: bool) -> bool:
    options = "[Y/n]" if default else "[y/N]"
    while True:
        answer = prompt_text(f"{message} {options} ").strip().lower()
        if not answer:
            return default
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please answer yes or no.")


def prompt_for_image() -> str:
    while True:
        image = prompt_text("Published Obsura API image tag or digest: ").strip()
        if not image:
            print("A real published image reference is required.")
            continue
        try:
            require_real_image_reference(image, label="init image")
        except UserError as exc:
            print(exc)
            continue
        return image


def set_env_value(path: Path, key: str, value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    output: list[str] = []
    updated = False

    for line in lines:
        if line.startswith(f"{key}="):
            output.append(f"{key}={value}")
            updated = True
        else:
            output.append(line)

    if not updated:
        output.append(f"{key}={value}")

    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def quickstart_needed(stack: config.StackPaths, postgres_env: Path) -> bool:
    current_image = stack_configured_api_image(stack) or ""
    postgres_values = parse_env_file(postgres_env)
    current_password = postgres_values.get("POSTGRES_PASSWORD", "")
    return (
        not current_image
        or placeholder_like(current_image)
        or not current_password
        or placeholder_like(current_password)
    )


def handle(args: argparse.Namespace) -> int:
    created: list[str] = []
    skipped: list[str] = []
    changed: list[str] = []
    quickstart_notes: list[str] = []
    repo_root = config.repo_root()
    env_dir = config.env_dir(repo_root)
    local_stack = config.resolve_stack("local")
    quickstart_local = bool(args.quickstart_local)
    image = args.image

    if args.image and not args.quickstart_local:
        raise UserError("--image is only supported with --quickstart-local")
    if args.template_only and args.quickstart_local:
        raise UserError("--template-only cannot be combined with --quickstart-local")
    if args.template_only and args.image:
        raise UserError("--template-only cannot be combined with --image")

    for example_name, target_name in config.EXAMPLE_ENV_FILES.items():
        source = env_dir / example_name
        target = env_dir / target_name

        if not source.exists():
            raise UserError(f"missing example env file: {source}")

        if target.exists() and not args.force:
            skipped.append(target.name)
            continue

        shutil.copyfile(source, target)
        created.append(target.name)

    global_env = env_dir / "global.env"
    postgres_env = env_dir / "postgres.env"

    if image:
        require_real_image_reference(image, label="init image")

    if (
        not quickstart_local
        and not args.template_only
        and not image
        and interactive_console_available()
        and quickstart_needed(local_stack, postgres_env)
    ):
        print(key_label("Local quickstart:"))
        print(f"  obsuractl can finish a local-ready setup by updating {local_stack.compose_file}")
        print("  and generating a strong POSTGRES_PASSWORD for you.")
        quickstart_local = prompt_yes_no("Prepare the local quickstart now?", default=True)

    if quickstart_local and not image:
        image = prompt_for_image()

    if image:
        set_stack_api_image(local_stack, image)
        changed.append(str(local_stack.compose_file))
        if quickstart_local:
            quickstart_notes.append(f"Set the api and volume-init image in {local_stack.compose_file}.")

    if quickstart_local:
        postgres_values = parse_env_file(postgres_env)
        current_password = postgres_values.get("POSTGRES_PASSWORD", "")
        if args.force or not current_password or placeholder_like(current_password):
            generated_password = secrets.token_hex(24)
            set_env_value(postgres_env, "POSTGRES_PASSWORD", generated_password)
            changed.append(str(postgres_env))
            quickstart_notes.append(f"Generated a strong POSTGRES_PASSWORD in {postgres_env}.")
        else:
            quickstart_notes.append(f"Kept the existing POSTGRES_PASSWORD in {postgres_env}.")

    if created:
        print(f"{key_label('Repository root:')} {repo_root}")
        print(key_label("Created:"))
        for name in created:
            print(f"  - {env_dir / name}")

    if skipped:
        if not created:
            print(f"{key_label('Repository root:')} {repo_root}")
        print(key_label("Left unchanged:"))
        for name in skipped:
            print(f"  - {env_dir / name}")

    if changed:
        print(key_label("Updated:"))
        for path in changed:
            print(f"  - {path}")

    if quickstart_notes:
        print(key_label("Local quickstart:"))
        for note in quickstart_notes:
            print(f"  - {note}")

    print(key_label("Next steps:"))
    if quickstart_local:
        print("  1. Start the stack with obsuractl up local.")
        print("  2. Check status with obsuractl status local.")
        print("  3. Follow logs with obsuractl logs local api --follow if needed.")
        print("  4. Verify health at http://127.0.0.1:8000/api/v1/health if you kept the default port.")
        print("  Optional: run obsuractl doctor local for a standalone preflight check.")
    else:
        if image:
            print(f"  1. The local api image is already set in {local_stack.compose_file}.")
            print(f"  2. Edit {postgres_env} and replace POSTGRES_PASSWORD.")
            print("  3. Run obsuractl doctor production or obsuractl doctor local.")
            print("  4. Start the stack with obsuractl up local or obsuractl up production.")
        else:
            print("  1. Edit compose/local/docker-compose.yaml and set the api image to a published tag or digest.")
            print("  2. Edit env/postgres.env and replace POSTGRES_PASSWORD.")
            print("  3. Run obsuractl doctor production or obsuractl doctor local.")
            print("  4. Start the stack with obsuractl up local or obsuractl up production.")
    return 0
