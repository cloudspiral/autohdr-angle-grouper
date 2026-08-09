"""CSV and in-memory partition validation for AutoHDR predictions."""

from __future__ import annotations

import csv
from collections import Counter
from collections.abc import Iterable, Sequence
from pathlib import Path


def _validate_filename(filename: str) -> None:
    if not isinstance(filename, str) or not filename:
        raise ValueError("predictions must contain non-empty filenames")
    if "/" in filename or "\\" in filename or Path(filename).name != filename:
        raise ValueError(f"predictions must contain filenames only: {filename}")


def canonicalize_groups(groups: Iterable[Iterable[str]]) -> list[list[str]]:
    """Return a stable representation independent of group and member order."""

    canonical = [sorted(group) for group in groups]
    return sorted(canonical, key=tuple)


def validate_partition(
    groups: Sequence[Sequence[str]], expected_filenames: Sequence[str]
) -> None:
    """Require a complete, filename-only partition of ``expected_filenames``."""

    expected = list(expected_filenames)
    for filename in expected:
        _validate_filename(filename)
    if len(expected) != len(set(expected)):
        raise ValueError("expected filenames must be unique")

    predicted: list[str] = []
    for group in groups:
        if not group:
            raise ValueError("predicted groups must not be empty")
        for filename in group:
            _validate_filename(filename)
            predicted.append(filename)

    duplicates = sorted(name for name, count in Counter(predicted).items() if count > 1)
    missing = sorted(set(expected) - set(predicted))
    unexpected = sorted(set(predicted) - set(expected))
    if duplicates or missing or unexpected:
        raise ValueError(
            "invalid grouping: "
            f"duplicates={duplicates}, missing={missing}, unexpected={unexpected}"
        )


def validate_groups(groups: Sequence[Sequence[str]], image_paths: Sequence[str]) -> None:
    """Validate groups against input paths while exposing the starter API helper."""

    expected = [Path(image_path).name for image_path in image_paths]
    validate_partition(groups, expected)


def read_group_csv(path: Path) -> list[list[str]]:
    """Read a ``filename,group_id`` CSV and reject ambiguous duplicate rows."""

    with path.open(newline="", encoding="utf-8-sig") as input_file:
        reader = csv.DictReader(input_file)
        fieldnames = reader.fieldnames or []
        if len(fieldnames) != 2 or set(fieldnames) != {"filename", "group_id"}:
            raise ValueError(
                "CSV headers must contain filename and group_id exactly once"
            )

        buckets: dict[str, list[str]] = {}
        seen: set[str] = set()
        for line_number, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"unexpected extra CSV value on line {line_number}")
            filename = row.get("filename", "")
            group_id = row.get("group_id", "")
            _validate_filename(filename)
            if not group_id:
                raise ValueError(f"empty group_id on CSV line {line_number}")
            if filename in seen:
                raise ValueError(f"duplicate filename in CSV: {filename}")
            seen.add(filename)
            buckets.setdefault(group_id, []).append(filename)

    return canonicalize_groups(buckets.values())


def write_predictions(
    groups: Sequence[Sequence[str]], image_paths: Sequence[str], output_path: Path
) -> None:
    """Validate and write deterministic challenge-format predictions."""

    validate_groups(groups, image_paths)
    canonical_groups = canonicalize_groups(groups)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.writer(output_file, lineterminator="\n")
        writer.writerow(["filename", "group_id"])
        for group_id, group in enumerate(canonical_groups):
            for filename in group:
                writer.writerow([filename, group_id])
