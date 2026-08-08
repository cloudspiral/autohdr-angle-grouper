"""AutoHDR camera-angle grouping submission entrypoint."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

import cv2
import numpy as np

INPUT_DIR = Path("/input/images")
OUTPUT_DIR = Path("/output")
SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png"}

# Calibration points for the exposure-invariant structural descriptor. These are
# intentionally module-level names so labeled AutoHDR evaluation can tune them.
DESCRIPTOR_IMAGE_SIZE = 96
DESCRIPTOR_GRID_SIZE = 16
EXPOSURE_LOW_PERCENTILE = 2.0
EXPOSURE_HIGH_PERCENTILE = 98.0
GRADIENT_ORIENTATION_BINS = 6
SPATIAL_POOLING_SIGMA = 2.0
LUMINANCE_FEATURE_WEIGHT = 0.35
GRADIENT_FEATURE_WEIGHT = 0.65
STRUCTURAL_DISTANCE_THRESHOLD = 0.16
_DESCRIPTOR_EPSILON = 1e-8


def _unit_vector(values: np.ndarray) -> np.ndarray:
    """Return a stable float32 unit vector, preserving an all-zero vector."""

    vector = values.astype(np.float32, copy=False).reshape(-1)
    norm = float(np.linalg.norm(vector))
    if norm <= _DESCRIPTOR_EPSILON:
        return np.zeros_like(vector)
    return vector / norm


def _normalize_exposure(grayscale: np.ndarray) -> np.ndarray:
    """Suppress global exposure and monotonic tone differences."""

    low, high = np.percentile(
        grayscale, [EXPOSURE_LOW_PERCENTILE, EXPOSURE_HIGH_PERCENTILE]
    )
    dynamic_range = float(high - low)
    if dynamic_range <= _DESCRIPTOR_EPSILON:
        return np.zeros(grayscale.shape, dtype=np.float32)

    normalized = np.clip((grayscale.astype(np.float32) - low) / dynamic_range, 0.0, 1.0)
    normalized_u8 = np.rint(normalized * 255.0).astype(np.uint8)
    return cv2.equalizeHist(normalized_u8).astype(np.float32) / 255.0


def _build_descriptor(image_path: str) -> np.ndarray:
    """Build an exposure-normalized, spatially pooled structural descriptor."""

    read_flags = cv2.IMREAD_GRAYSCALE | cv2.IMREAD_IGNORE_ORIENTATION
    grayscale = cv2.imread(image_path, read_flags)
    if grayscale is None:
        raise ValueError(f"unable to decode image: {image_path}")

    interpolation = (
        cv2.INTER_AREA
        if max(grayscale.shape) > DESCRIPTOR_IMAGE_SIZE
        else cv2.INTER_LINEAR
    )
    resized = cv2.resize(
        grayscale,
        (DESCRIPTOR_IMAGE_SIZE, DESCRIPTOR_IMAGE_SIZE),
        interpolation=interpolation,
    )
    normalized = _normalize_exposure(resized)

    pooled_luminance = cv2.GaussianBlur(
        normalized,
        (0, 0),
        sigmaX=SPATIAL_POOLING_SIGMA,
        sigmaY=SPATIAL_POOLING_SIGMA,
    )
    pooled_luminance = cv2.resize(
        pooled_luminance,
        (DESCRIPTOR_GRID_SIZE, DESCRIPTOR_GRID_SIZE),
        interpolation=cv2.INTER_AREA,
    )
    pooled_luminance -= float(pooled_luminance.mean())
    luminance_features = _unit_vector(pooled_luminance)

    gradient_x = cv2.Sobel(normalized, cv2.CV_32F, 1, 0, ksize=3)
    gradient_y = cv2.Sobel(normalized, cv2.CV_32F, 0, 1, ksize=3)
    magnitude, angle = cv2.cartToPolar(gradient_x, gradient_y, angleInDegrees=False)
    unsigned_angle = np.mod(angle, np.pi)
    scaled_angle = unsigned_angle * (GRADIENT_ORIENTATION_BINS / np.pi)

    orientation_features: list[np.ndarray] = []
    for bin_index in range(GRADIENT_ORIENTATION_BINS):
        bin_distance = np.abs(scaled_angle - float(bin_index))
        circular_distance = np.minimum(bin_distance, GRADIENT_ORIENTATION_BINS - bin_distance)
        orientation_weight = np.clip(1.0 - circular_distance, 0.0, 1.0)
        channel = magnitude * orientation_weight
        channel = cv2.GaussianBlur(
            channel,
            (0, 0),
            sigmaX=SPATIAL_POOLING_SIGMA,
            sigmaY=SPATIAL_POOLING_SIGMA,
        )
        orientation_features.append(
            cv2.resize(
                channel,
                (DESCRIPTOR_GRID_SIZE, DESCRIPTOR_GRID_SIZE),
                interpolation=cv2.INTER_AREA,
            )
        )

    gradient_features = _unit_vector(np.stack(orientation_features))
    descriptor = np.concatenate(
        (
            np.sqrt(LUMINANCE_FEATURE_WEIGHT) * luminance_features,
            np.sqrt(GRADIENT_FEATURE_WEIGHT) * gradient_features,
        )
    )
    return _unit_vector(descriptor)


def _structural_distance(left: np.ndarray, right: np.ndarray) -> float:
    """Return cosine distance, treating two featureless images as equivalent."""

    left_has_structure = bool(np.any(left))
    right_has_structure = bool(np.any(right))
    if not left_has_structure or not right_has_structure:
        return 0.0 if left_has_structure == right_has_structure else 1.0
    similarity = float(np.clip(np.dot(left, right), -1.0, 1.0))
    return 1.0 - similarity


def _connected_components(descriptors: Sequence[np.ndarray]) -> list[list[int]]:
    """Join every below-threshold descriptor pair into deterministic components."""

    parents = list(range(len(descriptors)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parents[max(left_root, right_root)] = min(left_root, right_root)

    for left_index, left_descriptor in enumerate(descriptors):
        for right_index in range(left_index + 1, len(descriptors)):
            if (
                _structural_distance(left_descriptor, descriptors[right_index])
                <= STRUCTURAL_DISTANCE_THRESHOLD
            ):
                union(left_index, right_index)

    components: dict[int, list[int]] = {}
    for index in range(len(descriptors)):
        components.setdefault(find(index), []).append(index)
    return list(components.values())


def group_images(image_paths: list[str]) -> list[list[str]]:
    """Group images by exposure-normalized pixel structure.

    Paths and filenames are used only to load pixels and serialize stable output;
    component membership is decided exclusively from decoded pixel descriptors.
    """

    ordered_paths = sorted(image_paths)
    descriptors = [_build_descriptor(image_path) for image_path in ordered_paths]
    groups = [
        sorted(Path(ordered_paths[index]).name for index in component)
        for component in _connected_components(descriptors)
    ]
    return sorted(groups, key=lambda group: tuple(group))


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
