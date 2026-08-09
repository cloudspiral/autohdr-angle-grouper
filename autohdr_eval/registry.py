"""SQLite-backed source of truth for local evaluation runs."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class RunRegistry:
    """Persist run lifecycle and evidence without storing dataset bytes."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    git_commit TEXT NOT NULL,
                    dirty_tree INTEGER NOT NULL,
                    config_path TEXT NOT NULL,
                    config_hash TEXT NOT NULL,
                    dataset_fingerprint TEXT NOT NULL,
                    split_id TEXT NOT NULL,
                    split_fingerprint TEXT,
                    cache_schema_versions TEXT NOT NULL,
                    seed INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    parent_run_id TEXT,
                    hypothesis_id TEXT,
                    metrics TEXT NOT NULL,
                    resources TEXT NOT NULL,
                    artifact_paths TEXT NOT NULL,
                    notes TEXT NOT NULL
                )
                """
            )

    def start(self, record: Mapping[str, Any]) -> None:
        required = {
            "run_id",
            "started_at",
            "git_commit",
            "dirty_tree",
            "config_path",
            "config_hash",
            "dataset_fingerprint",
            "split_id",
            "seed",
        }
        missing = required - set(record)
        if missing:
            raise ValueError(f"run record missing fields: {sorted(missing)}")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO runs (
                    run_id, started_at, git_commit, dirty_tree, config_path,
                    config_hash, dataset_fingerprint, split_id,
                    split_fingerprint, cache_schema_versions, seed, status,
                    parent_run_id, hypothesis_id, metrics, resources,
                    artifact_paths, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["run_id"],
                    record["started_at"],
                    record["git_commit"],
                    int(bool(record["dirty_tree"])),
                    record["config_path"],
                    record["config_hash"],
                    record["dataset_fingerprint"],
                    record["split_id"],
                    record.get("split_fingerprint"),
                    json.dumps(record.get("cache_schema_versions", {}), sort_keys=True),
                    record["seed"],
                    "running",
                    record.get("parent_run_id"),
                    record.get("hypothesis_id"),
                    "{}",
                    "{}",
                    "{}",
                    record.get("notes", ""),
                ),
            )

    def finish(
        self,
        run_id: str,
        *,
        finished_at: str,
        status: str,
        metrics: Mapping[str, Any] | None = None,
        resources: Mapping[str, Any] | None = None,
        artifact_paths: Mapping[str, Any] | None = None,
        notes: str = "",
    ) -> None:
        if status not in {"passed", "failed", "reverted"}:
            raise ValueError(f"invalid terminal run status: {status}")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE runs
                SET finished_at = ?, status = ?, metrics = ?, resources = ?,
                    artifact_paths = ?, notes = ?
                WHERE run_id = ?
                """,
                (
                    finished_at,
                    status,
                    json.dumps(metrics or {}, sort_keys=True),
                    json.dumps(resources or {}, sort_keys=True),
                    json.dumps(artifact_paths or {}, sort_keys=True),
                    notes,
                    run_id,
                ),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"unknown run_id: {run_id}")

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM runs ORDER BY started_at DESC, run_id DESC LIMIT ?",
                (limit,),
            ).fetchall()

        decoded: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["dirty_tree"] = bool(item["dirty_tree"])
            for key in (
                "cache_schema_versions",
                "metrics",
                "resources",
                "artifact_paths",
            ):
                item[key] = json.loads(item[key])
            decoded.append(item)
        return decoded

    def contains_split(self, split_id: str) -> bool:
        """Return whether any run has already started for a split."""

        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM runs WHERE split_id = ? LIMIT 1", (split_id,)
            ).fetchone()
        return row is not None
