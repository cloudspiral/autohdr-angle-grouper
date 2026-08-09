from __future__ import annotations

import json
from pathlib import Path

import pytest

from autohdr_eval.classical import ScreenedPercentileClassicalConfig
from autohdr_eval.config import load_config
from autohdr_eval.registry import RunRegistry
from solution import SUBMISSION_CONFIG_PATH, StructuralConfig


def test_committed_structural_config_matches_solution_defaults() -> None:
    repo_root = Path(__file__).parents[1]
    config = load_config(repo_root / "configs" / "b1-structural.json")

    assert StructuralConfig.from_parameters(config.parameters) == StructuralConfig()
    assert len(config.fingerprint) == 64


def test_submission_config_strictly_extends_frozen_dual_view_parameters() -> None:
    repo_root = Path(__file__).parents[1]
    phase3 = load_config(repo_root / "configs" / "phase3" / "b2-dual-clahe.json")
    phase4 = load_config(SUBMISSION_CONFIG_PATH)
    parsed = ScreenedPercentileClassicalConfig.from_parameters(phase4.parameters)

    assert phase4.algorithm == "classical-screened-dual-clahe"
    assert {
        key: value
        for key, value in phase4.parameters.items()
        if key != "candidate_screen"
    } == phase3.parameters
    assert parsed.candidate_screen.all_pairs_max_images == 64
    assert parsed.candidate_screen.top_k == 12
    assert parsed.candidate_screen.structural == phase3_structural_parameters(repo_root)


def phase3_structural_parameters(repo_root: Path) -> dict[str, object]:
    return load_config(repo_root / "configs" / "b1-structural.json").parameters


def test_config_fingerprint_is_independent_of_json_key_order(tmp_path: Path) -> None:
    left = tmp_path / "left.json"
    right = tmp_path / "right.json"
    config = {
        "schema_version": 1,
        "name": "b0",
        "algorithm": "singleton",
        "seed": 0,
        "parameters": {},
    }
    left.write_text(json.dumps(config), encoding="utf-8")
    right.write_text(json.dumps(dict(reversed(list(config.items())))), encoding="utf-8")

    assert load_config(left).fingerprint == load_config(right).fingerprint


def test_config_rejects_unknown_keys(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps(
            {
                "algorithm": "singleton",
                "extra": True,
                "name": "b0",
                "parameters": {},
                "schema_version": 1,
                "seed": 0,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="config keys"):
        load_config(path)


def test_registry_records_run_lifecycle(tmp_path: Path) -> None:
    registry = RunRegistry(tmp_path / "runs.sqlite3")
    registry.start(
        {
            "config_hash": "c" * 64,
            "config_path": "configs/b0.json",
            "dataset_fingerprint": "d" * 64,
            "dirty_tree": True,
            "git_commit": "a" * 40,
            "run_id": "run-1",
            "seed": 0,
            "split_id": "smoke",
            "started_at": "2026-08-08T00:00:00+00:00",
        }
    )
    registry.finish(
        "run-1",
        finished_at="2026-08-08T00:00:01+00:00",
        status="passed",
        metrics={"exact_group_score": 0.5},
    )

    [run] = registry.recent()
    assert run["status"] == "passed"
    assert run["dirty_tree"] is True
    assert run["metrics"] == {"exact_group_score": 0.5}
    assert registry.contains_split("smoke") is True
    assert registry.contains_split("unknown") is False
