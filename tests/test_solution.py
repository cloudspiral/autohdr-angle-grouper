from __future__ import annotations

import csv
from pathlib import Path

import cv2
import numpy as np
import pytest

from solution import discover_images, group_images, run, validate_groups


def make_image_files(directory: Path, names: list[str]) -> list[str]:
    directory.mkdir(parents=True)
    for name in names:
        (directory / name).write_bytes(b"fixture")
    return [str(directory / name) for name in names]


def make_scene(kind: str, height: int = 120, width: int = 160) -> np.ndarray:
    """Create a textured synthetic scene with geometry that survives exposure edits."""

    y_gradient = np.linspace(35, 125, height, dtype=np.float32)[:, None]
    image = np.repeat(y_gradient, width, axis=1)
    image = np.stack((image, image * 0.9, image * 0.75), axis=-1)

    if kind == "house":
        cv2.rectangle(image, (22, 48), (105, 105), (155, 175, 195), -1)
        cv2.line(image, (15, 50), (63, 16), (225, 225, 225), 6)
        cv2.line(image, (63, 16), (113, 50), (225, 225, 225), 6)
        cv2.rectangle(image, (38, 62), (58, 82), (35, 55, 75), -1)
        cv2.rectangle(image, (72, 58), (92, 105), (70, 90, 115), -1)
        cv2.circle(image, (132, 36), 13, (205, 190, 70), -1)
    elif kind == "hallway":
        cv2.line(image, (0, 0), (80, 60), (220, 220, 220), 7)
        cv2.line(image, (159, 0), (80, 60), (220, 220, 220), 7)
        cv2.line(image, (0, 119), (80, 60), (25, 45, 65), 8)
        cv2.line(image, (159, 119), (80, 60), (25, 45, 65), 8)
        cv2.rectangle(image, (68, 38), (92, 72), (175, 115, 70), -1)
        cv2.circle(image, (80, 60), 8, (245, 235, 185), -1)
    else:
        raise ValueError(f"unknown synthetic scene: {kind}")

    return np.clip(image, 0, 255).astype(np.uint8)


def write_valid_image(path: Path, image: np.ndarray) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    assert cv2.imwrite(str(path), image)
    return str(path)


def exposed(image: np.ndarray, multiplier: float) -> np.ndarray:
    return np.clip(image.astype(np.float32) * multiplier, 0, 255).astype(np.uint8)


def shifted(image: np.ndarray, x_pixels: int, y_pixels: int) -> np.ndarray:
    transform = np.float32([[1, 0, x_pixels], [0, 1, y_pixels]])
    return cv2.warpAffine(
        image,
        transform,
        (image.shape[1], image.shape[0]),
        borderMode=cv2.BORDER_REFLECT_101,
    )


def group_sets(groups: list[list[str]]) -> set[frozenset[str]]:
    return {frozenset(group) for group in groups}


def test_discover_images_filters_and_sorts_supported_files(tmp_path: Path) -> None:
    image_dir = tmp_path / "images"
    make_image_files(image_dir, ["b.JPEG", "a.jpg", "c.png", "notes.txt"])

    assert [Path(path).name for path in discover_images(image_dir)] == [
        "a.jpg",
        "b.JPEG",
        "c.png",
    ]


def test_group_images_groups_dark_middle_and_bright_exposures(tmp_path: Path) -> None:
    scene = make_scene("house")
    image_paths = [
        write_valid_image(tmp_path / "images" / "random-c.jpg", exposed(scene, 1.65)),
        write_valid_image(tmp_path / "images" / "random-a.jpg", exposed(scene, 0.45)),
        write_valid_image(tmp_path / "images" / "random-b.jpg", exposed(scene, 1.0)),
    ]

    groups = group_images(image_paths)

    assert group_sets(groups) == {
        frozenset({"random-a.jpg", "random-b.jpg", "random-c.jpg"})
    }
    validate_groups(groups, image_paths)


def test_group_images_tolerates_modest_pixel_shift(tmp_path: Path) -> None:
    scene = make_scene("house")
    image_paths = [
        write_valid_image(tmp_path / "images" / "base.png", scene),
        write_valid_image(tmp_path / "images" / "shifted.png", shifted(scene, 4, -3)),
    ]

    assert group_sets(group_images(image_paths)) == {
        frozenset({"base.png", "shifted.png"})
    }


def test_group_images_separates_structurally_different_scenes(tmp_path: Path) -> None:
    house = make_scene("house")
    hallway = make_scene("hallway")
    image_paths = [
        write_valid_image(tmp_path / "images" / "image-4.jpg", exposed(hallway, 1.4)),
        write_valid_image(tmp_path / "images" / "image-2.jpg", exposed(house, 1.4)),
        write_valid_image(tmp_path / "images" / "image-3.jpg", exposed(hallway, 0.6)),
        write_valid_image(tmp_path / "images" / "image-1.jpg", exposed(house, 0.6)),
    ]

    assert group_sets(group_images(image_paths)) == {
        frozenset({"image-1.jpg", "image-2.jpg"}),
        frozenset({"image-3.jpg", "image-4.jpg"}),
    }


def test_group_images_is_deterministic_and_emits_every_input_once(tmp_path: Path) -> None:
    house = make_scene("house")
    hallway = make_scene("hallway")
    image_paths = [
        write_valid_image(tmp_path / "images" / "z.png", exposed(house, 0.7)),
        write_valid_image(tmp_path / "images" / "q.png", exposed(hallway, 1.25)),
        write_valid_image(tmp_path / "images" / "m.png", exposed(house, 1.25)),
    ]

    first = group_images(image_paths)
    second = group_images(list(reversed(image_paths)))

    assert first == second
    validate_groups(first, image_paths)
    assert sorted(filename for group in first for filename in group) == ["m.png", "q.png", "z.png"]


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
    write_valid_image(image_dir / "second.jpeg", make_scene("hallway"))
    write_valid_image(image_dir / "first.jpg", make_scene("house"))

    output_path = run(image_dir, output_dir)

    with output_path.open(newline="", encoding="utf-8") as output_file:
        assert list(csv.DictReader(output_file)) == [
            {"filename": "first.jpg", "group_id": "0"},
            {"filename": "second.jpeg", "group_id": "1"},
        ]


def test_group_images_falls_back_to_singleton_for_corrupt_image(tmp_path: Path) -> None:
    image_dir = tmp_path / "images"
    valid = write_valid_image(image_dir / "valid.jpg", make_scene("house"))
    corrupt_path = image_dir / "corrupt.jpg"
    corrupt_path.write_bytes(b"not an image")

    groups = group_images([valid, str(corrupt_path)])

    assert group_sets(groups) == {
        frozenset({"valid.jpg"}),
        frozenset({"corrupt.jpg"}),
    }
    validate_groups(groups, [valid, str(corrupt_path)])


def test_run_with_empty_input_writes_header_only_csv(tmp_path: Path) -> None:
    image_dir = tmp_path / "images"
    image_dir.mkdir()

    first = run(image_dir, tmp_path / "first")
    second = run(image_dir, tmp_path / "second")

    assert first.read_bytes() == b"filename,group_id\n"
    assert first.read_bytes() == second.read_bytes()
