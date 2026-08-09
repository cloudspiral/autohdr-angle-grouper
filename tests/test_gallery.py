from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from autohdr_eval.gallery import render_error_gallery


def _write_image(path: Path, value: int) -> None:
    image = np.full((48, 72, 3), value, dtype=np.uint8)
    cv2.putText(
        image,
        path.stem,
        (3, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.3,
        (255 - value, 255 - value, 255 - value),
        1,
        cv2.LINE_AA,
    )
    assert cv2.imwrite(str(path), image)


def test_gallery_renders_deterministic_failure_contact_sheets(tmp_path: Path) -> None:
    dataset = tmp_path / "images"
    dataset.mkdir()
    for index, filename in enumerate(["a.jpg", "b.jpg", "c.jpg"]):
        _write_image(dataset / filename, 50 + index * 60)

    diagnostics = tmp_path / "diagnostics.json"
    diagnostics.write_text(
        json.dumps(
            {
                "failures": [
                    {
                        "failure_types": ["split"],
                        "predicted_groups": [["a.jpg"], ["b.jpg"]],
                        "reference_group": ["a.jpg", "b.jpg"],
                    },
                    {
                        "failure_types": ["merge"],
                        "predicted_groups": [["b.jpg", "c.jpg"]],
                        "reference_group": ["c.jpg"],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first = render_error_gallery(
        dataset_root=dataset,
        diagnostics_path=diagnostics,
        output_dir=first_dir,
    )
    second = render_error_gallery(
        dataset_root=dataset,
        diagnostics_path=diagnostics,
        output_dir=second_dir,
    )

    assert first["failure_count"] == 2
    assert first["items"] == second["items"]
    assert (first_dir / "index.json").read_bytes() == (
        second_dir / "index.json"
    ).read_bytes()
    for item in first["items"]:
        assert (first_dir / item["image"]).read_bytes() == (
            second_dir / item["image"]
        ).read_bytes()


def test_gallery_rejects_ambiguous_or_missing_image_names(tmp_path: Path) -> None:
    dataset = tmp_path / "images"
    dataset.mkdir()
    diagnostics = tmp_path / "diagnostics.json"
    diagnostics.write_text(
        json.dumps(
            {
                "failures": [
                    {
                        "failure_types": ["split"],
                        "predicted_groups": [["missing.jpg"]],
                        "reference_group": ["missing.jpg"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    try:
        render_error_gallery(
            dataset_root=dataset,
            diagnostics_path=diagnostics,
            output_dir=tmp_path / "gallery",
        )
    except ValueError as error:
        assert "missing or ambiguous" in str(error)
    else:
        raise AssertionError("missing gallery image should be rejected")
