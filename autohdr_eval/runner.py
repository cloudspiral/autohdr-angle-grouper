"""Reproducible B0/B1 evaluation execution and protected-holdout gating."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import random
import re
import resource
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from autohdr_eval.config import EvaluationConfig, canonical_json_bytes, load_config
from autohdr_eval.contracts import canonicalize_groups, write_predictions
from autohdr_eval.dataset import (
    SUPPORTED_SUFFIXES,
    dataset_fingerprint,
    read_manifest,
    sha256_file,
)
from autohdr_eval.registry import RunRegistry
from autohdr_eval.scoring import ScoreResult, diagnose_groups, score_groups

CACHE_SCHEMA_VERSIONS = {"dataset": 1, "predictions": 1, "run": 1}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _git_state(repo_root: Path) -> tuple[str, bool]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return commit, bool(status.strip())


def _peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def _environment() -> dict[str, str]:
    return {
        "opencv": cv2.__version__,
        "numpy": np.__version__,
        "platform": platform.platform(),
        "python": platform.python_version(),
    }


def _fingerprint_selected_dataset(manifest_path: Path, image_paths: list[str]) -> str:
    image_hashes = {
        Path(image_path).name: sha256_file(Path(image_path))
        for image_path in image_paths
    }
    return dataset_fingerprint(manifest_path, image_hashes)


def _load_audit_fingerprint(
    audit_path: Path, manifest_path: Path, image_paths: list[str]
) -> str:
    with audit_path.open(encoding="utf-8") as input_file:
        audit = json.load(input_file)
    if not isinstance(audit, dict):
        raise ValueError("audit must be a JSON object")
    if audit.get("audit_schema_version") != 1:
        raise ValueError("unsupported dataset audit schema")
    current_manifest_hash = sha256_file(manifest_path)
    if audit.get("manifest_sha256") != current_manifest_hash:
        raise ValueError("audit manifest hash does not match the requested manifest")
    unsafe_fields = {
        "corrupt_images": audit.get("corrupt_images", []),
        "duplicate_basenames": audit.get("duplicate_basenames", []),
        "extra_images": audit.get("extra_images", []),
        "missing_images": audit.get("missing_images", []),
    }
    if any(unsafe_fields.values()):
        raise ValueError(f"dataset audit contains blocking integrity failures: {unsafe_fields}")
    audited_hashes = audit.get("image_sha256")
    if not isinstance(audited_hashes, dict) or not all(
        isinstance(filename, str)
        and isinstance(file_hash, str)
        and re.fullmatch(r"[0-9a-f]{64}", file_hash) is not None
        for filename, file_hash in audited_hashes.items()
    ):
        raise ValueError("audit does not contain valid per-image SHA-256 values")
    current_names = {Path(image_path).name for image_path in image_paths}
    if set(audited_hashes) != current_names:
        raise ValueError("audit image inventory does not match the requested dataset")
    changed_images = sorted(
        Path(image_path).name
        for image_path in image_paths
        if sha256_file(Path(image_path)) != audited_hashes[Path(image_path).name]
    )
    if changed_images:
        raise ValueError(f"image bytes changed after audit: {changed_images}")

    fingerprint = audit.get("dataset_fingerprint")
    current_fingerprint = dataset_fingerprint(manifest_path, audited_hashes)
    if (
        not isinstance(fingerprint, str)
        or re.fullmatch(r"[0-9a-f]{64}", fingerprint) is None
        or fingerprint != current_fingerprint
    ):
        raise ValueError("audit does not contain a valid dataset fingerprint")
    return fingerprint


def load_split(
    path: Path | None,
    *,
    dataset_fingerprint: str,
    allow_protected: bool,
) -> tuple[dict[str, Any], str]:
    if path is None:
        raw: dict[str, Any] = {
            "dataset_fingerprint": dataset_fingerprint,
            "limitations": ["No committed split specification was supplied."],
            "protected": False,
            "schema_version": 1,
            "seed": 0,
            "selection": {"type": "all"},
            "source_package": "uncommitted",
            "split_id": "unpartitioned-smoke",
            "unit": "unknown",
        }
    else:
        with path.open(encoding="utf-8") as split_file:
            raw = json.load(split_file)
    if not isinstance(raw, dict):
        raise ValueError("split must be a JSON object")
    required = {
        "dataset_fingerprint",
        "limitations",
        "protected",
        "schema_version",
        "seed",
        "selection",
        "source_package",
        "split_id",
        "unit",
    }
    if set(raw) != required:
        raise ValueError(f"split keys must be exactly {sorted(required)}")
    if type(raw["schema_version"]) is not int or raw["schema_version"] != 1:
        raise ValueError(f"unsupported split schema: {raw['schema_version']}")
    if not isinstance(raw["dataset_fingerprint"], str) or not re.fullmatch(
        r"[0-9a-f]{64}", raw["dataset_fingerprint"]
    ):
        raise ValueError("split dataset_fingerprint must be a lowercase SHA-256")
    if raw["dataset_fingerprint"] != dataset_fingerprint:
        raise ValueError("split dataset fingerprint does not match the audited dataset")
    if not isinstance(raw["protected"], bool):
        raise ValueError("split protected must be a boolean")
    if raw["protected"] and not allow_protected:
        raise PermissionError(
            "protected splits require the separate final-evaluate command"
        )
    if not isinstance(raw["split_id"], str) or not re.fullmatch(
        r"[A-Za-z0-9._-]+", raw["split_id"]
    ):
        raise ValueError("split_id contains unsupported characters")
    if type(raw["seed"]) is not int:
        raise ValueError("split seed must be an integer")
    if not isinstance(raw["source_package"], str) or not raw["source_package"]:
        raise ValueError("split source_package must be a non-empty string")
    if not isinstance(raw["unit"], str) or not raw["unit"]:
        raise ValueError("split unit must be a non-empty string")
    if not isinstance(raw["limitations"], list) or not all(
        isinstance(limitation, str) for limitation in raw["limitations"]
    ):
        raise ValueError("split limitations must be a string list")
    if not isinstance(raw["selection"], dict):
        raise ValueError("split selection must be an object")
    return raw, hashlib.sha256(canonical_json_bytes(raw)).hexdigest()


def _resolve_reference_and_paths(
    dataset_root: Path,
    manifest_path: Path,
    split: dict[str, Any],
) -> tuple[list[list[str]], list[str]]:
    rows, _ = read_manifest(manifest_path)
    selection = split["selection"]
    selection_type = selection.get("type")
    if selection_type == "all":
        if set(selection) != {"type"}:
            raise ValueError("all selection only accepts the type field")
        selected_rows = rows
    elif selection_type == "group_ids":
        if set(selection) != {"type", "values"}:
            raise ValueError("group_ids selection requires exactly type and values")
        group_ids = selection.get("values")
        if not isinstance(group_ids, list) or not all(
            isinstance(group_id, str) for group_id in group_ids
        ):
            raise ValueError("group_ids selection requires a string values list")
        if not group_ids or len(group_ids) != len(set(group_ids)):
            raise ValueError("group_ids selection values must be non-empty and unique")
        selected = set(group_ids)
        selected_rows = [row for row in rows if row["group_id"] in selected]
        if {row["group_id"] for row in selected_rows} != selected:
            raise ValueError("split references group IDs absent from the manifest")
    else:
        raise ValueError(f"unsupported split selection type: {selection_type}")
    if not selected_rows:
        raise ValueError("split selection contains no manifest rows")

    discovered: dict[str, list[Path]] = {}
    for path in dataset_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            discovered.setdefault(path.name, []).append(path)
    expected = sorted(row["filename"] for row in selected_rows)
    ambiguous = sorted(name for name in expected if len(discovered.get(name, [])) != 1)
    if ambiguous:
        raise ValueError(f"selected images are missing or have duplicate basenames: {ambiguous}")

    grouped: dict[str, list[str]] = {}
    for row in selected_rows:
        grouped.setdefault(row["group_id"], []).append(row["filename"])
    reference_groups = canonicalize_groups(grouped.values())
    image_paths = [str(discovered[filename][0]) for filename in expected]
    return reference_groups, image_paths


@dataclass(frozen=True)
class PredictionOutcome:
    groups: list[list[str]]
    resources: dict[str, Any]
    artifacts: dict[str, Any]
    pair_decisions: tuple[Any, ...] = ()


def _predict(
    config: EvaluationConfig,
    image_paths: list[str],
    *,
    dataset_fingerprint: str,
    cache_root: Path,
) -> PredictionOutcome:
    if config.algorithm == "singleton":
        if config.parameters:
            raise ValueError("singleton baseline does not accept parameters")
        return PredictionOutcome(
            groups=[[Path(path).name] for path in sorted(image_paths)],
            resources={},
            artifacts={},
        )
    if config.algorithm == "structural":
        from solution import StructuralConfig, group_images_with_config

        structural_config = StructuralConfig.from_parameters(config.parameters)
        return PredictionOutcome(
            groups=group_images_with_config(image_paths, structural_config),
            resources={},
            artifacts={},
        )
    if config.algorithm in {"classical", "classical-percentile-clahe"}:
        from autohdr_eval.classical import (
            ClassicalConfig,
            PercentileClassicalConfig,
            run_classical,
        )

        config_type = (
            PercentileClassicalConfig
            if config.algorithm == "classical-percentile-clahe"
            else ClassicalConfig
        )
        classical_config = config_type.from_parameters(config.parameters)
        classical = run_classical(
            image_paths,
            classical_config,
            dataset_fingerprint=dataset_fingerprint,
            cache_root=cache_root,
            seed=config.seed,
        )
        return PredictionOutcome(
            groups=classical.groups,
            resources=classical.resources,
            artifacts={"classical_summary": classical.summary},
            pair_decisions=classical.decisions,
        )
    raise ValueError(f"unsupported algorithm: {config.algorithm}")


@dataclass(frozen=True)
class RunOutcome:
    run_id: str
    artifact_dir: Path
    predictions_path: Path
    metrics: ScoreResult
    resources: dict[str, Any]


def run_evaluation(
    *,
    repo_root: Path,
    config_path: Path,
    dataset_root: Path,
    manifest_path: Path,
    artifact_root: Path,
    registry_path: Path,
    audit_path: Path | None = None,
    split_path: Path | None = None,
    allow_protected: bool = False,
) -> RunOutcome:
    """Run one config on one audited split and persist all evidence."""

    config = load_config(config_path)
    random.seed(config.seed)
    np.random.seed(config.seed)
    _, all_paths = _resolve_reference_and_paths(
        dataset_root,
        manifest_path,
        {"selection": {"type": "all"}},
    )
    dataset_fingerprint = (
        _load_audit_fingerprint(audit_path, manifest_path, all_paths)
        if audit_path is not None
        else _fingerprint_selected_dataset(manifest_path, all_paths)
    )
    split, split_fingerprint = load_split(
        split_path,
        dataset_fingerprint=dataset_fingerprint,
        allow_protected=allow_protected,
    )
    reference_groups, image_paths = _resolve_reference_and_paths(
        dataset_root, manifest_path, split
    )
    git_commit, dirty_tree = _git_state(repo_root)

    started_at = _utc_now()
    identity = hashlib.sha256(
        f"{time.time_ns()}:{config.fingerprint}:{dataset_fingerprint}:{split_fingerprint}".encode()
    ).hexdigest()[:10]
    run_id = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{config.name}-{identity}"
    artifact_dir = (
        artifact_root
        / dataset_fingerprint[:12]
        / config.fingerprint[:12]
        / run_id
    )
    registry = RunRegistry(registry_path)
    if split["protected"] and registry.contains_split(split["split_id"]):
        raise PermissionError(
            f"protected split {split['split_id']} already has a run registry entry"
        )
    artifact_dir.mkdir(parents=True, exist_ok=False)
    registry.start(
        {
            "cache_schema_versions": CACHE_SCHEMA_VERSIONS,
            "config_hash": config.fingerprint,
            "config_path": str(config_path),
            "dataset_fingerprint": dataset_fingerprint,
            "dirty_tree": dirty_tree,
            "git_commit": git_commit,
            "run_id": run_id,
            "seed": config.seed,
            "split_fingerprint": split_fingerprint,
            "split_id": split["split_id"],
            "started_at": started_at,
        }
    )

    predictions_path = artifact_dir / "predictions.csv"
    started_clock = time.perf_counter()
    try:
        prediction = _predict(
            config,
            image_paths,
            dataset_fingerprint=dataset_fingerprint,
            cache_root=artifact_root.parent / "cache",
        )
        predicted_groups = prediction.groups
        write_predictions(predicted_groups, image_paths, predictions_path)
        metrics = score_groups(reference_groups, predicted_groups)
        diagnostics = diagnose_groups(reference_groups, predicted_groups)
        if prediction.pair_decisions:
            from autohdr_eval.classical import diagnose_pair_decisions

            prediction.artifacts["pair_diagnostics"] = diagnose_pair_decisions(
                reference_groups, list(prediction.pair_decisions)
            )
        resources = {
            "candidate_pair_count": (
                len(image_paths) * (len(image_paths) - 1) // 2
                if config.algorithm
                in {"classical", "classical-percentile-clahe", "structural"}
                else 0
            ),
            "image_count": len(image_paths),
            "peak_rss_bytes": _peak_rss_bytes(),
            "predicted_group_count": len(predicted_groups),
            "wall_seconds": time.perf_counter() - started_clock,
        }
        resources.update(prediction.resources)
        _write_json(artifact_dir / "resolved_config.json", config.as_dict())
        _write_json(artifact_dir / "split.json", split)
        _write_json(artifact_dir / "metrics.json", metrics.as_dict())
        _write_json(artifact_dir / "diagnostics.json", diagnostics)
        _write_json(artifact_dir / "resources.json", resources)
        _write_json(artifact_dir / "environment.json", _environment())
        for artifact_name, artifact_value in prediction.artifacts.items():
            _write_json(artifact_dir / f"{artifact_name}.json", artifact_value)
        run_summary = {
            "config_hash": config.fingerprint,
            "dataset_fingerprint": dataset_fingerprint,
            "dirty_tree": dirty_tree,
            "finished_at": _utc_now(),
            "git_commit": git_commit,
            "metrics": metrics.as_dict(),
            "resources": resources,
            "run_id": run_id,
            "split_fingerprint": split_fingerprint,
            "split_id": split["split_id"],
            "started_at": started_at,
            "status": "passed",
        }
        _write_json(artifact_dir / "run.json", run_summary)
        artifact_paths = {
            "diagnostics": str(artifact_dir / "diagnostics.json"),
            "environment": str(artifact_dir / "environment.json"),
            "metrics": str(artifact_dir / "metrics.json"),
            "predictions": str(predictions_path),
            "resolved_config": str(artifact_dir / "resolved_config.json"),
            "run": str(artifact_dir / "run.json"),
            "split": str(artifact_dir / "split.json"),
        }
        artifact_paths.update(
            {
                artifact_name: str(artifact_dir / f"{artifact_name}.json")
                for artifact_name in prediction.artifacts
            }
        )
        registry.finish(
            run_id,
            finished_at=run_summary["finished_at"],
            status="passed",
            metrics=metrics.as_dict(),
            resources=resources,
            artifact_paths=artifact_paths,
        )
    except Exception as error:
        registry.finish(
            run_id,
            finished_at=_utc_now(),
            status="failed",
            resources={"wall_seconds": time.perf_counter() - started_clock},
            notes=f"{type(error).__name__}: {error}",
        )
        raise

    return RunOutcome(
        run_id=run_id,
        artifact_dir=artifact_dir,
        predictions_path=predictions_path,
        metrics=metrics,
        resources=resources,
    )


def validate_frozen_evaluation(
    *,
    repo_root: Path,
    config_path: Path,
    split_path: Path,
    frozen_commit: str,
    expected_config_hash: str,
    expected_split_fingerprint: str,
) -> None:
    """Fail closed before a one-time protected-holdout evaluation."""

    git_commit, dirty_tree = _git_state(repo_root)
    if dirty_tree:
        raise ValueError("final evaluation requires a clean working tree")
    if git_commit != frozen_commit:
        raise ValueError(f"HEAD {git_commit} does not match frozen commit {frozen_commit}")
    config = load_config(config_path)
    if config.fingerprint != expected_config_hash:
        raise ValueError("config hash does not match the frozen config hash")
    with split_path.open(encoding="utf-8") as split_file:
        split = json.load(split_file)
    split_fingerprint = hashlib.sha256(canonical_json_bytes(split)).hexdigest()
    if split_fingerprint != expected_split_fingerprint:
        raise ValueError("split file hash does not match the frozen split hash")
    if split.get("protected") is not True:
        raise ValueError("final-evaluate requires a protected split")


def deterministic_runtime_environment() -> None:
    """Apply conservative thread controls before CPU-heavy native libraries run."""

    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    cv2.setNumThreads(1)
