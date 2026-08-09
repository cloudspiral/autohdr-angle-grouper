"""Validate the human-gated Codabench manifest and build a deterministic ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

EXPECTED_KEYS = {"docker_image", "email", "machine_type"}
PLACEHOLDER_NAMESPACE = "YOUR_DOCKERHUB_NAMESPACE"
PLACEHOLDER_EMAIL = "YOUR_CODABENCH_EMAIL"
IMAGE_PATTERN = re.compile(
    r"^[a-z0-9]+(?:[._-][a-z0-9]+)*/"
    r"[a-z0-9]+(?:[._-][a-z0-9]+)*:[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$"
)
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_manifest(manifest_path: Path) -> dict[str, str]:
    """Parse the deliberately flat, scalar-only submission YAML contract."""

    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(
        manifest_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"submission.yaml line {line_number} is not key: value")
        key, value = (part.strip() for part in line.split(":", 1))
        if not key or not value:
            raise ValueError(f"submission.yaml line {line_number} has an empty key/value")
        if key in values:
            raise ValueError(f"submission.yaml repeats key {key}")
        values[key] = value
    if set(values) != EXPECTED_KEYS:
        raise ValueError(
            f"submission.yaml keys must be exactly {sorted(EXPECTED_KEYS)}"
        )
    return values


def validate_manifest(values: dict[str, str]) -> dict[str, bool]:
    """Validate values while explicitly allowing the two human-owned placeholders."""

    image = values["docker_image"]
    namespace_placeholder = image.startswith(f"{PLACEHOLDER_NAMESPACE}/")
    if not namespace_placeholder and IMAGE_PATTERN.fullmatch(image) is None:
        raise ValueError("docker_image must be a namespaced image with an immutable tag")

    email = values["email"]
    email_placeholder = email == PLACEHOLDER_EMAIL
    if not email_placeholder and EMAIL_PATTERN.fullmatch(email) is None:
        raise ValueError("email must be the registered Codabench email")

    if values["machine_type"] not in {"cpu-large", "cpu-xlarge"}:
        raise ValueError("machine_type must be cpu-large or cpu-xlarge")
    return {
        "dockerhub_namespace": namespace_placeholder,
        "registered_email": email_placeholder,
    }


def prepare_submission(manifest_path: Path, output_path: Path) -> dict[str, object]:
    """Validate and package exactly one submission.yaml with stable ZIP metadata."""

    values = parse_manifest(manifest_path)
    placeholders = validate_manifest(values)
    manifest_bytes = manifest_path.read_bytes()

    member = ZipInfo("submission.yaml", date_time=(1980, 1, 1, 0, 0, 0))
    member.compress_type = ZIP_DEFLATED
    member.external_attr = 0o100644 << 16
    with ZipFile(output_path, "w") as archive:
        archive.writestr(member, manifest_bytes)

    with ZipFile(output_path) as archive:
        if archive.namelist() != ["submission.yaml"]:
            raise AssertionError("submission ZIP contains unexpected members")
        if archive.read("submission.yaml") != manifest_bytes:
            raise AssertionError("submission ZIP manifest differs from source")

    return {
        "docker_image": values["docker_image"],
        "machine_type": values["machine_type"],
        "manifest_path": str(manifest_path),
        "manifest_sha256": _sha256(manifest_bytes),
        "output_path": str(output_path),
        "placeholders": placeholders,
        "zip_members": ["submission.yaml"],
        "zip_sha256": _sha256(output_path.read_bytes()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("submission.yaml"))
    parser.add_argument("--output", type=Path, default=Path("submission.zip"))
    args = parser.parse_args(argv)
    print(
        json.dumps(
            prepare_submission(args.manifest.resolve(), args.output.resolve()),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
