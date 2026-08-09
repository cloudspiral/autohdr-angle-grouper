"""Strict, hashable configuration loading for reproducible grouping runs."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SUPPORTED_ALGORITHMS = {"singleton", "structural"}


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON with stable ordering for fingerprints and artifacts."""

    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


@dataclass(frozen=True)
class EvaluationConfig:
    schema_version: int
    name: str
    algorithm: str
    seed: int
    parameters: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "name": self.name,
            "parameters": self.parameters,
            "schema_version": self.schema_version,
            "seed": self.seed,
        }

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(canonical_json_bytes(self.as_dict())).hexdigest()


def load_config(path: Path) -> EvaluationConfig:
    """Load and validate a committed evaluation configuration."""

    with path.open(encoding="utf-8") as config_file:
        raw = json.load(config_file)
    if not isinstance(raw, dict):
        raise ValueError("config must be a JSON object")

    expected_keys = {"schema_version", "name", "algorithm", "seed", "parameters"}
    if set(raw) != expected_keys:
        raise ValueError(
            f"config keys must be exactly {sorted(expected_keys)}; got {sorted(raw)}"
        )
    if type(raw["schema_version"]) is not int or raw["schema_version"] != 1:
        raise ValueError(f"unsupported config schema: {raw['schema_version']}")
    if not isinstance(raw["name"], str) or not re.fullmatch(
        r"[A-Za-z0-9._-]+", raw["name"]
    ):
        raise ValueError("config name must use only letters, numbers, dot, underscore, or dash")
    if raw["algorithm"] not in SUPPORTED_ALGORITHMS:
        raise ValueError(f"unsupported algorithm: {raw['algorithm']}")
    if type(raw["seed"]) is not int:
        raise ValueError("config seed must be an integer")
    if not isinstance(raw["parameters"], dict):
        raise ValueError("config parameters must be an object")

    return EvaluationConfig(
        schema_version=raw["schema_version"],
        name=raw["name"],
        algorithm=raw["algorithm"],
        seed=raw["seed"],
        parameters=raw["parameters"],
    )
