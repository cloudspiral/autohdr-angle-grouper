"""AutoHDR camera-angle grouping submission entrypoint."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass, fields
from functools import lru_cache
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from autohdr_eval.contracts import validate_groups as validate_groups
from autohdr_eval.contracts import write_predictions as write_predictions

INPUT_DIR = Path("/input/images")
OUTPUT_DIR = Path("/output")
SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png"}
OPENCV_THREADS = 2
SUBMISSION_CONFIG_PATH = (
    Path(__file__).resolve().parent / "configs" / "phase4" / "b2-screened-dual-clahe.json"
)

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


@dataclass(frozen=True)
class StructuralConfig:
    """Configurable B1 descriptor and threshold-graph parameters."""

    descriptor_image_size: int = DESCRIPTOR_IMAGE_SIZE
    descriptor_grid_size: int = DESCRIPTOR_GRID_SIZE
    exposure_low_percentile: float = EXPOSURE_LOW_PERCENTILE
    exposure_high_percentile: float = EXPOSURE_HIGH_PERCENTILE
    gradient_orientation_bins: int = GRADIENT_ORIENTATION_BINS
    spatial_pooling_sigma: float = SPATIAL_POOLING_SIGMA
    luminance_feature_weight: float = LUMINANCE_FEATURE_WEIGHT
    gradient_feature_weight: float = GRADIENT_FEATURE_WEIGHT
    structural_distance_threshold: float = STRUCTURAL_DISTANCE_THRESHOLD

    def __post_init__(self) -> None:
        if self.descriptor_image_size <= 0 or self.descriptor_grid_size <= 0:
            raise ValueError("descriptor dimensions must be positive")
        if not 0 <= self.exposure_low_percentile < self.exposure_high_percentile <= 100:
            raise ValueError("exposure percentiles must be ordered within [0, 100]")
        if self.gradient_orientation_bins <= 0:
            raise ValueError("gradient_orientation_bins must be positive")
        if self.spatial_pooling_sigma <= 0:
            raise ValueError("spatial_pooling_sigma must be positive")
        if self.luminance_feature_weight < 0 or self.gradient_feature_weight < 0:
            raise ValueError("feature weights must be non-negative")
        if self.luminance_feature_weight + self.gradient_feature_weight <= 0:
            raise ValueError("at least one feature weight must be positive")
        if not 0 <= self.structural_distance_threshold <= 2:
            raise ValueError("structural_distance_threshold must be within [0, 2]")

    @classmethod
    def from_parameters(cls, parameters: dict[str, Any]) -> StructuralConfig:
        expected = {field.name for field in fields(cls)}
        if set(parameters) != expected:
            raise ValueError(
                f"structural parameters must be exactly {sorted(expected)}; "
                f"got {sorted(parameters)}"
            )
        return cls(**parameters)


DEFAULT_STRUCTURAL_CONFIG = StructuralConfig()


def _unit_vector(values: np.ndarray) -> np.ndarray:
    """Return a stable float32 unit vector, preserving an all-zero vector."""

    vector = values.astype(np.float32, copy=False).reshape(-1)
    norm = float(np.linalg.norm(vector))
    if norm <= _DESCRIPTOR_EPSILON:
        return np.zeros_like(vector)
    return vector / norm


def _normalize_exposure(
    grayscale: np.ndarray, config: StructuralConfig = DEFAULT_STRUCTURAL_CONFIG
) -> np.ndarray:
    """Suppress global exposure and monotonic tone differences."""

    low, high = np.percentile(
        grayscale, [config.exposure_low_percentile, config.exposure_high_percentile]
    )
    dynamic_range = float(high - low)
    if dynamic_range <= _DESCRIPTOR_EPSILON:
        return np.zeros(grayscale.shape, dtype=np.float32)

    normalized = np.clip((grayscale.astype(np.float32) - low) / dynamic_range, 0.0, 1.0)
    normalized_u8 = np.rint(normalized * 255.0).astype(np.uint8)
    return cv2.equalizeHist(normalized_u8).astype(np.float32) / 255.0


def _build_descriptor(
    image_path: str, config: StructuralConfig = DEFAULT_STRUCTURAL_CONFIG
) -> np.ndarray:
    """Build an exposure-normalized, spatially pooled structural descriptor."""

    # OpenCV applies EXIF orientation by default. Orientation is used only to
    # decode the intended pixels; no other metadata is a grouping signal.
    grayscale = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if grayscale is None:
        raise ValueError(f"unable to decode image: {image_path}")

    interpolation = (
        cv2.INTER_AREA
        if max(grayscale.shape) > config.descriptor_image_size
        else cv2.INTER_LINEAR
    )
    resized = cv2.resize(
        grayscale,
        (config.descriptor_image_size, config.descriptor_image_size),
        interpolation=interpolation,
    )
    normalized = _normalize_exposure(resized, config)

    pooled_luminance = cv2.GaussianBlur(
        normalized,
        (0, 0),
        sigmaX=config.spatial_pooling_sigma,
        sigmaY=config.spatial_pooling_sigma,
    )
    pooled_luminance = cv2.resize(
        pooled_luminance,
        (config.descriptor_grid_size, config.descriptor_grid_size),
        interpolation=cv2.INTER_AREA,
    )
    pooled_luminance -= float(pooled_luminance.mean())
    luminance_features = _unit_vector(pooled_luminance)

    gradient_x = cv2.Sobel(normalized, cv2.CV_32F, 1, 0, ksize=3)
    gradient_y = cv2.Sobel(normalized, cv2.CV_32F, 0, 1, ksize=3)
    magnitude, angle = cv2.cartToPolar(gradient_x, gradient_y, angleInDegrees=False)
    unsigned_angle = np.mod(angle, np.pi)
    scaled_angle = unsigned_angle * (config.gradient_orientation_bins / np.pi)

    orientation_features: list[np.ndarray] = []
    for bin_index in range(config.gradient_orientation_bins):
        bin_distance = np.abs(scaled_angle - float(bin_index))
        circular_distance = np.minimum(
            bin_distance, config.gradient_orientation_bins - bin_distance
        )
        orientation_weight = np.clip(1.0 - circular_distance, 0.0, 1.0)
        channel = magnitude * orientation_weight
        channel = cv2.GaussianBlur(
            channel,
            (0, 0),
            sigmaX=config.spatial_pooling_sigma,
            sigmaY=config.spatial_pooling_sigma,
        )
        orientation_features.append(
            cv2.resize(
                channel,
                (config.descriptor_grid_size, config.descriptor_grid_size),
                interpolation=cv2.INTER_AREA,
            )
        )

    gradient_features = _unit_vector(np.stack(orientation_features))
    descriptor = np.concatenate(
        (
            np.sqrt(config.luminance_feature_weight) * luminance_features,
            np.sqrt(config.gradient_feature_weight) * gradient_features,
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


def _connected_components(
    descriptors: Sequence[np.ndarray],
    threshold: float = STRUCTURAL_DISTANCE_THRESHOLD,
) -> list[list[int]]:
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
                <= threshold
            ):
                union(left_index, right_index)

    components: dict[int, list[int]] = {}
    for index in range(len(descriptors)):
        components.setdefault(find(index), []).append(index)
    return list(components.values())


def group_images_with_config(
    image_paths: list[str], config: StructuralConfig
) -> list[list[str]]:
    """Group images with an explicit B1 configuration and safe decode fallback."""

    ordered_paths = sorted(image_paths)
    decoded_paths: list[str] = []
    descriptors: list[np.ndarray] = []
    fallback_singletons: list[list[str]] = []
    for image_path in ordered_paths:
        try:
            descriptor = _build_descriptor(image_path, config)
        except (OSError, ValueError, cv2.error) as error:
            filename = Path(image_path).name
            print(f"Warning: {filename} could not be decoded; using singleton: {error}", flush=True)
            fallback_singletons.append([filename])
            continue
        decoded_paths.append(image_path)
        descriptors.append(descriptor)

    groups = [
        sorted(Path(decoded_paths[index]).name for index in component)
        for component in _connected_components(
            descriptors, threshold=config.structural_distance_threshold
        )
    ]
    groups.extend(fallback_singletons)
    return sorted(groups, key=lambda group: tuple(group))


def group_images(image_paths: list[str]) -> list[list[str]]:
    """Group images with screened dual-view local geometry.

    Paths and filenames are used only to load pixels and serialize stable output;
    component membership is decided exclusively from decoded pixel evidence.
    """

    outcome = group_images_with_resources(image_paths)
    print(
        "Evaluated "
        f"{outcome.resources['candidate_pair_count']}/"
        f"{outcome.resources['all_pair_count']} candidate pairs in each view",
        flush=True,
    )
    return outcome.groups


def group_images_with_resources(
    image_paths: list[str], *, opencv_threads: int = OPENCV_THREADS
) -> Any:
    """Run the submission implementation and expose counters for benchmarks."""

    from autohdr_eval.classical import run_screened_dual_classical_uncached

    if opencv_threads < 1:
        raise ValueError("opencv_threads must be positive")
    cv2.setNumThreads(opencv_threads)
    config, seed = _submission_config()
    outcome = run_screened_dual_classical_uncached(image_paths, config, seed=seed)
    outcome.resources["opencv_threads_requested"] = opencv_threads
    return outcome


@lru_cache(maxsize=1)
def _submission_config() -> tuple[Any, int]:
    """Load and strictly validate the packaged Phase 4 runtime configuration."""

    from autohdr_eval.classical import ScreenedPercentileClassicalConfig
    from autohdr_eval.config import load_config

    loaded = load_config(SUBMISSION_CONFIG_PATH)
    if loaded.algorithm != "classical-screened-dual-clahe":
        raise ValueError("submission config must select screened dual-view classical")
    return ScreenedPercentileClassicalConfig.from_parameters(loaded.parameters), loaded.seed


def discover_images(input_dir: Path) -> list[str]:
    """Return supported image paths in a stable order."""

    if not input_dir.is_dir():
        raise FileNotFoundError(f"input image directory does not exist: {input_dir}")

    return [
        str(path)
        for path in sorted(input_dir.iterdir(), key=lambda candidate: candidate.name)
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    ]


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
