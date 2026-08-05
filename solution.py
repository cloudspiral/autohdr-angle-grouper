"""AutoHDR camera-angle grouping submission entrypoint.

The module intentionally starts with the challenge's safe singleton baseline.
Issue-driven work can improve :func:`group_images` without changing the
container contract or CSV validation around it.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

INPUT_DIR = Path("/input/images")
OUTPUT_DIR = Path("/output")
SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png"}


def group_images(image_paths: list[str]) -> list[list[str]]:
    """Return one group per camera angle.

    This initial implementation is the deterministic singleton baseline. It
    satisfies the submission contract but intentionally does not attempt to
    recognize exposure brackets yet.
    """

    return [[Path(image_path).name] for image_path in sorted(image_paths)]


def discover_images(input_dir: Path) -> list[str]:
    """Return supported image paths in a stable order."""

    if not input_dir.is_dir():
        raise FileNotFoundError(f"input image directory does not exist: {input_dir}")

    return [
        str(path)
        for path in sorted(input_dir.iterdir(), key=lambda candidate: candidate.name)
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    ]


def validate_groups(groups: Sequence[Sequence[str]], image_paths: Sequence[str]) -> None:
    """Enforce the challenge's exactly-once, filename-only output contract."""

    expected = [Path(image_path).name for image_path in image_paths]
    if len(expected) != len(set(expected)):
        raise ValueError("input images must have unique basenames")

    predicted: list[str] = []
    for group in groups:
        if not group:
            raise ValueError("predicted groups must not be empty")
        for filename in group:
            if Path(filename).name != filename:
                raise ValueError(f"predictions must contain filenames only: {filename}")
            predicted.append(filename)

    duplicates = sorted(name for name, count in Counter(predicted).items() if count > 1)
    missing = sorted(set(expected) - set(predicted))
    unexpected = sorted(set(predicted) - set(expected))
    if duplicates or missing or unexpected:
        raise ValueError(
            "invalid grouping: "
            f"duplicates={duplicates}, missing={missing}, unexpected={unexpected}"
        )


def write_predictions(
    groups: Sequence[Sequence[str]], image_paths: Sequence[str], output_path: Path
) -> None:
    """Validate groups and write the required predictions CSV."""

    validate_groups(groups, image_paths)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(["filename", "group_id"])
        for group_id, group in enumerate(groups):
            for filename in sorted(group):
                writer.writerow([filename, group_id])


def run(input_dir: Path = INPUT_DIR, output_dir: Path = OUTPUT_DIR) -> Path:
    """Run grouping against one photoshoot and return the output CSV path."""

    image_paths = discover_images(input_dir)
    print(f"Loaded {len(image_paths)} images from {input_dir}", flush=True)

    groups = group_images(image_paths)
    print(f"Predicted {len(groups)} groups", flush=True)

    output_path = output_dir / "predictions.csv"
    write_predictions(groups, image_paths, output_path)
    print(f"Wrote {len(image_paths)} predictions to {output_path}", flush=True)
    return output_path


def parse_args() -> argparse.Namespace:
    """Parse optional local paths while preserving the container defaults."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    run(arguments.input_dir, arguments.output_dir)
