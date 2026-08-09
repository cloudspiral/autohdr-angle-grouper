from __future__ import annotations

import csv
from pathlib import Path

import pytest

from autohdr_eval.contracts import read_group_csv
from autohdr_eval.scoring import diagnose_groups, score_csv, score_groups

REFERENCE_GROUPS = [
    ["living_room_dark", "living_room_mid", "living_room_bright"],
    ["kitchen_wide_dark", "kitchen_wide_bright"],
    ["kitchen_close"],
    ["master_bed_dark", "master_bed_mid", "master_bed_bright"],
    ["master_bed_window_dark", "master_bed_window_bright"],
    ["bathroom_dark", "bathroom_bright"],
    ["backyard"],
    ["exterior_front_day", "exterior_front_dusk"],
]


def test_official_perfect_example_scores_one() -> None:
    result = score_groups(REFERENCE_GROUPS, list(reversed(REFERENCE_GROUPS)))

    assert result.exact_matches == 8
    assert result.total_reference_groups == 8
    assert result.exact_group_score == 1.0
    assert result.merge_damaged_reference_groups == 0
    assert result.split_reference_groups == 0


def test_official_singleton_example_scores_two_of_eight() -> None:
    predictions = [[filename] for group in REFERENCE_GROUPS for filename in group]

    result = score_groups(REFERENCE_GROUPS, predictions)

    assert result.exact_matches == 2
    assert result.exact_group_score == 0.25
    assert result.singleton_exact_matches == 2
    assert result.non_singleton_exact_matches == 0
    assert result.split_reference_groups == 6


def test_official_merge_example_scores_six_of_eight() -> None:
    predictions = [
        group
        for group in REFERENCE_GROUPS
        if group not in (REFERENCE_GROUPS[1], REFERENCE_GROUPS[2])
    ]
    predictions.append(REFERENCE_GROUPS[1] + REFERENCE_GROUPS[2])

    result = score_groups(REFERENCE_GROUPS, predictions)

    assert result.exact_matches == 6
    assert result.exact_group_score == 0.75
    assert result.merge_damaged_reference_groups == 2

    diagnostics = diagnose_groups(REFERENCE_GROUPS, predictions)
    assert diagnostics["merge_damaged_reference_groups"] == [
        ["kitchen_close"],
        ["kitchen_wide_bright", "kitchen_wide_dark"],
    ]
    assert len(diagnostics["failures"]) == 2
    assert all(failure["failure_types"] == ["merge"] for failure in diagnostics["failures"])


def test_official_split_example_damages_one_reference_group() -> None:
    predictions = REFERENCE_GROUPS[1:] + [
        ["living_room_dark", "living_room_mid"],
        ["living_room_bright"],
    ]

    result = score_groups(REFERENCE_GROUPS, predictions)

    assert result.exact_matches == 7
    assert result.exact_group_score == 0.875
    assert result.split_reference_groups == 1

    diagnostics = diagnose_groups(REFERENCE_GROUPS, predictions)
    assert diagnostics["split_reference_groups"] == [
        ["living_room_bright", "living_room_dark", "living_room_mid"]
    ]
    assert diagnostics["failures"] == [
        {
            "failure_types": ["split"],
            "predicted_groups": [
                ["living_room_bright"],
                ["living_room_dark", "living_room_mid"],
            ],
            "reference_group": [
                "living_room_bright",
                "living_room_dark",
                "living_room_mid",
            ],
        }
    ]


def write_groups(path: Path, groups: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(["group_id", "filename"])
        for group_id, group in enumerate(groups):
            for filename in reversed(group):
                writer.writerow([f"group-{group_id}", filename])


def test_csv_scoring_ignores_row_group_and_column_order(tmp_path: Path) -> None:
    reference = tmp_path / "reference.csv"
    predictions = tmp_path / "predictions.csv"
    write_groups(reference, REFERENCE_GROUPS)
    write_groups(predictions, list(reversed(REFERENCE_GROUPS)))

    assert score_csv(reference, predictions).exact_group_score == 1.0


def test_csv_reader_rejects_duplicate_filename(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.csv"
    path.write_text("filename,group_id\na.jpg,0\na.jpg,1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate filename"):
        read_group_csv(path)


def test_empty_reference_and_prediction_have_defined_perfect_score() -> None:
    result = score_groups([], [])

    assert result.total_reference_groups == 0
    assert result.exact_group_score == 1.0
