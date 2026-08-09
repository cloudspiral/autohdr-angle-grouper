"""Deterministic cheap candidate generation for expensive local matching."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np


@dataclass(frozen=True)
class CandidateScreenConfig:
    """Structural top-k screen and the batch-size all-pairs crossover."""

    all_pairs_max_images: int
    top_k: int
    structural: dict[str, Any]

    def __post_init__(self) -> None:
        if self.all_pairs_max_images < 2:
            raise ValueError("all_pairs_max_images must be at least two")
        if self.top_k < 1:
            raise ValueError("top_k must be positive")
        expected_structural = {
            "descriptor_grid_size",
            "descriptor_image_size",
            "exposure_high_percentile",
            "exposure_low_percentile",
            "gradient_feature_weight",
            "gradient_orientation_bins",
            "luminance_feature_weight",
            "spatial_pooling_sigma",
            "structural_distance_threshold",
        }
        if set(self.structural) != expected_structural:
            raise ValueError(
                "candidate structural parameters must be exactly "
                f"{sorted(expected_structural)}; got {sorted(self.structural)}"
            )

    @classmethod
    def from_parameters(cls, raw: Any) -> CandidateScreenConfig:
        if not isinstance(raw, dict):
            raise ValueError("candidate_screen must be an object")
        expected = {"all_pairs_max_images", "structural", "top_k"}
        if set(raw) != expected:
            raise ValueError(
                f"candidate_screen keys must be exactly {sorted(expected)}; "
                f"got {sorted(raw)}"
            )
        if type(raw["all_pairs_max_images"]) is not int:
            raise ValueError("all_pairs_max_images must be an integer")
        if type(raw["top_k"]) is not int:
            raise ValueError("top_k must be an integer")
        if not isinstance(raw["structural"], dict):
            raise ValueError("candidate structural parameters must be an object")
        return cls(
            all_pairs_max_images=raw["all_pairs_max_images"],
            top_k=raw["top_k"],
            structural=raw["structural"],
        )


@dataclass(frozen=True)
class CandidateOutcome:
    """Screened paths, candidate pairs, fallbacks, and resource counters."""

    image_paths: tuple[str, ...]
    candidate_pairs: tuple[tuple[str, str], ...]
    fallback_filenames: tuple[str, ...]
    resources: dict[str, Any]


def _all_pairs(filenames: list[str]) -> tuple[tuple[str, str], ...]:
    return tuple(
        (left, right)
        for left_index, left in enumerate(filenames)
        for right in filenames[left_index + 1 :]
    )


def generate_structural_candidates(
    image_paths: list[str], config: CandidateScreenConfig
) -> CandidateOutcome:
    """Nominate local-match pairs without treating proximity as grouping proof."""

    # Imported lazily to avoid a module cycle: solution owns the frozen B1
    # descriptor, while its submission path calls this screen.
    from solution import StructuralConfig, _build_descriptor

    ordered_paths = sorted((Path(path) for path in image_paths), key=lambda path: path.name)
    filenames = [path.name for path in ordered_paths]
    if len(filenames) != len(set(filenames)):
        raise ValueError("candidate generation requires unique input basenames")

    all_pair_count = len(filenames) * (len(filenames) - 1) // 2
    if len(ordered_paths) <= config.all_pairs_max_images:
        pairs = _all_pairs(filenames)
        return CandidateOutcome(
            image_paths=tuple(str(path) for path in ordered_paths),
            candidate_pairs=pairs,
            fallback_filenames=(),
            resources={
                "all_pair_count": all_pair_count,
                "candidate_fraction": 1.0 if all_pair_count else 0.0,
                "candidate_pair_count": len(pairs),
                "candidate_screen_fallbacks": 0,
                "candidate_screen_mode": "all_pairs",
                "screen_descriptor_count": 0,
            },
        )

    structural_config = StructuralConfig.from_parameters(config.structural)
    valid_paths: list[Path] = []
    descriptors: list[np.ndarray] = []
    fallbacks: list[str] = []
    for path in ordered_paths:
        try:
            descriptor = _build_descriptor(str(path), structural_config)
        except (OSError, ValueError, cv2.error) as error:
            print(
                f"Warning: {path.name} could not be screened; using singleton: {error}",
                flush=True,
            )
            fallbacks.append(path.name)
            continue
        valid_paths.append(path)
        descriptors.append(descriptor)

    valid_names = [path.name for path in valid_paths]
    valid_pair_count = len(valid_names) * (len(valid_names) - 1) // 2
    if len(valid_names) < 2:
        pairs: tuple[tuple[str, str], ...] = ()
    elif config.top_k >= len(valid_names) - 1:
        pairs = _all_pairs(valid_names)
    else:
        matrix = np.stack(descriptors).astype(np.float32, copy=False)
        similarities = np.clip(matrix @ matrix.T, -1.0, 1.0)
        distances = 1.0 - similarities
        has_structure = np.any(matrix != 0.0, axis=1)
        both_empty = (~has_structure)[:, None] & (~has_structure)[None, :]
        one_empty = has_structure[:, None] ^ has_structure[None, :]
        distances[both_empty] = 0.0
        distances[one_empty] = 1.0
        selected: set[tuple[str, str]] = set()
        for index, filename in enumerate(valid_names):
            other_indices = [other for other in range(len(valid_names)) if other != index]
            cutoff = sorted(float(distances[index, other]) for other in other_indices)[
                config.top_k - 1
            ]
            # Include every numeric tie at the top-k boundary. Filename order is
            # therefore never used to decide which tied pixel descriptors survive.
            for other in other_indices:
                if float(distances[index, other]) <= cutoff + 1e-12:
                    selected.add(tuple(sorted((filename, valid_names[other]))))
        pairs = tuple(sorted(selected))

    return CandidateOutcome(
        image_paths=tuple(str(path) for path in valid_paths),
        candidate_pairs=pairs,
        fallback_filenames=tuple(sorted(fallbacks)),
        resources={
            "all_pair_count": valid_pair_count,
            "candidate_fraction": (
                len(pairs) / valid_pair_count if valid_pair_count else 0.0
            ),
            "candidate_pair_count": len(pairs),
            "candidate_screen_fallbacks": len(fallbacks),
            "candidate_screen_mode": "structural_top_k",
            "screen_descriptor_count": len(descriptors),
        },
    )
