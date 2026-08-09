from __future__ import annotations

import hashlib
from pathlib import Path
from zipfile import ZipFile

import pytest

from scripts.prepare_submission import parse_manifest, prepare_submission


def _write_manifest(path: Path, *, image: str, email: str) -> None:
    path.write_text(
        f"docker_image: {image}\nmachine_type: cpu-large\nemail: {email}\n",
        encoding="utf-8",
    )


def test_prepare_submission_accepts_explicit_human_placeholders(tmp_path: Path) -> None:
    manifest = tmp_path / "submission.yaml"
    output = tmp_path / "submission.zip"
    _write_manifest(
        manifest,
        image="YOUR_DOCKERHUB_NAMESPACE/autohdr-angle-grouper:phase5-532cc1b",
        email="YOUR_CODABENCH_EMAIL",
    )

    result = prepare_submission(manifest, output)

    assert result["placeholders"] == {
        "dockerhub_namespace": True,
        "registered_email": True,
    }
    with ZipFile(output) as archive:
        assert archive.namelist() == ["submission.yaml"]
        assert archive.read("submission.yaml") == manifest.read_bytes()


def test_prepare_submission_is_byte_deterministic(tmp_path: Path) -> None:
    manifest = tmp_path / "submission.yaml"
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    _write_manifest(
        manifest,
        image="example/autohdr-angle-grouper:phase5-532cc1b",
        email="registered@example.com",
    )

    prepare_submission(manifest, first)
    prepare_submission(manifest, second)

    assert hashlib.sha256(first.read_bytes()).digest() == hashlib.sha256(
        second.read_bytes()
    ).digest()


def test_parse_manifest_rejects_extra_fields(tmp_path: Path) -> None:
    manifest = tmp_path / "submission.yaml"
    _write_manifest(
        manifest,
        image="example/autohdr-angle-grouper:phase5-532cc1b",
        email="registered@example.com",
    )
    manifest.write_text(
        manifest.read_text(encoding="utf-8") + "unexpected: value\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="keys must be exactly"):
        parse_manifest(manifest)
