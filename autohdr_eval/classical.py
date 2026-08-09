"""Deterministic classical feature matching and support-aware grouping for B2."""

from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from autohdr_eval.config import canonical_json_bytes
from autohdr_eval.contracts import canonicalize_groups
from autohdr_eval.dataset import sha256_file

CLASSICAL_CACHE_SCHEMA_VERSION = 1


def _strict_dataclass(cls: type[Any], raw: Any, name: str) -> Any:
    if not isinstance(raw, dict):
        raise ValueError(f"{name} must be an object")
    expected = {field.name for field in fields(cls)}
    if set(raw) != expected:
        raise ValueError(
            f"{name} keys must be exactly {sorted(expected)}; got {sorted(raw)}"
        )
    return cls(**raw)


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


@dataclass(frozen=True)
class FeatureConfig:
    max_dimension: int
    max_features: int
    contrast_threshold: float
    edge_threshold: float
    sigma: float
    clahe_clip_limit: float
    clahe_grid_size: int

    def __post_init__(self) -> None:
        if self.max_dimension < 64 or self.max_features < 16:
            raise ValueError("classical feature dimensions are too small")
        if self.contrast_threshold <= 0 or self.edge_threshold <= 0 or self.sigma <= 0:
            raise ValueError("SIFT thresholds and sigma must be positive")
        if self.clahe_clip_limit <= 0 or self.clahe_grid_size <= 0:
            raise ValueError("CLAHE parameters must be positive")


@dataclass(frozen=True)
class MatchConfig:
    ratio_test: float
    min_matches_for_model: int
    ransac_reproj_threshold: float
    ransac_max_iters: int
    ransac_confidence: float
    coverage_grid_size: int
    structural_thumbnail_size: int

    def __post_init__(self) -> None:
        if not 0 < self.ratio_test < 1:
            raise ValueError("ratio_test must be between zero and one")
        if self.min_matches_for_model < 3:
            raise ValueError("min_matches_for_model must be at least three")
        if self.ransac_reproj_threshold <= 0 or self.ransac_max_iters <= 0:
            raise ValueError("RANSAC controls must be positive")
        if not 0 < self.ransac_confidence < 1:
            raise ValueError("ransac_confidence must be between zero and one")
        if self.coverage_grid_size <= 0 or self.structural_thumbnail_size < 32:
            raise ValueError("coverage and thumbnail sizes must be positive")


@dataclass(frozen=True)
class StateConfig:
    strong_min_inliers: int
    strong_min_inlier_ratio: float
    strong_min_coverage: float
    strong_max_transfer_error: float
    strong_min_structural_correlation: float
    positive_min_inliers: int
    positive_min_inlier_ratio: float
    positive_min_coverage: float
    positive_max_transfer_error: float
    positive_min_structural_correlation: float
    min_scale: float
    max_scale: float
    max_abs_rotation_degrees: float
    max_translation_fraction: float
    negative_min_keypoints: int
    negative_min_mutual_matches: int
    negative_max_inlier_ratio: float
    negative_max_structural_correlation: float

    def __post_init__(self) -> None:
        if self.strong_min_inliers < self.positive_min_inliers:
            raise ValueError("strong_min_inliers must not be below positive_min_inliers")
        if self.strong_min_inlier_ratio < self.positive_min_inlier_ratio:
            raise ValueError("strong inlier ratio must not be below positive inlier ratio")
        if self.strong_min_coverage < self.positive_min_coverage:
            raise ValueError("strong coverage must not be below positive coverage")
        if self.strong_max_transfer_error > self.positive_max_transfer_error:
            raise ValueError("strong transfer error must not exceed positive transfer error")
        if not 0 < self.min_scale <= 1 <= self.max_scale:
            raise ValueError("scale bounds must contain one")
        for value in (
            self.strong_min_inlier_ratio,
            self.strong_min_coverage,
            self.positive_min_inlier_ratio,
            self.positive_min_coverage,
            self.negative_max_inlier_ratio,
        ):
            if not 0 <= value <= 1:
                raise ValueError("ratio and coverage thresholds must be within [0, 1]")


@dataclass(frozen=True)
class GroupingConfig:
    min_independent_support_edges: int
    representative_strong_support: bool
    strong_negative_veto: bool

    def __post_init__(self) -> None:
        if self.min_independent_support_edges < 2:
            raise ValueError("grouping requires at least two independent support edges")
        if not isinstance(self.representative_strong_support, bool):
            raise ValueError("representative_strong_support must be boolean")
        if not isinstance(self.strong_negative_veto, bool):
            raise ValueError("strong_negative_veto must be boolean")


