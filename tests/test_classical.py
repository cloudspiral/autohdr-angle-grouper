from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np

from autohdr_eval.classical import (
    ClassicalConfig,
    PairDecision,
    PairEvidence,
    PairEvidenceCache,
    PercentileClassicalConfig,
    PercentileStretchConfig,
    _percentile_stretch,
    classify_pair,
    diagnose_pair_decisions,
    fuse_pair_decisions,
    group_from_decisions,
    run_classical,
    run_dual_classical,
)
from autohdr_eval.config import load_config


def classical_config() -> ClassicalConfig:
    repo_root = Path(__file__).parents[1]
    config = load_config(repo_root / "configs" / "b2-classical.json")
    return ClassicalConfig.from_parameters(config.parameters)


def percentile_config() -> PercentileClassicalConfig:
    repo_root = Path(__file__).parents[1]
    config = load_config(repo_root / "configs" / "phase3" / "b2-percentile-clahe.json")
    return PercentileClassicalConfig.from_parameters(config.parameters)


def selected_classical_config() -> ClassicalConfig:
    repo_root = Path(__file__).parents[1]
    config = load_config(repo_root / "configs" / "phase2" / "b2-selected.json")
    return ClassicalConfig.from_parameters(config.parameters)


def dual_config() -> PercentileClassicalConfig:
    repo_root = Path(__file__).parents[1]
    config = load_config(repo_root / "configs" / "phase3" / "b2-dual-clahe.json")
    return PercentileClassicalConfig.from_parameters(config.parameters)


def test_percentile_architecture_has_distinct_cache_identity() -> None:
    baseline = selected_classical_config()
    candidate = percentile_config()

    assert candidate.feature == baseline.feature
    assert candidate.match == baseline.match
    assert candidate.state == baseline.state
    assert candidate.grouping == baseline.grouping
    assert candidate.feature_fingerprint != baseline.feature_fingerprint
    assert candidate.evidence_fingerprint != baseline.evidence_fingerprint


def test_percentile_stretch_is_bounded_deterministic_and_handles_flat_images() -> None:
    config = PercentileStretchConfig(low_percentile=25.0, high_percentile=75.0)
    values = np.asarray([[0, 10, 20, 30, 40]], dtype=np.uint8)

    assert _percentile_stretch(values, config).tolist() == [[0, 0, 128, 255, 255]]
    flat = np.full((3, 4), 17, dtype=np.uint8)
    stretched = _percentile_stretch(flat, config)
    assert np.array_equal(stretched, flat)
    assert stretched is not flat


def test_dual_view_fusion_keeps_strongest_state_but_honors_either_negative() -> None:
    strong = decision("a.jpg", "b.jpg", "strong_positive", 0.8)
    positive = decision("a.jpg", "b.jpg", "positive", 0.9)
    unknown = decision("a.jpg", "b.jpg", "unknown", 0.2)
    negative = decision("a.jpg", "b.jpg", "negative", 0.1)

    [selected] = fuse_pair_decisions((unknown,), (strong,), (positive,))
    [vetoed] = fuse_pair_decisions((strong,), (negative,))

    assert selected.state == "strong_positive"
    assert selected.score == strong.score
    assert selected.reasons[0] == "dual_view_strongest_nonnegative_state"
    assert vetoed.state == "negative"
    assert vetoed.reasons[0] == "dual_view_negative_veto"


def test_dual_classical_reuses_both_view_cache_layers(tmp_path: Path) -> None:
    rng = np.random.default_rng(23)
    source = tmp_path / "a.png"
    assert cv2.imwrite(
        str(source),
        rng.integers(0, 256, size=(180, 240, 3), dtype=np.uint8),
    )
    copy = tmp_path / "b.png"
    shutil.copyfile(source, copy)

    first = run_dual_classical(
        [str(source), str(copy)],
        dual_config(),
        dataset_fingerprint="a" * 64,
        cache_root=tmp_path / "cache",
        seed=0,
    )
    second = run_dual_classical(
        [str(copy), str(source)],
        dual_config(),
        dataset_fingerprint="a" * 64,
        cache_root=tmp_path / "cache",
        seed=0,
    )

    assert first.groups == [["a.png", "b.png"]]
    assert second.groups == first.groups
    assert first.resources["feature_cache_hits"] == 2
    assert first.resources["feature_cache_misses"] == 2
    assert first.resources["pair_cache_misses"] == 2
    assert second.resources["feature_cache_hits"] == 4
    assert second.resources["pair_cache_hits"] == 2


