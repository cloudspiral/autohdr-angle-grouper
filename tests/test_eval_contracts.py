from __future__ import annotations

from pathlib import Path

import pytest

from autohdr_eval.contracts import (
    canonicalize_groups,
    read_group_csv,
    validate_partition,
    write_predictions,
)


def test_canonicalize_groups_is_order_independent() -> None:
    assert canonicalize_groups([["b.jpg", "a.jpg"], ["c.jpg"]]) == [
        ["a.jpg", "b.jpg"],
        ["c.jpg"],
    ]


@pytest.mark.parametrize("filename", ["dir/a.jpg", "dir\\a.jpg", ""])
def test_partition_rejects_path_or_empty_filename(filename: str) -> None:
    with pytest.raises(ValueError, match="filename"):
        validate_partition([[filename]], [filename])


def test_empty_partition_writes_header_only_csv(tmp_path: Path) -> None:
    output = tmp_path / "predictions.csv"

    write_predictions([], [], output)

    assert output.read_bytes() == b"filename,group_id\n"


def test_prediction_bytes_are_stable_across_input_group_order(tmp_path: Path) -> None:
    image_paths = ["/input/b.jpg", "/input/a.jpg", "/input/c.jpg"]
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"

    write_predictions([["c.jpg"], ["b.jpg", "a.jpg"]], image_paths, first)
    write_predictions([["a.jpg", "b.jpg"], ["c.jpg"]], image_paths, second)

    assert first.read_bytes() == second.read_bytes()


def test_csv_reader_rejects_extra_columns(tmp_path: Path) -> None:
    path = tmp_path / "extra.csv"
    path.write_text("filename,group_id,note\na.jpg,0,nope\n", encoding="utf-8")

    with pytest.raises(ValueError, match="exactly once"):
        read_group_csv(path)
