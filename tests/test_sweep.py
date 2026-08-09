from __future__ import annotations

import json
from pathlib import Path

import pytest

from autohdr_eval.sweep import (
    aggregate_candidate_runs,
    load_sweep_definition,
    rank_candidate_aggregates,
)


def run_record(
    *,
    score: float,
    exact: int,
    total: int,
    merges: int = 0,
    splits: int = 0,
    wall: float = 1.0,
) -> dict[str, object]:
    return {
        "metrics": {
            "exact_group_score": score,
            "exact_matches": exact,
            "merge_damaged_reference_groups": merges,
            "non_singleton_exact_matches": exact,
            "non_singleton_reference_groups": total,
            "split_reference_groups": splits,
            "total_reference_groups": total,
        },
        "resources": {
            "feature_cache_hits": 2,
            "feature_cache_misses": 1,
            "pair_cache_hits": 5,
            "pair_cache_misses": 3,
            "peak_rss_bytes": 100,
            "wall_seconds": wall,
        },
    }


def test_candidate_aggregation_uses_micro_mean_worst_and_resources() -> None:
    result = aggregate_candidate_runs(
        [
            run_record(score=1.0, exact=2, total=2, splits=0, wall=2.0),
            run_record(score=0.5, exact=2, total=4, splits=2, wall=3.0),
        ]
    )

    assert result["micro_exact_group_score"] == 4 / 6
    assert result["mean_fold_exact_group_score"] == 0.75
    assert result["worst_fold_exact_group_score"] == 0.5
    assert result["split_reference_groups"] == 2
    assert result["total_wall_seconds"] == 5.0
    assert result["feature_cache_hits"] == 4
    assert result["pair_cache_misses"] == 6


def test_ranking_prioritizes_zero_merges_then_exact_and_worst_fold() -> None:
    candidates = [
        {
            "candidate_id": "merge-high-score",
            "aggregate": {
                "merge_damaged_reference_groups": 1,
                "micro_exact_group_score": 1.0,
                "worst_fold_exact_group_score": 1.0,
                "micro_non_singleton_exact_group_score": 1.0,
                "split_reference_groups": 0,
                "total_wall_seconds": 1.0,
            },
        },
        {
            "candidate_id": "stable",
            "aggregate": {
                "merge_damaged_reference_groups": 0,
                "micro_exact_group_score": 0.9,
                "worst_fold_exact_group_score": 0.8,
                "micro_non_singleton_exact_group_score": 0.9,
                "split_reference_groups": 2,
                "total_wall_seconds": 3.0,
            },
        },
        {
            "candidate_id": "same-mean-worse-fold",
            "aggregate": {
                "merge_damaged_reference_groups": 0,
                "micro_exact_group_score": 0.9,
                "worst_fold_exact_group_score": 0.7,
                "micro_non_singleton_exact_group_score": 0.95,
                "split_reference_groups": 1,
                "total_wall_seconds": 2.0,
            },
        },
    ]

    assert rank_candidate_aggregates(candidates) == [
        "stable",
        "same-mean-worse-fold",
        "merge-high-score",
    ]


def test_definition_loader_enforces_fixed_selection_policy(tmp_path: Path) -> None:
    definition = {
        "candidates": [{"candidate_id": "baseline", "config": "config.json"}],
        "folds": ["fold-a.json"],
        "limitations": ["fixture"],
        "schema_version": 1,
        "selection": {
            "primary": "micro_exact_group_score",
            "require_zero_merge_damage": True,
            "tie_breaks": [
                "worst_fold_exact_group_score",
                "micro_non_singleton_exact_group_score",
                "split_reference_groups",
                "total_wall_seconds",
                "candidate_id",
            ],
        },
        "stage": "fixture",
        "sweep_id": "fixture-v1",
    }
    path = tmp_path / "sweep.json"
    path.write_text(json.dumps(definition), encoding="utf-8")

    loaded = load_sweep_definition(path)
    assert loaded.sweep_id == "fixture-v1"
    assert len(loaded.fingerprint) == 64

    definition["selection"]["require_zero_merge_damage"] = False
    path.write_text(json.dumps(definition), encoding="utf-8")
    with pytest.raises(ValueError, match="fixed policy"):
        load_sweep_definition(path)

    definition["selection"]["require_zero_merge_damage"] = True
    definition["folds"] = ["../outside.json"]
    path.write_text(json.dumps(definition), encoding="utf-8")
    with pytest.raises(ValueError, match="repository-relative"):
        load_sweep_definition(path)