def evidence(left: str = "a.jpg", right: str = "b.jpg") -> PairEvidence:
    return PairEvidence(
        left=left,
        right=right,
        left_keypoints=200,
        right_keypoints=180,
        forward_ratio_matches=40,
        reverse_ratio_matches=38,
        mutual_matches=32,
        model_found=True,
        inliers=24,
        inlier_ratio=0.75,
        median_transfer_error=1.0,
        grid_coverage_left=0.25,
        grid_coverage_right=0.25,
        hull_coverage_left=0.2,
        hull_coverage_right=0.2,
        coverage_min=0.25,
        scale=1.0,
        rotation_degrees=0.5,
        translation_fraction=0.02,
        structural_correlation=0.8,
        transform=[[1.0, 0.0, 2.0], [0.0, 1.0, 1.0]],
    )


def decision(left: str, right: str, state: str, score: float = 0.9) -> PairDecision:
    return PairDecision(left, right, state, score, ("fixture",))


def test_pair_classification_distinguishes_strong_negative_and_unknown() -> None:
    config = classical_config().state

    strong = classify_pair(evidence(), config)
    negative = classify_pair(
        replace(
            evidence(),
            model_found=False,
            inliers=0,
            inlier_ratio=0.0,
            median_transfer_error=None,
            coverage_min=0.0,
            scale=None,
            rotation_degrees=None,
            translation_fraction=None,
            structural_correlation=None,
            transform=None,
        ),
        config,
    )
    unknown = classify_pair(
        replace(
            evidence(),
            left_keypoints=4,
            right_keypoints=5,
            forward_ratio_matches=0,
            reverse_ratio_matches=0,
            mutual_matches=0,
            model_found=False,
            inliers=0,
            inlier_ratio=0.0,
            median_transfer_error=None,
            coverage_min=0.0,
            scale=None,
            rotation_degrees=None,
            translation_fraction=None,
            structural_correlation=None,
            transform=None,
        ),
        config,
    )

    assert strong.state == "strong_positive"
    assert negative.state == "negative"
    assert unknown.state == "unknown"


def test_support_aware_grouping_allows_unknown_chain_but_honors_negative_veto() -> None:
    config = classical_config().grouping
    qualities = {"a.jpg": 1.0, "b.jpg": 3.0, "c.jpg": 2.0}
    chain = [
        decision("a.jpg", "b.jpg", "strong_positive"),
        decision("b.jpg", "c.jpg", "strong_positive"),
        decision("a.jpg", "c.jpg", "unknown", 0.0),
    ]

    accepted = group_from_decisions(
        ["c.jpg", "a.jpg", "b.jpg"], list(reversed(chain)), qualities, config
    )
    vetoed = group_from_decisions(
        ["a.jpg", "b.jpg", "c.jpg"],
        chain[:2] + [decision("a.jpg", "c.jpg", "negative", 0.1)],
        qualities,
        config,
    )

    assert accepted == [["a.jpg", "b.jpg", "c.jpg"]]
    assert vetoed == [["a.jpg", "b.jpg"], ["c.jpg"]]


def test_pair_evidence_cache_round_trips_raw_measurements(tmp_path: Path) -> None:
    cache = PairEvidenceCache(tmp_path / "pair-evidence.sqlite3")
    expected = evidence()

    assert cache.get("d" * 64, "e" * 64, "a" * 64, "b" * 64) is None
    cache.put("d" * 64, "e" * 64, "a" * 64, "b" * 64, expected)

    assert cache.get("d" * 64, "e" * 64, "a" * 64, "b" * 64) == expected


def test_pair_diagnostics_separate_evidence_precision_and_recall() -> None:
    result = diagnose_pair_decisions(
        [["a.jpg", "b.jpg"], ["c.jpg"]],
        [
            decision("a.jpg", "b.jpg", "strong_positive", 0.95),
            decision("a.jpg", "c.jpg", "positive", 0.75),
            decision("b.jpg", "c.jpg", "unknown", 0.1),
        ],
    )

    assert result["pair_count"] == 3
    assert result["same_group_pair_count"] == 1
    assert result["different_group_pair_count"] == 2
    assert result["positive_pair_precision"] == 0.5
    assert result["same_group_positive_recall"] == 1.0
    assert result["known_state_coverage"] == 2 / 3
    assert result["false_positive_examples"][0]["left"] == "a.jpg"
    assert result["same_group_miss_examples"] == []


