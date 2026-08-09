"""Benchmark the exact cache-free submission entrypoint on one frozen split."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import resource
import subprocess
import time
from pathlib import Path
from typing import Any

from autohdr_eval.config import canonical_json_bytes, load_config
from autohdr_eval.contracts import validate_groups
from solution import SUBMISSION_CONFIG_PATH, group_images_with_resources


def _git_state(repo_root: Path) -> tuple[str, bool]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    return commit, dirty


def _peak_rss_bytes() -> int:
    maximum = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(maximum if platform.system() == "Darwin" else maximum * 1024)


def _split_paths(dataset_root: Path, manifest_path: Path, split_path: Path) -> list[str]:
    with manifest_path.open(newline="", encoding="utf-8-sig") as manifest_file:
        rows = list(csv.DictReader(manifest_file))
    if not rows or set(rows[0]) != {"filename", "group_id"}:
        raise ValueError("manifest must contain filename and group_id columns")
    split = json.loads(split_path.read_text(encoding="utf-8"))
    selection = split.get("selection", {})
    if selection.get("type") == "all":
        names = sorted(row["filename"] for row in rows)
    elif selection.get("type") == "group_ids" and isinstance(
        selection.get("values"), list
    ):
        selected_groups = set(selection["values"])
        names = sorted(
            row["filename"] for row in rows if row["group_id"] in selected_groups
        )
    else:
        raise ValueError("benchmark splits must select all rows or explicit group_ids")
    image_root = dataset_root / "images"
    paths = [image_root / name for name in names]
    missing = [path.name for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"benchmark split is missing images: {missing[:10]}")
    return [str(path) for path in paths]


def benchmark(
    *,
    repo_root: Path,
    dataset_root: Path,
    manifest_path: Path,
    split_path: Path,
) -> dict[str, Any]:
    image_paths = _split_paths(dataset_root, manifest_path, split_path)
    git_commit, dirty_tree = _git_state(repo_root)
    config = load_config(SUBMISSION_CONFIG_PATH)
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    outcome = group_images_with_resources(image_paths)
    cpu_seconds = time.process_time() - started_cpu
    wall_seconds = time.perf_counter() - started_wall
    validate_groups(outcome.groups, image_paths)
    prediction_hash = hashlib.sha256(canonical_json_bytes(outcome.groups)).hexdigest()
    split = json.loads(split_path.read_text(encoding="utf-8"))
    return {
        "config_hash": config.fingerprint,
        "config_path": str(SUBMISSION_CONFIG_PATH.relative_to(repo_root)),
        "dirty_tree": dirty_tree,
        "git_commit": git_commit,
        "image_count": len(image_paths),
        "machine": {
            "machine": platform.machine(),
            "platform": platform.platform(),
            "processor": platform.processor(),
            "python": platform.python_version(),
        },
        "peak_rss_bytes": _peak_rss_bytes(),
        "prediction_sha256": prediction_hash,
        "predicted_group_count": len(outcome.groups),
        "resources": outcome.resources,
        "schema_version": 1,
        "split_id": split["split_id"],
        "split_path": str(split_path),
        "timing": {
            "cpu_seconds": cpu_seconds,
            "wall_seconds": wall_seconds,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = benchmark(
        repo_root=args.repo_root.resolve(),
        dataset_root=args.dataset_root,
        manifest_path=args.manifest,
        split_path=args.split,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json_bytes(result))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