@dataclass(frozen=True)
class ClassicalConfig:
    feature: FeatureConfig
    match: MatchConfig
    state: StateConfig
    grouping: GroupingConfig

    @classmethod
    def from_parameters(cls, raw: dict[str, Any]) -> ClassicalConfig:
        expected = {"feature", "grouping", "match", "state"}
        if set(raw) != expected:
            raise ValueError(
                f"classical parameters must be exactly {sorted(expected)}; got {sorted(raw)}"
            )
        return cls(
            feature=_strict_dataclass(FeatureConfig, raw["feature"], "feature"),
            match=_strict_dataclass(MatchConfig, raw["match"], "match"),
            state=_strict_dataclass(StateConfig, raw["state"], "state"),
            grouping=_strict_dataclass(GroupingConfig, raw["grouping"], "grouping"),
        )

    @property
    def feature_fingerprint(self) -> str:
        return _fingerprint(
            {
                "cache_schema_version": CLASSICAL_CACHE_SCHEMA_VERSION,
                "feature": asdict(self.feature),
            }
        )

    @property
    def evidence_fingerprint(self) -> str:
        return _fingerprint(
            {
                "cache_schema_version": CLASSICAL_CACHE_SCHEMA_VERSION,
                "feature_fingerprint": self.feature_fingerprint,
                "match": asdict(self.match),
            }
        )


@dataclass(frozen=True)
class PercentileStretchConfig:
    low_percentile: float
    high_percentile: float

    def __post_init__(self) -> None:
        if not 0 <= self.low_percentile < self.high_percentile <= 100:
            raise ValueError("percentile stretch bounds must be ordered within [0, 100]")


@dataclass(frozen=True)
class PercentileClassicalConfig(ClassicalConfig):
    percentile_stretch: PercentileStretchConfig

    @classmethod
    def from_parameters(cls, raw: dict[str, Any]) -> PercentileClassicalConfig:
        expected = {"feature", "grouping", "match", "percentile_stretch", "state"}
        if set(raw) != expected:
            raise ValueError(
                "percentile classical parameters must be exactly "
                f"{sorted(expected)}; got {sorted(raw)}"
            )
        base = ClassicalConfig.from_parameters(
            {key: raw[key] for key in ("feature", "grouping", "match", "state")}
        )
        return cls(
            feature=base.feature,
            match=base.match,
            state=base.state,
            grouping=base.grouping,
            percentile_stretch=_strict_dataclass(
                PercentileStretchConfig,
                raw["percentile_stretch"],
                "percentile_stretch",
            ),
        )

    @property
    def feature_fingerprint(self) -> str:
        return _fingerprint(
            {
                "architecture": "percentile-clahe-v1",
                "cache_schema_version": CLASSICAL_CACHE_SCHEMA_VERSION,
                "feature": asdict(self.feature),
                "percentile_stretch": asdict(self.percentile_stretch),
            }
        )


@dataclass(frozen=True)
class FeatureRecord:
    filename: str
    content_hash: str
    points: np.ndarray
    descriptors: np.ndarray
    normalized: np.ndarray
    width: int
    height: int
    quality: float


@dataclass(frozen=True)
class PairEvidence:
    left: str
    right: str
    left_keypoints: int
    right_keypoints: int
    forward_ratio_matches: int
    reverse_ratio_matches: int
    mutual_matches: int
    model_found: bool
    inliers: int
    inlier_ratio: float
    median_transfer_error: float | None
    grid_coverage_left: float
    grid_coverage_right: float
    hull_coverage_left: float
    hull_coverage_right: float
    coverage_min: float
    scale: float | None
    rotation_degrees: float | None
    translation_fraction: float | None
    structural_correlation: float | None
    transform: list[list[float]] | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> PairEvidence:
        return cls(**raw)


@dataclass(frozen=True)
class PairDecision:
    left: str
    right: str
    state: str
    score: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ClassicalOutcome:
    groups: list[list[str]]
    resources: dict[str, Any]
    summary: dict[str, Any]
    decisions: tuple[PairDecision, ...]


def _resize_for_features(grayscale: np.ndarray, maximum: int) -> np.ndarray:
    height, width = grayscale.shape
    if max(height, width) <= maximum:
        return grayscale
    scale = maximum / max(height, width)
    return cv2.resize(
        grayscale,
        (max(1, round(width * scale)), max(1, round(height * scale))),
        interpolation=cv2.INTER_AREA,
    )


def _percentile_stretch(
    grayscale: np.ndarray, config: PercentileStretchConfig
) -> np.ndarray:
    low, high = np.percentile(
        grayscale,
        [config.low_percentile, config.high_percentile],
    )
    dynamic_range = float(high - low)
    if dynamic_range <= 1e-12:
        return grayscale.copy()
    normalized = np.clip(
        (grayscale.astype(np.float32) - float(low)) / dynamic_range,
        0.0,
        1.0,
    )
    return np.rint(normalized * 255.0).astype(np.uint8)


