from __future__ import annotations

import csv
from pathlib import Path

import pytest

from solution import discover_images, group_images, run, validate_groups


def make_image_files(directory: Path, names: list[str]) -> list[str]:
    directory.mkdir(parents=True)
    for name in names:
        (directory / name).write_bytes(b"fixture")
    return [str(directory / name) for name in names]


def test_discover_images_filters_and_sorts_supported_files(tmp_path: Path) -> None:
    image_dir = tmp_path / "images"
    make_image_files(image_dir, ["b.JPEG", "a.jpg", "c.png", "notes.txt"])

    assert [Path(path).name for path in discover_images(image_dir)] == [
        "a.jpg",
        "b.JPEG",
        "c.png",
    ]


def test_singleton_baseline_returns_every_filename_once(tmp_path: Path) -> None:
    image_paths = make_image_files(tmp_path / "images", ["bravo.jpg", "alpha.jpg"])

    groups = group_images(image_paths)

    assert groups == [["alpha.jpg"], ["bravo.jpg"]]
    validate_groups(groups, image_paths)


@pytest.mark.parametrize(
    ("groups", "message"),
    [
        ([[]], "must not be empty"),
        ([["one.jpg"], ["one.jpg"]], "duplicates"),
        ([["one.jpg"]], "missing"),
        ([["one.jpg", "three.jpg"]], "unexpected"),
        ([["nested/one.jpg", "two.jpg"]], "filenames only"),
    ],
)
def test_validate_groups_rejects_contract_violations(
    tmp_path: Path, groups: list[list[str]], message: str
) -> None:
    image_paths = make_image_files(tmp_path / "images", ["one.jpg", "two.jpg"])

    with pytest.raises(ValueError, match=message):
        validate_groups(groups, image_paths)


def test_run_writes_required_csv_contract(tmp_path: Path) -> None:
    image_dir = tmp_path / "images"
    output_dir = tmp_path / "output"
    make_image_files(image_dir, ["second.jpeg", "first.jpg"])

    output_path = run(image_dir, output_dir)

    with output_path.open(newline="", encoding="utf-8") as output_file:
        assert list(csv.DictReader(output_file)) == [
            {"filename": "first.jpg", "group_id": "0"},
            {"filename": "second.jpeg", "group_id": "1"},
        ]
