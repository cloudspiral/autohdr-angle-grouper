from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from autohdr_eval.dataset import audit_dataset
from autohdr_eval.runner import load_split, run_evaluation


def test_runner_records_and_scores_singleton_baseline(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    images = dataset / "images"
    images.mkdir(parents=True)
    for filename in ("a.jpg", "b.jpg", "c.jpg"):
        (images / filename).write_bytes(filename.encode())
    manifest = dataset / "public_manifest.csv"
    manifest.write_text(
        "group_id,filename\n0,a.jpg\n0,b.jpg\n1,c.jpg\n", encoding="utf-8"
    )
    repo_root = Path(__file__).parents[1]

    outcome = run_evaluation(
        repo_root=repo_root,
        config_path=repo_root / "configs" / "b0-singletons.json",
        dataset_root=dataset,
        manifest_path=manifest,
        artifact_root=tmp_path / "artifacts",
        registry_path=tmp_path / "registry.sqlite3",
    )

    assert outcome.metrics.exact_group_score == 0.5
    assert outcome.metrics.exact_matches == 1
    assert outcome.resources["candidate_pair_count"] == 0
    assert outcome.predictions_path.is_file()
    assert (outcome.artifact_dir / "run.json").is_file()


def test_ordinary_run_gate_rejects_protected_split(tmp_path: Path) -> None:
    split = tmp_path / "protected.json"
    split.write_text(
        json.dumps(
            {
                "dataset_fingerprint": "d" * 64,
                "limitations": [],
                "protected": True,
                "schema_version": 1,
                "seed": 0,
                "selection": {"type": "all"},
                "source_package": "fixture",
                "split_id": "final-holdout-v1",
                "unit": "photoshoot",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(PermissionError, match="final-evaluate"):
        load_split(split, dataset_fingerprint="d" * 64, allow_protected=False)


def test_runner_rejects_image_bytes_changed_after_audit(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    images = dataset / "images"
    images.mkdir(parents=True)
    image = images / "a.png"
    assert cv2.imwrite(str(image), np.zeros((4, 4, 3), dtype=np.uint8))
    manifest = dataset / "public_manifest.csv"
    manifest.write_text("group_id,filename\n0,a.png\n", encoding="utf-8")
    audit_path = tmp_path / "audit.json"
    audit_path.write_text(
        json.dumps(audit_dataset(dataset, manifest)), encoding="utf-8"
    )
    assert cv2.imwrite(str(image), np.full((4, 4, 3), 255, dtype=np.uint8))
    repo_root = Path(__file__).parents[1]

    with pytest.raises(ValueError, match="changed after audit"):
        run_evaluation(
            repo_root=repo_root,
            config_path=repo_root / "configs" / "b0-singletons.json",
            dataset_root=dataset,
            manifest_path=manifest,
            audit_path=audit_path,
            artifact_root=tmp_path / "artifacts",
            registry_path=tmp_path / "registry.sqlite3",
        )


@pytest.mark.parametrize(
    ("config_filename", "expected_pair_misses"),
    [
        ("b2-percentile-clahe.json", 1),
        ("b2-dual-clahe.json", 2),
    ],
)
def test_exposure_classical_dispatches_as_pairwise_algorithm(
    tmp_path: Path,
    config_filename: str,
    expected_pair_misses: int,
) -> None:
    repo_root = Path(__file__).parents[1]
    dataset = tmp_path / "dataset"
    images = dataset / "images"
    images.mkdir(parents=True)
    rng = np.random.default_rng(19)
    for filename in ("a.png", "b.png"):
        assert cv2.imwrite(
            str(images / filename),
            rng.integers(0, 256, size=(64, 64, 3), dtype=np.uint8),
        )
    manifest = dataset / "public_manifest.csv"
    manifest.write_text(
        "group_id,filename\n0,a.png\n1,b.png\n",
        encoding="utf-8",
    )
    audit_path = tmp_path / "audit.json"
    audit_path.write_text(json.dumps(audit_dataset(dataset, manifest)), encoding="utf-8")

    outcome = run_evaluation(
        repo_root=repo_root,
        config_path=repo_root / "configs" / "phase3" / config_filename,
        dataset_root=dataset,
        manifest_path=manifest,
        audit_path=audit_path,
        artifact_root=tmp_path / "artifacts",
        registry_path=tmp_path / "registry.sqlite3",
    )

    assert outcome.resources["candidate_pair_count"] == 1
    assert outcome.resources["pair_cache_misses"] == expected_pair_misses
