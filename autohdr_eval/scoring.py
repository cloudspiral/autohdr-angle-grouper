"""Exact-group scoring and merge/split diagnostics."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from autohdr_eval.contracts import canonicalize_groups, read_group_csv, validate_partition


def _size_distribution(groups: list[frozenset[str]]) -> dict[str, int]:
    return {
        str(size): count
        for size, count in sorted(Counter(len(group) for group in groups).items())
    }


@dataclass(frozen=True)
class ScoreResult:
    exact_matches: int
    total_reference_groups: int
    exact_group_score: float
    singleton_exact_matches: int
    singleton_reference_groups: int
    non_singleton_exact_matches: int
    non_singleton_reference_groups: int
    predicted_exact_group_precision: float
    merge_damaged_reference_groups: int
    split_reference_groups: int
    predicted_groups: int
    predicted_singletons: int
    reference_group_size_distribution: dict[str, int]
    predicted_group_size_distribution: dict[str, int]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def score_groups(
    reference_groups: list[list[str]], predicted_groups: list[list[str]]
) -> ScoreResult:
    """Score a complete prediction using the official exact-set denominator."""

    reference = canonicalize_groups(reference_groups)
    expected = [filename for group in reference for filename in group]
    validate_partition(reference, expected)
    validate_partition(predicted_groups, expected)

    reference_sets = [frozenset(group) for group in reference]
    predicted_sets = [frozenset(group) for group in canonicalize_groups(predicted_groups)]
    reference_unique = set(reference_sets)
    predicted_unique = set(predicted_sets)
    if len(reference_unique) != len(reference_sets):
        raise ValueError("reference contains duplicate groups")
    if len(predicted_unique) != len(predicted_sets):
        raise ValueError("predictions contain duplicate groups")

    exact_sets = reference_unique & predicted_unique
    total_reference = len(reference_sets)
    exact_matches = len(exact_sets)
    singleton_reference = [group for group in reference_sets if len(group) == 1]
    non_singleton_reference = [group for group in reference_sets if len(group) > 1]

    predicted_by_filename = {
        filename: group for group in predicted_sets for filename in group
    }
    merge_damaged = 0
    split_groups = 0
    for reference_group in reference_sets:
        touched_predictions = {predicted_by_filename[name] for name in reference_group}
        if len(touched_predictions) > 1:
            split_groups += 1
        if any(predicted_group - reference_group for predicted_group in touched_predictions):
            merge_damaged += 1

    return ScoreResult(
        exact_matches=exact_matches,
        total_reference_groups=total_reference,
        exact_group_score=exact_matches / total_reference if total_reference else 1.0,
        singleton_exact_matches=sum(group in exact_sets for group in singleton_reference),
        singleton_reference_groups=len(singleton_reference),
        non_singleton_exact_matches=sum(
            group in exact_sets for group in non_singleton_reference
        ),
        non_singleton_reference_groups=len(non_singleton_reference),
        predicted_exact_group_precision=(
            exact_matches / len(predicted_sets) if predicted_sets else 1.0
        ),
        merge_damaged_reference_groups=merge_damaged,
        split_reference_groups=split_groups,
        predicted_groups=len(predicted_sets),
        predicted_singletons=sum(len(group) == 1 for group in predicted_sets),
        reference_group_size_distribution=_size_distribution(reference_sets),
        predicted_group_size_distribution=_size_distribution(predicted_sets),
    )


def diagnose_groups(
    reference_groups: list[list[str]], predicted_groups: list[list[str]]
) -> dict[str, list[list[str]]]:
    """Return deterministic filename-level group failures for gallery generation."""

    reference = canonicalize_groups(reference_groups)
    expected = [filename for group in reference for filename in group]
    validate_partition(reference, expected)
    validate_partition(predicted_groups, expected)
    predicted_sets = [frozenset(group) for group in canonicalize_groups(predicted_groups)]
    predicted_by_filename = {
        filename: group for group in predicted_sets for filename in group
    }

    diagnostics: dict[str, list[list[str]]] = {
        "exact_reference_groups": [],
        "merge_damaged_reference_groups": [],
        "split_reference_groups": [],
    }
    for reference_group_list in reference:
        reference_group = frozenset(reference_group_list)
        touched = {predicted_by_filename[name] for name in reference_group}
        if reference_group in touched:
            diagnostics["exact_reference_groups"].append(reference_group_list)
        if len(touched) > 1:
            diagnostics["split_reference_groups"].append(reference_group_list)
        if any(predicted_group - reference_group for predicted_group in touched):
            diagnostics["merge_damaged_reference_groups"].append(reference_group_list)
    return diagnostics


def score_csv(reference_path: Path, prediction_path: Path) -> ScoreResult:
    """Load two challenge-format CSV files and return exact-group metrics."""

    return score_groups(read_group_csv(reference_path), read_group_csv(prediction_path))