def _extract_features(
    path: Path,
    content_hash: str,
    config: FeatureConfig,
    percentile_stretch: PercentileStretchConfig | None = None,
) -> FeatureRecord:
    grayscale = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if grayscale is None:
        raise ValueError(f"unable to decode image: {path}")
    working = _resize_for_features(grayscale, config.max_dimension)
    if percentile_stretch is not None:
        working = _percentile_stretch(working, percentile_stretch)
    clahe = cv2.createCLAHE(
        clipLimit=config.clahe_clip_limit,
        tileGridSize=(config.clahe_grid_size, config.clahe_grid_size),
    )
    normalized = clahe.apply(working)
    sift = cv2.SIFT_create(
        nfeatures=config.max_features,
        contrastThreshold=config.contrast_threshold,
        edgeThreshold=config.edge_threshold,
        sigma=config.sigma,
    )
    keypoints, descriptors = sift.detectAndCompute(normalized, None)
    if descriptors is None or not keypoints:
        points = np.empty((0, 2), dtype=np.float32)
        rootsift = np.empty((0, 128), dtype=np.float32)
    else:
        points = np.asarray([keypoint.pt for keypoint in keypoints], dtype=np.float32)
        descriptors = descriptors.astype(np.float32, copy=False)
        l1_norm = np.sum(np.abs(descriptors), axis=1, keepdims=True)
        rootsift = np.sqrt(descriptors / np.maximum(l1_norm, 1e-12)).astype(
            np.float32, copy=False
        )
    contrast = float(np.std(normalized)) / 64.0
    quality = float(len(points)) + min(1.0, contrast)
    height, width = normalized.shape
    return FeatureRecord(
        filename=path.name,
        content_hash=content_hash,
        points=points,
        descriptors=rootsift,
        normalized=normalized,
        width=width,
        height=height,
        quality=quality,
    )


class FeatureCache:
    def __init__(self, root: Path, config_fingerprint: str) -> None:
        self.root = root / "features" / config_fingerprint
        self.root.mkdir(parents=True, exist_ok=True)

    def get(
        self,
        path: Path,
        content_hash: str,
        config: FeatureConfig,
        percentile_stretch: PercentileStretchConfig | None = None,
    ) -> tuple[FeatureRecord, bool]:
        cache_path = self.root / f"{content_hash}.npz"
        if cache_path.is_file():
            try:
                with np.load(cache_path, allow_pickle=False) as cached:
                    record = FeatureRecord(
                        filename=path.name,
                        content_hash=content_hash,
                        points=cached["points"].astype(np.float32, copy=False),
                        descriptors=cached["descriptors"].astype(np.float32, copy=False),
                        normalized=cached["normalized"].astype(np.uint8, copy=False),
                        width=int(cached["width"]),
                        height=int(cached["height"]),
                        quality=float(cached["quality"]),
                    )
                return record, True
            except (OSError, ValueError, KeyError):
                pass

        record = _extract_features(path, content_hash, config, percentile_stretch)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=self.root, suffix=".npz", delete=False
            ) as output_file:
                temporary = Path(output_file.name)
                np.savez_compressed(
                    output_file,
                    points=record.points,
                    descriptors=record.descriptors,
                    normalized=record.normalized,
                    width=np.asarray(record.width, dtype=np.int64),
                    height=np.asarray(record.height, dtype=np.int64),
                    quality=np.asarray(record.quality, dtype=np.float64),
                )
            os.replace(temporary, cache_path)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
        return record, False


