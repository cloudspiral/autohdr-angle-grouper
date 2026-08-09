"""Deterministic visual error galleries for exact-group failures."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from autohdr_eval.config import canonical_json_bytes
from autohdr_eval.dataset import SUPPORTED_SUFFIXES

_PALETTE = [
    (230, 120, 40),
    (60, 180, 75),
    (180, 70, 200),
    (40, 170, 220),
    (220, 80, 90),
    (120, 180, 40),
]


def _safe_text(value: str, maximum: int = 24) -> str:
    ascii_value = value.encode("ascii", errors="replace").decode("ascii")
    return ascii_value if len(ascii_value) <= maximum else f"{ascii_value[: maximum - 3]}..."


def _thumbnail(image: np.ndarray | None, width: int, height: int) -> np.ndarray:
    canvas = np.full((height, width, 3), 28, dtype=np.uint8)
    if image is None:
        cv2.putText(
            canvas,
            "decode failed",
            (8, height // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (80, 80, 230),
            1,
            cv2.LINE_AA,
        )
        return canvas
    image_height, image_width = image.shape[:2]
    scale = min(width / image_width, height / image_height)
    resized = cv2.resize(
        image,
        (max(1, round(image_width * scale)), max(1, round(image_height * scale))),
        interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR,
    )
    top = (height - resized.shape[0]) // 2
    left = (width - resized.shape[1]) // 2
    canvas[top : top + resized.shape[0], left : left + resized.shape[1]] = resized
    return canvas


def _render_failure(
    failure: dict[str, Any],
    images: dict[str, Path],
    output_path: Path,
) -> None:
    reference = set(failure["reference_group"])
    predicted_groups = failure["predicted_groups"]
    items = [
        (filename, group_index)
        for group_index, group in enumerate(predicted_groups)
        for filename in group
    ]
    columns = min(6, max(1, len(items)))
    rows = max(1, math.ceil(len(items) / columns))
    cell_width = 180
    cell_height = 150
    header_height = 52
    canvas = np.full(
        (header_height + rows * cell_height, columns * cell_width, 3),
        245,
        dtype=np.uint8,
    )
    failure_label = "+".join(failure["failure_types"])
    cv2.putText(
        canvas,
        f"{failure_label} | reference={len(reference)} | predicted={len(predicted_groups)}",
        (10, 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (25, 25, 25),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        canvas,
        "border color = predicted group; REF marks a reference member",
        (10, 44),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        (70, 70, 70),
        1,
        cv2.LINE_AA,
    )

    for item_index, (filename, group_index) in enumerate(items):
        row, column = divmod(item_index, columns)
        x_start = column * cell_width
        y_start = header_height + row * cell_height
        image = cv2.imread(str(images[filename]), cv2.IMREAD_COLOR)
        thumbnail = _thumbnail(image, cell_width - 12, 112)
        canvas[y_start + 5 : y_start + 117, x_start + 6 : x_start + cell_width - 6] = thumbnail
        color = _PALETTE[group_index % len(_PALETTE)]
        cv2.rectangle(
            canvas,
            (x_start + 3, y_start + 2),
            (x_start + cell_width - 4, y_start + cell_height - 3),
            color,
            3,
        )
        label = _safe_text(filename)
        if filename in reference:
            label = f"REF {label}"
        cv2.putText(
            canvas,
            label,
            (x_start + 8, y_start + 138),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.38,
            (20, 20, 20),
            1,
            cv2.LINE_AA,
        )
    if not cv2.imwrite(
        str(output_path), canvas, [cv2.IMWRITE_PNG_COMPRESSION, 9]
    ):
        raise OSError(f"unable to write gallery image: {output_path}")


def render_error_gallery(
    *,
    dataset_root: Path,
    diagnostics_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Render every recorded group failure and write a deterministic index."""

    with diagnostics_path.open(encoding="utf-8") as input_file:
        diagnostics = json.load(input_file)
    failures = diagnostics.get("failures")
    if not isinstance(failures, list):
        raise ValueError("diagnostics artifact does not contain a failures list")

    discovered: dict[str, list[Path]] = {}
    for path in dataset_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            discovered.setdefault(path.name, []).append(path)
    required = {
        filename
        for failure in failures
        for group in failure["predicted_groups"]
        for filename in group
    }
    ambiguous = sorted(filename for filename in required if len(discovered.get(filename, [])) != 1)
    if ambiguous:
        raise ValueError(f"gallery images are missing or ambiguous: {ambiguous}")
    images = {filename: discovered[filename][0] for filename in required}

    output_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    ordered_failures = sorted(
        failures,
        key=lambda failure: (
            tuple(failure["reference_group"]),
            tuple(failure["failure_types"]),
        ),
    )
    for index, failure in enumerate(ordered_failures, start=1):
        identity = hashlib.sha256(
            canonical_json_bytes(failure["reference_group"])
        ).hexdigest()[:10]
        kind = "-".join(failure["failure_types"])
        filename = f"{index:03d}-{kind}-{identity}.png"
        _render_failure(failure, images, output_dir / filename)
        entries.append(
            {
                "failure_types": failure["failure_types"],
                "image": filename,
                "predicted_group_count": len(failure["predicted_groups"]),
                "reference_group": failure["reference_group"],
            }
        )
    index_value = {
        "diagnostics_path": str(diagnostics_path),
        "failure_count": len(entries),
        "items": entries,
        "schema_version": 1,
    }
    (output_dir / "index.json").write_bytes(canonical_json_bytes(index_value))
    return index_value
