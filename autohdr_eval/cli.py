"""Command-line entrypoints for auditing, running, and scoring AutoHDR experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from autohdr_eval.config import canonical_json_bytes, load_config
from autohdr_eval.dataset import audit_dataset, compare_dataset_audits
from autohdr_eval.gallery import render_error_gallery
from autohdr_eval.registry import RunRegistry
from autohdr_eval.runner import (
    deterministic_runtime_environment,
    run_evaluation,
    validate_frozen_evaluation,
)
from autohdr_eval.scoring import score_csv


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _add_run_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--audit", type=Path)
    parser.add_argument("--split", type=Path)
    parser.add_argument("--artifact-root", type=Path, default=Path("artifacts/runs"))
    parser.add_argument(
        "--registry", type=Path, default=Path("artifacts/run-registry.sqlite3")
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="audit one labeled dataset package")
    audit.add_argument("--dataset-root", type=Path, required=True)
    audit.add_argument("--manifest", type=Path, required=True)
    audit.add_argument("--archive", type=Path)
    audit.add_argument("--output", type=Path, required=True)

    compare_audits = subparsers.add_parser(
        "compare-audits", help="measure exact and perceptual overlap between packages"
    )
    compare_audits.add_argument("--left", type=Path, required=True)
    compare_audits.add_argument("--right", type=Path, required=True)
    compare_audits.add_argument("--output", type=Path, required=True)

    score = subparsers.add_parser("score", help="score one prediction CSV exactly")
    score.add_argument("--reference", type=Path, required=True)
    score.add_argument("--predictions", type=Path, required=True)

    run = subparsers.add_parser("run", help="run a non-protected evaluation")
    _add_run_arguments(run)

    final_evaluate = subparsers.add_parser(
        "final-evaluate", help="run a frozen protected holdout exactly once"
    )
    _add_run_arguments(final_evaluate)
    final_evaluate.add_argument("--frozen-commit", required=True)
    final_evaluate.add_argument("--config-hash", required=True)
    final_evaluate.add_argument("--split-hash", required=True)

    summarize = subparsers.add_parser("summarize", help="list recent registered runs")
    summarize.add_argument(
        "--registry", type=Path, default=Path("artifacts/run-registry.sqlite3")
    )
    summarize.add_argument("--limit", type=int, default=20)

    gallery = subparsers.add_parser(
        "gallery", help="render deterministic contact sheets for scored group failures"
    )
    gallery.add_argument("--dataset-root", type=Path, required=True)
    gallery.add_argument("--diagnostics", type=Path, required=True)
    gallery.add_argument("--output-dir", type=Path, required=True)

    fingerprint = subparsers.add_parser(
        "fingerprint", help="print canonical config or split fingerprints"
    )
    fingerprint.add_argument("--config", type=Path)
    fingerprint.add_argument("--split", type=Path)
    return parser


def _run_from_args(args: argparse.Namespace, *, allow_protected: bool) -> dict[str, Any]:
    outcome = run_evaluation(
        repo_root=args.repo_root.resolve(),
        config_path=args.config.resolve(),
        dataset_root=args.dataset_root.resolve(),
        manifest_path=args.manifest.resolve(),
        audit_path=args.audit.resolve() if args.audit else None,
        split_path=args.split.resolve() if args.split else None,
        artifact_root=args.artifact_root.resolve(),
        registry_path=args.registry.resolve(),
        allow_protected=allow_protected,
    )
    return {
        "artifact_dir": str(outcome.artifact_dir),
        "metrics": outcome.metrics.as_dict(),
        "predictions": str(outcome.predictions_path),
        "resources": outcome.resources,
        "run_id": outcome.run_id,
    }


def main(argv: list[str] | None = None) -> int:
    deterministic_runtime_environment()
    args = build_parser().parse_args(argv)

    if args.command == "audit":
        result = audit_dataset(
            args.dataset_root.resolve(),
            args.manifest.resolve(),
            args.archive.resolve() if args.archive else None,
        )
        _write_json(args.output, result)
        _print_json(result)
        return 0
    if args.command == "score":
        _print_json(score_csv(args.reference, args.predictions).as_dict())
        return 0
    if args.command == "compare-audits":
        with args.left.open(encoding="utf-8") as input_file:
            left = json.load(input_file)
        with args.right.open(encoding="utf-8") as input_file:
            right = json.load(input_file)
        result = compare_dataset_audits(left, right)
        _write_json(args.output, result)
        _print_json(result)
        return 0
    if args.command == "run":
        _print_json(_run_from_args(args, allow_protected=False))
        return 0
    if args.command == "final-evaluate":
        if args.split is None:
            raise ValueError("final-evaluate requires --split")
        validate_frozen_evaluation(
            repo_root=args.repo_root.resolve(),
            config_path=args.config.resolve(),
            split_path=args.split.resolve(),
            frozen_commit=args.frozen_commit,
            expected_config_hash=args.config_hash,
            expected_split_fingerprint=args.split_hash,
        )
        _print_json(_run_from_args(args, allow_protected=True))
        return 0
    if args.command == "summarize":
        _print_json(RunRegistry(args.registry).recent(args.limit))
        return 0
    if args.command == "gallery":
        _print_json(
            render_error_gallery(
                dataset_root=args.dataset_root.resolve(),
                diagnostics_path=args.diagnostics.resolve(),
                output_dir=args.output_dir.resolve(),
            )
        )
        return 0
    if args.command == "fingerprint":
        if bool(args.config) == bool(args.split):
            raise ValueError("provide exactly one of --config or --split")
        if args.config:
            _print_json({"config_hash": load_config(args.config).fingerprint})
        else:
            with args.split.open(encoding="utf-8") as split_file:
                split = json.load(split_file)
            _print_json(
                {"split_hash": hashlib.sha256(canonical_json_bytes(split)).hexdigest()}
            )
        return 0
    raise AssertionError(f"unhandled command: {args.command}")