class PairEvidenceCache:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS pair_evidence (
                    schema_version INTEGER NOT NULL,
                    dataset_fingerprint TEXT NOT NULL,
                    evidence_fingerprint TEXT NOT NULL,
                    left_hash TEXT NOT NULL,
                    right_hash TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    PRIMARY KEY (
                        schema_version, dataset_fingerprint, evidence_fingerprint,
                        left_hash, right_hash
                    )
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=60)

    def get(
        self,
        dataset_fingerprint: str,
        evidence_fingerprint: str,
        left_hash: str,
        right_hash: str,
    ) -> PairEvidence | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT evidence_json FROM pair_evidence
                WHERE schema_version = ? AND dataset_fingerprint = ?
                  AND evidence_fingerprint = ? AND left_hash = ? AND right_hash = ?
                """,
                (
                    CLASSICAL_CACHE_SCHEMA_VERSION,
                    dataset_fingerprint,
                    evidence_fingerprint,
                    left_hash,
                    right_hash,
                ),
            ).fetchone()
        if row is None:
            return None
        return PairEvidence.from_dict(json.loads(row[0]))

    def put(
        self,
        dataset_fingerprint: str,
        evidence_fingerprint: str,
        left_hash: str,
        right_hash: str,
        evidence: PairEvidence,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO pair_evidence (
                    schema_version, dataset_fingerprint, evidence_fingerprint,
                    left_hash, right_hash, evidence_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    CLASSICAL_CACHE_SCHEMA_VERSION,
                    dataset_fingerprint,
                    evidence_fingerprint,
                    left_hash,
                    right_hash,
                    json.dumps(
                        evidence.as_dict(),
                        allow_nan=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                ),
            )


def _ratio_matches(
    matcher: cv2.BFMatcher, query: np.ndarray, train: np.ndarray, ratio: float
) -> list[cv2.DMatch]:
    if len(query) == 0 or len(train) < 2:
        return []
    pairs = matcher.knnMatch(query, train, k=2)
    return [first for first, second in pairs if first.distance < ratio * second.distance]


def _grid_coverage(points: np.ndarray, width: int, height: int, grid_size: int) -> float:
    if len(points) == 0:
        return 0.0
    x_cells = np.minimum((points[:, 0] / max(width, 1) * grid_size).astype(int), grid_size - 1)
    y_cells = np.minimum((points[:, 1] / max(height, 1) * grid_size).astype(int), grid_size - 1)
    return len(set(zip(x_cells.tolist(), y_cells.tolist(), strict=True))) / (grid_size**2)


def _hull_coverage(points: np.ndarray, width: int, height: int) -> float:
    if len(points) < 3:
        return 0.0
    hull = cv2.convexHull(points.astype(np.float32))
    return float(cv2.contourArea(hull)) / max(width * height, 1)


def _scaled_transform(
    transform: np.ndarray,
    left_shape: tuple[int, int],
    right_shape: tuple[int, int],
    maximum: int,
) -> tuple[np.ndarray, tuple[int, int]]:
    left_height, left_width = left_shape
    right_height, right_width = right_shape
    left_scale = min(1.0, maximum / max(left_height, left_width))
    right_scale = min(1.0, maximum / max(right_height, right_width))
    left_matrix = np.asarray(
        [[left_scale, 0.0, 0.0], [0.0, left_scale, 0.0], [0.0, 0.0, 1.0]]
    )
    right_matrix = np.asarray(
        [[right_scale, 0.0, 0.0], [0.0, right_scale, 0.0], [0.0, 0.0, 1.0]]
    )
    homogeneous = np.vstack((transform, [0.0, 0.0, 1.0]))
    scaled = right_matrix @ homogeneous @ np.linalg.inv(left_matrix)
    output_size = (
        max(1, round(right_width * right_scale)),
        max(1, round(right_height * right_scale)),
    )
    return scaled[:2].astype(np.float32), output_size


def _gradient_correlation(
    left: np.ndarray,
    right: np.ndarray,
    transform: np.ndarray,
    maximum: int,
) -> float | None:
    scaled_transform, output_size = _scaled_transform(
        transform, left.shape, right.shape, maximum
    )
    left_small = _resize_for_features(left, maximum)
    right_small = _resize_for_features(right, maximum)
    warped = cv2.warpAffine(
        left_small,
        scaled_transform,
        output_size,
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    mask = cv2.warpAffine(
        np.ones(left_small.shape, dtype=np.uint8),
        scaled_transform,
        output_size,
        flags=cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    ).astype(bool)
    if mask.shape != right_small.shape:
        return None
    if int(np.count_nonzero(mask)) < 64:
        return None

    def gradient(image: np.ndarray) -> np.ndarray:
        image_float = image.astype(np.float32) / 255.0
        x_gradient = cv2.Sobel(image_float, cv2.CV_32F, 1, 0, ksize=3)
        y_gradient = cv2.Sobel(image_float, cv2.CV_32F, 0, 1, ksize=3)
        return cv2.magnitude(x_gradient, y_gradient)

    left_values = gradient(warped)[mask]
    right_values = gradient(right_small)[mask]
    left_values -= float(np.mean(left_values))
    right_values -= float(np.mean(right_values))
    denominator = float(np.linalg.norm(left_values) * np.linalg.norm(right_values))
    if denominator <= 1e-12:
        return None
    return float(np.clip(np.dot(left_values, right_values) / denominator, -1.0, 1.0))


def compute_pair_evidence(
    left: FeatureRecord,
    right: FeatureRecord,
    config: MatchConfig,
    seed: int,
) -> PairEvidence:
    """Measure raw correspondence, transform, coverage, and alignment evidence."""

    matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
    forward = _ratio_matches(matcher, left.descriptors, right.descriptors, config.ratio_test)
    reverse = _ratio_matches(matcher, right.descriptors, left.descriptors, config.ratio_test)
    reverse_pairs = {(match.queryIdx, match.trainIdx) for match in reverse}
    mutual = [
        match for match in forward if (match.trainIdx, match.queryIdx) in reverse_pairs
    ]

    defaults: dict[str, Any] = {
        "model_found": False,
        "inliers": 0,
        "inlier_ratio": 0.0,
        "median_transfer_error": None,
        "grid_coverage_left": 0.0,
        "grid_coverage_right": 0.0,
        "hull_coverage_left": 0.0,
        "hull_coverage_right": 0.0,
        "coverage_min": 0.0,
        "scale": None,
        "rotation_degrees": None,
        "translation_fraction": None,
        "structural_correlation": None,
        "transform": None,
    }
    if len(mutual) >= config.min_matches_for_model:
        source = np.asarray([left.points[match.queryIdx] for match in mutual], dtype=np.float32)
        target = np.asarray([right.points[match.trainIdx] for match in mutual], dtype=np.float32)
        pair_seed = int.from_bytes(
            hashlib.sha256(f"{seed}:{left.content_hash}:{right.content_hash}".encode()).digest()[:4],
            "big",
        ) & 0x7FFFFFFF
        cv2.setRNGSeed(pair_seed)
        transform, inlier_mask = cv2.estimateAffinePartial2D(
            source,
            target,
            method=cv2.RANSAC,
            ransacReprojThreshold=config.ransac_reproj_threshold,
            maxIters=config.ransac_max_iters,
            confidence=config.ransac_confidence,
            refineIters=10,
        )
        if transform is not None and inlier_mask is not None:
            inlier_bits = inlier_mask.reshape(-1).astype(bool)
            inlier_source = source[inlier_bits]
            inlier_target = target[inlier_bits]
            predicted_target = cv2.transform(inlier_source[None, :, :], transform)[0]
            inverse = cv2.invertAffineTransform(transform)
            predicted_source = cv2.transform(inlier_target[None, :, :], inverse)[0]
            transfer_error = 0.5 * (
                np.linalg.norm(predicted_target - inlier_target, axis=1)
                + np.linalg.norm(predicted_source - inlier_source, axis=1)
            )
            grid_left = _grid_coverage(
                inlier_source, left.width, left.height, config.coverage_grid_size
            )
            grid_right = _grid_coverage(
                inlier_target, right.width, right.height, config.coverage_grid_size
            )
            hull_left = _hull_coverage(inlier_source, left.width, left.height)
            hull_right = _hull_coverage(inlier_target, right.width, right.height)
            a_value, b_value, x_translation = transform[0]
            c_value, _d_value, y_translation = transform[1]
            scale = float(math.hypot(a_value, c_value))
            rotation = float(math.degrees(math.atan2(c_value, a_value)))
            translation = float(
                math.hypot(
                    x_translation / max(right.width, 1),
                    y_translation / max(right.height, 1),
                )
            )
            defaults = {
                "model_found": True,
                "inliers": int(np.count_nonzero(inlier_bits)),
                "inlier_ratio": float(np.mean(inlier_bits)),
                "median_transfer_error": float(np.median(transfer_error)),
                "grid_coverage_left": grid_left,
                "grid_coverage_right": grid_right,
                "hull_coverage_left": hull_left,
                "hull_coverage_right": hull_right,
                "coverage_min": min(max(grid_left, hull_left), max(grid_right, hull_right)),
                "scale": scale,
                "rotation_degrees": rotation,
                "translation_fraction": translation,
                "structural_correlation": _gradient_correlation(
                    left.normalized,
                    right.normalized,
                    transform,
                    config.structural_thumbnail_size,
                ),
                "transform": transform.astype(float).tolist(),
            }

    return PairEvidence(
        left=left.filename,
        right=right.filename,
        left_keypoints=len(left.points),
        right_keypoints=len(right.points),
        forward_ratio_matches=len(forward),
        reverse_ratio_matches=len(reverse),
        mutual_matches=len(mutual),
        **defaults,
    )


def _plausible_transform(evidence: PairEvidence, config: StateConfig) -> bool:
    return bool(
        evidence.model_found
        and evidence.scale is not None
        and config.min_scale <= evidence.scale <= config.max_scale
        and evidence.rotation_degrees is not None
        and abs(evidence.rotation_degrees) <= config.max_abs_rotation_degrees
        and evidence.translation_fraction is not None
        and evidence.translation_fraction <= config.max_translation_fraction
    )


def classify_pair(evidence: PairEvidence, config: StateConfig) -> PairDecision:
    """Classify raw evidence as strong-positive, positive, negative, or unknown."""

    plausible = _plausible_transform(evidence, config)
    correlation = evidence.structural_correlation
    correlation_value = correlation if correlation is not None else -1.0
    error = evidence.median_transfer_error
    error_value = error if error is not None else math.inf
    score = float(
        np.mean(
            [
                min(1.0, evidence.inliers / max(config.strong_min_inliers, 1)),
                min(1.0, evidence.inlier_ratio / max(config.strong_min_inlier_ratio, 1e-9)),
                min(1.0, evidence.coverage_min / max(config.strong_min_coverage, 1e-9)),
                max(0.0, min(1.0, (correlation_value + 1.0) / 2.0)),
                max(0.0, 1.0 - error_value / max(config.positive_max_transfer_error, 1e-9)),
            ]
        )
    )
    if (
        plausible
        and evidence.inliers >= config.strong_min_inliers
        and evidence.inlier_ratio >= config.strong_min_inlier_ratio
        and evidence.coverage_min >= config.strong_min_coverage
        and error_value <= config.strong_max_transfer_error
        and correlation_value >= config.strong_min_structural_correlation
    ):
        return PairDecision(
            evidence.left,
            evidence.right,
            "strong_positive",
            score,
            ("coherent_high_support_geometry",),
        )
    if (
        plausible
        and evidence.inliers >= config.positive_min_inliers
        and evidence.inlier_ratio >= config.positive_min_inlier_ratio
        and evidence.coverage_min >= config.positive_min_coverage
        and error_value <= config.positive_max_transfer_error
        and correlation_value >= config.positive_min_structural_correlation
    ):
        return PairDecision(
            evidence.left,
            evidence.right,
            "positive",
            score,
            ("coherent_geometry",),
        )
    informative = (
        min(evidence.left_keypoints, evidence.right_keypoints)
        >= config.negative_min_keypoints
        and evidence.mutual_matches >= config.negative_min_mutual_matches
    )
    contradiction = informative and (
        not evidence.model_found
        or evidence.inlier_ratio <= config.negative_max_inlier_ratio
        or (
            not plausible
            and correlation_value <= config.negative_max_structural_correlation
        )
    )
    if contradiction:
        return PairDecision(
            evidence.left,
            evidence.right,
            "negative",
            score,
            ("informative_geometric_contradiction",),
        )
    return PairDecision(
        evidence.left,
        evidence.right,
        "unknown",
        score,
        ("insufficient_or_ambiguous_evidence",),
    )


def group_from_decisions(
    filenames: list[str],
    decisions: list[PairDecision],
    qualities: dict[str, float],
    config: GroupingConfig,
) -> list[list[str]]:
    """Merge only supported components while treating unknown edges as neutral."""

    ordered_names = sorted(filenames)
    clusters: dict[int, set[str]] = {
        index: {filename} for index, filename in enumerate(ordered_names)
    }
    owner = {filename: index for index, filename in enumerate(ordered_names)}
    decision_by_pair = {
        tuple(sorted((decision.left, decision.right))): decision
        for decision in decisions
    }
    candidates = sorted(
        (
            decision
            for decision in decisions
            if decision.state in {"strong_positive", "positive"}
        ),
        key=lambda decision: (
            0 if decision.state == "strong_positive" else 1,
            -decision.score,
            decision.left,
            decision.right,
        ),
    )

    def representative(members: set[str]) -> str:
        return min(members, key=lambda name: (-qualities.get(name, 0.0), name))

    def cross_decisions(left_members: set[str], right_members: set[str]) -> list[PairDecision]:
        values: list[PairDecision] = []
        for left_name in sorted(left_members):
            for right_name in sorted(right_members):
                decision = decision_by_pair.get(tuple(sorted((left_name, right_name))))
                if decision is not None:
                    values.append(decision)
        return values

    def can_merge(left_members: set[str], right_members: set[str]) -> bool:
        cross = cross_decisions(left_members, right_members)
        if config.strong_negative_veto and any(
            decision.state == "negative" for decision in cross
        ):
            return False
        support = [
            decision
            for decision in cross
            if decision.state in {"strong_positive", "positive"}
        ]
        strong = [decision for decision in support if decision.state == "strong_positive"]
        if len(left_members) == 1 and len(right_members) == 1:
            return bool(strong)
        if not strong:
            return False
        if len(left_members) == 1 or len(right_members) == 1:
            return True
        if config.representative_strong_support:
            left_rep = representative(left_members)
            right_rep = representative(right_members)
            if any(
                decision.state == "strong_positive"
                and (
                    decision.left in {left_rep, right_rep}
                    or decision.right in {left_rep, right_rep}
                )
                for decision in strong
            ):
                return True
        supported_left = {decision.left for decision in support} | {
            decision.right for decision in support
        }
        return (
            len(support) >= config.min_independent_support_edges
            and len(supported_left & left_members) >= 2
            and len(supported_left & right_members) >= 2
        )

    while True:
        changed = False
        for decision in candidates:
            left_owner = owner[decision.left]
            right_owner = owner[decision.right]
            if left_owner == right_owner:
                continue
            left_members = clusters[left_owner]
            right_members = clusters[right_owner]
            if not can_merge(left_members, right_members):
                continue
            keep = min(left_owner, right_owner)
            remove = max(left_owner, right_owner)
            clusters[keep] = clusters[left_owner] | clusters[right_owner]
            del clusters[remove]
            for filename in clusters[keep]:
                owner[filename] = keep
            changed = True
        if not changed:
            break
    return canonicalize_groups(clusters.values())


def diagnose_pair_decisions(
    reference_groups: list[list[str]], decisions: list[PairDecision]
) -> dict[str, Any]:
    """Measure tri-state pair evidence against labels without using labels as input."""

    reference_by_filename = {
        filename: group_index
        for group_index, group in enumerate(reference_groups)
        for filename in group
    }
    expected_names = set(reference_by_filename)
    decision_names = {
        filename for decision in decisions for filename in (decision.left, decision.right)
    }
    if decision_names != expected_names:
        raise ValueError("pair decisions and reference groups cover different filenames")
    expected_pair_count = len(expected_names) * (len(expected_names) - 1) // 2
    if len(decisions) != expected_pair_count:
        raise ValueError("pair decisions do not cover every unordered image pair")

    state_by_label: dict[str, Counter[str]] = {
        "different_group": Counter(),
        "same_group": Counter(),
    }
    false_positive: list[PairDecision] = []
    same_group_misses: list[PairDecision] = []
    positive_states = {"positive", "strong_positive"}
    valid_states = positive_states | {"negative", "unknown"}
    seen_pairs: set[tuple[str, str]] = set()
    for decision in decisions:
        pair = tuple(sorted((decision.left, decision.right)))
        if decision.left == decision.right or pair in seen_pairs:
            raise ValueError("pair decisions contain a duplicate or self-pair")
        if decision.state not in valid_states:
            raise ValueError(f"unsupported pair state: {decision.state}")
        seen_pairs.add(pair)
        same_group = (
            reference_by_filename[decision.left]
            == reference_by_filename[decision.right]
        )
        label = "same_group" if same_group else "different_group"
        state_by_label[label][decision.state] += 1
        if not same_group and decision.state in positive_states:
            false_positive.append(decision)
        if same_group and decision.state not in positive_states:
            same_group_misses.append(decision)

    same_total = sum(state_by_label["same_group"].values())
    different_total = sum(state_by_label["different_group"].values())
    same_positive = sum(
        state_by_label["same_group"][state] for state in positive_states
    )
    different_positive = sum(
        state_by_label["different_group"][state] for state in positive_states
    )
    positive_total = same_positive + different_positive
    different_negative = state_by_label["different_group"]["negative"]
    same_negative = state_by_label["same_group"]["negative"]
    negative_total = different_negative + same_negative
    known_total = positive_total + negative_total

    def examples(values: list[PairDecision]) -> list[dict[str, Any]]:
        return [
            asdict(decision)
            for decision in sorted(
                values,
                key=lambda item: (
                    0 if item.state == "strong_positive" else 1,
                    -item.score,
                    item.left,
                    item.right,
                ),
            )[:50]
        ]

    return {
        "pair_diagnostics_schema_version": 1,
        "pair_count": len(decisions),
        "same_group_pair_count": same_total,
        "different_group_pair_count": different_total,
        "state_by_reference_label": {
            label: dict(sorted(counts.items()))
            for label, counts in sorted(state_by_label.items())
        },
        "positive_pair_precision": (
            same_positive / positive_total if positive_total else 1.0
        ),
        "same_group_positive_recall": (
            same_positive / same_total if same_total else 1.0
        ),
        "negative_pair_precision": (
            different_negative / negative_total if negative_total else 1.0
        ),
        "different_group_negative_recall": (
            different_negative / different_total if different_total else 1.0
        ),
        "known_state_coverage": known_total / len(decisions) if decisions else 1.0,
        "false_positive_examples": examples(false_positive),
        "same_group_miss_examples": examples(same_group_misses),
    }


def run_classical(
    image_paths: list[str],
    config: ClassicalConfig,
    *,
    dataset_fingerprint: str,
    cache_root: Path,
    seed: int,
) -> ClassicalOutcome:
    """Extract or reuse features, cache all raw pair evidence, and form B2 groups."""

    ordered_paths = sorted((Path(path) for path in image_paths), key=lambda path: path.name)
    feature_cache = FeatureCache(cache_root, config.feature_fingerprint)
    percentile_stretch = (
        config.percentile_stretch
        if isinstance(config, PercentileClassicalConfig)
        else None
    )
    features: list[FeatureRecord] = []
    feature_hits = 0
    for index, path in enumerate(ordered_paths, start=1):
        content_hash = sha256_file(path)
        record, hit = feature_cache.get(
            path,
            content_hash,
            config.feature,
            percentile_stretch,
        )
        feature_hits += int(hit)
        features.append(record)
        if index == 1 or index % 50 == 0 or index == len(ordered_paths):
            print(f"B2 features {index}/{len(ordered_paths)}", flush=True)

    pair_cache = PairEvidenceCache(cache_root / "pair-evidence.sqlite3")
    evidence_values: list[PairEvidence] = []
    pair_hits = 0
    total_pairs = len(features) * (len(features) - 1) // 2
    processed = 0
    for left_index, left in enumerate(features):
        for right in features[left_index + 1 :]:
            processed += 1
            left_record, right_record = (left, right)
            left_hash, right_hash = left.content_hash, right.content_hash
            if (right_hash, right.filename) < (left_hash, left.filename):
                left_record, right_record = right, left
                left_hash, right_hash = right_hash, left_hash
            evidence = pair_cache.get(
                dataset_fingerprint,
                config.evidence_fingerprint,
                left_hash,
                right_hash,
            )
            if evidence is None:
                evidence = compute_pair_evidence(
                    left_record, right_record, config.match, seed
                )
                pair_cache.put(
                    dataset_fingerprint,
                    config.evidence_fingerprint,
                    left_hash,
                    right_hash,
                    evidence,
                )
            else:
                pair_hits += 1
                evidence = replace(
                    evidence,
                    left=left_record.filename,
                    right=right_record.filename,
                )
            evidence_values.append(evidence)
            if processed == 1 or processed % 1000 == 0 or processed == total_pairs:
                print(f"B2 pairs {processed}/{total_pairs}", flush=True)

    decisions = [classify_pair(evidence, config.state) for evidence in evidence_values]
    qualities = {feature.filename: feature.quality for feature in features}
    groups = group_from_decisions(
        [path.name for path in ordered_paths], decisions, qualities, config.grouping
    )
    state_counts = Counter(decision.state for decision in decisions)
    summary = {
        "cache_schema_version": CLASSICAL_CACHE_SCHEMA_VERSION,
        "dataset_fingerprint": dataset_fingerprint,
        "evidence_fingerprint": config.evidence_fingerprint,
        "feature_fingerprint": config.feature_fingerprint,
        "pair_cache_path": str(pair_cache.path),
        "pair_state_counts": dict(sorted(state_counts.items())),
        "strongest_pairs": [
            asdict(decision)
            for decision in sorted(
                decisions, key=lambda item: (-item.score, item.left, item.right)
            )[:50]
        ],
    }
    resources = {
        "feature_cache_hits": feature_hits,
        "feature_cache_misses": len(features) - feature_hits,
        "pair_cache_hits": pair_hits,
        "pair_cache_misses": total_pairs - pair_hits,
        "pair_state_counts": dict(sorted(state_counts.items())),
    }
    return ClassicalOutcome(
        groups=groups,
        resources=resources,
        summary=summary,
        decisions=tuple(decisions),
    )


def fuse_pair_decisions(
    *decision_sets: tuple[PairDecision, ...],
) -> tuple[PairDecision, ...]:
    """Fuse complete pair graphs while allowing either view to veto a merge."""

    if len(decision_sets) < 2:
        raise ValueError("dual-view fusion requires at least two decision sets")
    by_view = [
        {
            tuple(sorted((decision.left, decision.right))): decision
            for decision in decisions
        }
        for decisions in decision_sets
    ]
    expected_pairs = set(by_view[0])
    if any(set(view) != expected_pairs for view in by_view[1:]):
        raise ValueError("dual-view decisions must cover identical image pairs")

    state_priority = {"unknown": 0, "positive": 1, "strong_positive": 2}
    fused: list[PairDecision] = []
    for pair in sorted(expected_pairs):
        values = [view[pair] for view in by_view]
        negatives = [decision for decision in values if decision.state == "negative"]
        if negatives:
            chosen = max(negatives, key=lambda decision: (decision.score, decision.reasons))
            state = "negative"
            reason = "dual_view_negative_veto"
        else:
            if any(decision.state not in state_priority for decision in values):
                raise ValueError("dual-view decision has an unsupported state")
            chosen = max(
                values,
                key=lambda decision: (
                    state_priority[decision.state],
                    decision.score,
                    decision.reasons,
                ),
            )
            state = chosen.state
            reason = "dual_view_strongest_nonnegative_state"
        fused.append(
            PairDecision(
                left=pair[0],
                right=pair[1],
                state=state,
                score=chosen.score,
                reasons=(reason, *chosen.reasons),
            )
        )
    return tuple(fused)


def run_dual_classical(
    image_paths: list[str],
    config: PercentileClassicalConfig,
    *,
    dataset_fingerprint: str,
    cache_root: Path,
    seed: int,
) -> ClassicalOutcome:
    """Fuse baseline-CLAHE and percentile-CLAHE evidence before grouping."""

    baseline_config = ClassicalConfig(
        feature=config.feature,
        match=config.match,
        state=config.state,
        grouping=config.grouping,
    )
    baseline = run_classical(
        image_paths,
        baseline_config,
        dataset_fingerprint=dataset_fingerprint,
        cache_root=cache_root,
        seed=seed,
    )
    percentile = run_classical(
        image_paths,
        config,
        dataset_fingerprint=dataset_fingerprint,
        cache_root=cache_root,
        seed=seed,
    )
    decisions = fuse_pair_decisions(baseline.decisions, percentile.decisions)
    filenames = sorted(Path(path).name for path in image_paths)
    groups = group_from_decisions(
        filenames,
        list(decisions),
        {filename: 0.0 for filename in filenames},
        config.grouping,
    )
    state_counts = Counter(decision.state for decision in decisions)
    numeric_resource_keys = (
        "feature_cache_hits",
        "feature_cache_misses",
        "pair_cache_hits",
        "pair_cache_misses",
    )
    resources = {
        key: int(baseline.resources[key]) + int(percentile.resources[key])
        for key in numeric_resource_keys
    }
    resources["pair_state_counts"] = dict(sorted(state_counts.items()))
    resources["view_resources"] = {
        "baseline_clahe": baseline.resources,
        "percentile_clahe": percentile.resources,
    }
    summary = {
        "architecture": "dual-clahe-v1",
        "baseline_clahe": baseline.summary,
        "cache_schema_version": CLASSICAL_CACHE_SCHEMA_VERSION,
        "dataset_fingerprint": dataset_fingerprint,
        "pair_state_counts": dict(sorted(state_counts.items())),
        "percentile_clahe": percentile.summary,
        "strongest_pairs": [
            asdict(decision)
            for decision in sorted(
                decisions,
                key=lambda item: (-item.score, item.left, item.right),
            )[:50]
        ],
    }
    return ClassicalOutcome(
        groups=groups,
        resources=resources,
        summary=summary,
        decisions=decisions,
    )
