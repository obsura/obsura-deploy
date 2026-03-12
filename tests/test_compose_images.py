from __future__ import annotations

from pathlib import Path

from obsuractl.helpers import compose_service_image, set_compose_service_image


def test_compose_service_image_reads_expected_service_image(tmp_path: Path) -> None:
    compose_file = tmp_path / "docker-compose.yaml"
    compose_file.write_text(
        "services:\n"
        "  volume-init:\n"
        "    image: ghcr.io/obsura/obsura-api:0.1.0\n"
        "  api:\n"
        "    image: ghcr.io/obsura/obsura-api:0.1.0\n",
        encoding="utf-8",
    )

    assert compose_service_image(compose_file, "api") == "ghcr.io/obsura/obsura-api:0.1.0"


def test_set_compose_service_image_updates_only_target_service(tmp_path: Path) -> None:
    compose_file = tmp_path / "docker-compose.yaml"
    compose_file.write_text(
        "services:\n"
        "  volume-init:\n"
        "    image: ghcr.io/obsura/obsura-api:0.1.0\n"
        "  api:\n"
        "    image: ghcr.io/obsura/obsura-api:0.1.0\n"
        "  postgres:\n"
        "    image: postgres:17-alpine\n",
        encoding="utf-8",
    )

    set_compose_service_image(compose_file, "api", "ghcr.io/obsura/obsura-api:0.2.0")

    assert compose_service_image(compose_file, "api") == "ghcr.io/obsura/obsura-api:0.2.0"
    assert compose_service_image(compose_file, "volume-init") == "ghcr.io/obsura/obsura-api:0.1.0"
