"""Reproducible multi-fold configuration sweeps for classical experiments."""

from __future__ import annotations

import hashlib
import json
import statistics
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from autohdr_eval.config import canonical_json_bytes, load_config
from autohdr_eval.runner import run_evaluation

_SELECTION = {
    "primary": "micro_exact_group_score",
    "require_zero_merge_damage": True,
    "tie_breaks": [
        "worst_fold_exact_group_score",
        "micro_non_singleton_exact_group_score",
        "split_reference_groups",
        "total_wall_seconds",
        "candidate_id",
    ],
}


@dataclass(frozen=True)
class SweepCandidate:
    candidate_id: str
    config_path: str


@dataclass(frozen=True)
class SweepDefinition:
    sweep_id: str
    stage: str
    folds: tuple[str, ...]
    candidates: tuple[SweepCandidate, ...]
    limitations: tuple[str, ...]
    fingerprint: str


def _validate_repo_path(value: str, name: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value in {"", "."}:
        raise ValueError(f"{name} must be a safe repository-relative path")
    return value


def load_sweep_definition(path: Path) -> SweepDefinition:
    """Load a strict sweep definition and fingerprint its canonical contents."""

    with path.open(encoding="utf-8") as input_file:
        raw = json.load(input_file)
    if not isinstance(raw, dict):
        raise ValueError("sweep definition must be a JSON object")
    required = {
        "candidates",
        "folds",
        "limitations",
        "schema_version",
        "selection",
        "stage",
        "sweep_id",
    }
    if set(raw) != required:
        raise ValueError(f"sweep definition keys must be exactly {sorted(required)}")
    if type(raw["schema_version"]) is not int or raw["schema_version"] != 1:
        raise ValueError("unsupported sweep definition schema")
    if raw["selection"] != _SELECTION:
        raise ValueError("sweep selection policy must match the fixed policy")
    if not isinstance(raw["sweep_id"], str) or not raw["sweep_id"]:
        raise ValueError("sweep_id must be a non-empty string")
    if not isinstance(raw["stage"], str) or not raw["stage"]:
        raise ValueError("sweep stage must be a non-empty string")
    folds = raw["folds"]
    if (
        not isinstance(folds, list)
        or not folds
        or not all(isinstance(item, str) and item for item in folds)
        or len(folds) != len(set(folds))
    ):
        raise ValueError("sweep folds must be unique non-empty path strings")
    folds = [_validate_repo_path(item, "fold") for item in folds]
    limitations = raw["limitations"]
    if not isinstance(limitations, list) or not limitations or not all(
        isinstance(item, str) and item for item in limitations
    ):
        raise ValueError("sweep limitations must be non-empty strings")
    candidates_raw = raw["candidates"]
    if not isinstance(candidates_raw, list) or not candidates_raw:
        raise ValueError("sweep candidates must be a non-empty list")
    candidates: list[SweepCandidate] = []
    for item in candidates_raw:
        if not isinstance(item, dict) or set(item) != {"candidate_id", "config"}:
            raise ValueError("each sweep candidate requires candidate_id and config")
        candidate_id = item["candidate_id"]
        config_path = item["config"]
        if not isinstance(candidate_id, str) or not candidate_id:
            raise ValueError("candidate_id must be a non-empty string")
        if not isinstance(config_path, str) or not config_path:
            raise ValueError("candidate config must be a non-empty path string")
        candidates.append(
            SweepCandidate(
                candidate_id,
                _validate_repo_path(config_path, "candidate config"),
            )
        )
    candidate_ids = [candidate.candidate_id for candidate in candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("sweep candidate IDs must be unique")
    return SweepDefinition(
        sweep_id=raw["sweep_id"],
        stage=raw["stage"],
        folds=tuple(folds),
        candidates=tuple(candidates),
        limitations=tuple(limitations),
        fingerprint=hashlib.sha256(canonical_json_bytes(raw)).hexdigest(),
    )


def aggregate_candidate_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate fold metrics with micro, mean, worst-fold, and resource views."""

    if not runs:
        raise ValueError("cannot aggregate an empty candidate run list")
    total_reference = sum(run["metrics"]["total_reference_groups"] for run in runs)
    total_exact = sum(run["metrics"]["exact_matches"] for run in runs)
    total_non_singleton = sum(
        run["metrics"]["non_singleton_reference_groups"] for run in runs
    )
    total_non_singleton_exact = sum(
        run["metrics"]["non_singleton_exact_matches"] for run in runs
    )
    fold_scores = [run["metrics"]["exact_group_score"] for run in runs]
    return {
        "fold_count": len(runs),
        "micro_exact_group_score": (
            total_exact / total_reference if total_reference else 1.0
        ),
        "mean_fold_exact_group_score": statistics.fmean(fold_scores),
        "worst_fold_exact_group_score": min(fold_scores),
        "exact_matches": total_exact,
        "total_reference_groups": total_reference,
        "micro_non_singleton_exact_group_score": (
            total_non_singleton_exact / total_non_singleton
            if total_non_singleton
            else 1.0
        ),
        "non_singleton_exact_matches": total_non_singleton_exact,
        "non_singleton_reference_groups": total_non_singleton,
        "merge_damaged_reference_groups": sum(
            run["metrics"]["merge_damaged_reference_groups"] for run in runs
        ),
        "split_reference_groups": sum(
            run["metrics"]["split_reference_groups"] for run in runs
        ),
        "total_wall_seconds": sum(run["resources"]["wall_seconds"] for run in runs),
        "maximum_peak_rss_bytes": max(
            run["resources"]["peak_rss_bytes"] for run in runs
        ),
        "feature_cache_hits": sum(
            run["resources"].get("feature_cache_hits", 0) for run in runs
        ),
        "feature_cache_misses": sum(
            run["resources"].get("feature_cache_misses", 0) for run in runs
        ),
        "pair_cache_hits": sum(
            run["resources"].get("pair_cache_hits", 0) for run in runs
        ),
        "pair_cache_misses": sum(
            run["resources"].get("pair_cache_misses", 0) for run in runs
        ),
    }


def rank_candidate_aggregates(candidates: list[dict[str, Any]]) -> list[str]:
    """Rank zero-merge candidates by the committed exact-score policy."""

    def key(candidate: dict[str, Any]) -> tuple[Any, ...]:
        aggregate = candidate["aggregate"]
        return (
            int(aggregate["merge_damaged_reference_groups"] != 0),
            -aggregate["micro_exact_group_score"],
            -aggregate["worst_fold_exact_group_score"],
            -aggregate["micro_non_singleton_exact_group_score"],
            aggregate["split_reference_groups"],
            aggregate["total_wall_seconds"],
            candidate["candidate_id"],
        )

    return [candidate["candidate_id"] for candidate in sorted(candidates, key=key)]


def run_sweep(
    *,
    repo_root: Path,
    definition_path: Path,
    dataset_root: Path,
    manifest_path: Path,
    audit_path: Path,
    artifact_root: Path,
    registry_path: Path,
) -> dict[str, Any]:
    """Run every candidate on every fold and return a deterministic report."""

    definition = load_sweep_definition(definition_path)
    fold_values: list[dict[str, str]] = []
    for fold_path_value in definition.folds:
        fold_path = (repo_root / fold_path_value).resolve()
        with fold_path.open(encoding="utf-8") as input_file:
            raw_fold = json.load(input_file)
        fold_values.append(
            {
                "path": fold_path_value,
                "split_id": raw_fold["split_id"],
                "split_hash": hashlib.sha256(canonical_json_bytes(raw_fold)).hexdigest(),
            }
        )

    candidate_reports: list[dict[str, Any]] = []
    dataset_fingerprint: str | None = None
    for candidate in definition.candidates:
        config_path = (repo_root / candidate.config_path).resolve()
        config = load_config(config_path)
        runs: list[dict[str, Any]] = []
        for fold, fold_value in zip(definition.folds, fold_values, strict=True):
            outcome = run_evaluation(
                repo_root=repo_root,
                config_path=config_path,
                dataset_root=dataset_root,
                manifest_path=manifest_path,
                audit_path=audit_path,
                split_path=(repo_root / fold).resolve(),
                artifact_root=artifact_root,
                registry_path=registry_path,
            )
            with (outcome.artifact_dir / "run.json").open(encoding="utf-8") as input_file:
                run_record = json.load(input_file)
            if dataset_fingerprint is None:
                dataset_fingerprint = run_record["dataset_fingerprint"]
            elif dataset_fingerprint != run_record["dataset_fingerprint"]:
                raise ValueError("sweep runs produced different dataset fingerprints")
            runs.append(
                {
                    "fold_path": fold,
                    "metrics": outcome.metrics.as_dict(),
                    "resources": outcome.resources,
                    "run_id": outcome.run_id,
                    "split_id": fold_value["split_id"],
                }
            )
        candidate_reports.append(
            {
                "aggregate": aggregate_candidate_runs(runs),
                "candidate_id": candidate.candidate_id,
                "config_hash": config.fingerprint,
                "config_path": candidate.config_path,
                "runs": runs,
            }
        )

    ranking = rank_candidate_aggregates(candidate_reports)
    return {
        "candidates": candidate_reports,
        "dataset_fingerprint": dataset_fingerprint,
        "definition_fingerprint": definition.fingerprint,
        "folds": fold_values,
        "limitations": list(definition.limitations),
        "ranking": ranking,
        "schema_version": 1,
        "selected_candidate_id": ranking[0],
        "selection": _SELECTION,
        "stage": definition.stage,
        "sweep_id": definition.sweep_id,
    }