def test_pair_diagnostics_measure_partial_candidate_recall_and_connectivity() -> None:
    result = diagnose_pair_decisions(
        [["a.jpg", "b.jpg", "c.jpg"], ["d.jpg"]],
        [
            decision("a.jpg", "b.jpg", "strong_positive", 0.95),
            decision("b.jpg", "c.jpg", "positive", 0.75),
        ],
        require_complete=False,
    )

    assert result["pair_count"] == 2
    assert result["all_pair_count"] == 6
    assert result["candidate_pair_fraction"] == 1 / 3
    assert result["candidate_same_group_pair_recall"] == 2 / 3
    assert result["candidate_true_group_connectivity"] == {
        "connected_groups": 2,
        "total_groups": 2,
    }


def test_identical_content_reuses_pair_measurement_but_rebinds_filenames(
    tmp_path: Path,
) -> None:
    rng = np.random.default_rng(11)
    source = tmp_path / "a.png"
    assert cv2.imwrite(
        str(source), rng.integers(0, 256, size=(180, 240, 3), dtype=np.uint8)
    )
    paths = [source, tmp_path / "b.png", tmp_path / "c.png"]
    shutil.copyfile(source, paths[1])
    shutil.copyfile(source, paths[2])

    result = run_classical(
        [str(path) for path in paths],
        classical_config(),
        dataset_fingerprint="f" * 64,
        cache_root=tmp_path / "cache",
        seed=0,
    )

    assert result.groups == [["a.png", "b.png", "c.png"]]
    assert result.resources["pair_cache_misses"] == 1
    assert result.resources["pair_cache_hits"] == 2
    assert {
        tuple(sorted((item.left, item.right))) for item in result.decisions
    } == {("a.png", "b.png"), ("a.png", "c.png"), ("b.png", "c.png")}


def test_classical_pipeline_groups_exposures_and_reuses_both_cache_layers(
    tmp_path: Path,
) -> None:
    rng = np.random.default_rng(7)
    scene = rng.integers(20, 210, size=(220, 300, 3), dtype=np.uint8)
    cv2.rectangle(scene, (30, 40), (180, 190), (240, 180, 80), 8)
    cv2.circle(scene, (230, 90), 35, (30, 240, 210), 6)
    different = rng.integers(20, 210, size=(220, 300, 3), dtype=np.uint8)
    cv2.line(different, (0, 0), (299, 219), (255, 255, 255), 10)

    image_dir = tmp_path / "images"
    image_dir.mkdir()
    paths = [
        image_dir / "dark.png",
        image_dir / "bright.png",
        image_dir / "different.png",
    ]
    assert cv2.imwrite(str(paths[0]), np.clip(scene * 0.55, 0, 255).astype(np.uint8))
    assert cv2.imwrite(
        str(paths[1]), np.clip(scene.astype(np.float32) * 1.35, 0, 255).astype(np.uint8)
    )
    assert cv2.imwrite(str(paths[2]), different)

    config = classical_config()
    first = run_classical(
        [str(path) for path in reversed(paths)],
        config,
        dataset_fingerprint="d" * 64,
        cache_root=tmp_path / "cache",
        seed=0,
    )
    second = run_classical(
        [str(path) for path in paths],
        config,
        dataset_fingerprint="d" * 64,
        cache_root=tmp_path / "cache",
        seed=0,
    )

    assert first.groups == [["bright.png", "dark.png"], ["different.png"]]
    assert second.groups == first.groups
    assert first.resources["feature_cache_misses"] == 3
    assert first.resources["pair_cache_misses"] == 3
    assert second.resources["feature_cache_hits"] == 3
    assert second.resources["pair_cache_hits"] == 3


def test_classical_pipeline_evaluates_only_preselected_candidate_pairs(
    tmp_path: Path,
) -> None:
    rng = np.random.default_rng(31)
    source = tmp_path / "a.png"
    assert cv2.imwrite(
        str(source), rng.integers(0, 256, size=(180, 240, 3), dtype=np.uint8)
    )
    copy = tmp_path / "b.png"
    different = tmp_path / "c.png"
    shutil.copyfile(source, copy)
    assert cv2.imwrite(
        str(different), rng.integers(0, 256, size=(180, 240, 3), dtype=np.uint8)
    )

    result = run_classical(
        [str(source), str(copy), str(different)],
        classical_config(),
        dataset_fingerprint="e" * 64,
        cache_root=tmp_path / "cache",
        seed=0,
        candidate_pairs={("a.png", "b.png")},
    )

    assert result.groups == [["a.png", "b.png"], ["c.png"]]
    assert len(result.decisions) == 1
    assert result.resources["candidate_pair_count"] == 1
    assert result.resources["all_pair_count"] == 3
