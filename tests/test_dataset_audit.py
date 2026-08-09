from __future__ import annotations

import shutil
from pathlib import Path

import cv2
import numpy as np

from autohdr_eval.dataset import audit_dataset, compare_dataset_audits


def test_dataset_audit_reports_integrity_and_label_leakage(tmp_path: Path) -> None:
    dataset_root = tmp_path / "dataset"
    image_dir = dataset_root / "images"
    image_dir.mkdir(parents=True)
    image = np.full((20, 30, 3), 127, dtype=np.uint8)
    first = image_dir / "g1_a.jpg"
    second = image_dir / "g1_b.jpg"
    third = image_dir / "g2_c.png"
    assert cv2.imwrite(str(first), image)
    shutil.copyfile(first, second)
    assert cv2.imwrite(str(third), np.flip(image, axis=1))
    manifest = dataset_root / "public_manifest.csv"
    manifest.write_text(
        "group_id,filename\n1,g1_a.jpg\n1,g1_b.jpg\n2,g2_c.png\n",
        encoding="utf-8",
    )

    result = audit_dataset(dataset_root, manifest)

    assert result["audit_schema_version"] == 1
    assert result["manifest_image_count"] == 3
    assert result["group_count"] == 2
    assert result["directory_image_counts"] == {"images": 3}
    assert result["group_size_distribution"] == {"1": 1, "2": 1}
    assert result["filename_group_prefix_fraction"] == 1.0
    assert result["missing_images"] == []
    assert result["corrupt_images"] == []
    assert result["exact_duplicate_sets"] == [["g1_a.jpg", "g1_b.jpg"]]
    assert result["group_id_by_filename"] == {
        "g1_a.jpg": "1",
        "g1_b.jpg": "1",
        "g2_c.png": "2",
    }
    assert set(result["image_perceptual_hash"]) == {
        "g1_a.jpg",
        "g1_b.jpg",
        "g2_c.png",
    }
    assert set(result["image_sha256"]) == {"g1_a.jpg", "g1_b.jpg", "g2_c.png"}
    assert result["perceptual_cross_group_collision_sets"] == [
        ["g1_a.jpg", "g1_b.jpg", "g2_c.png"]
    ]
    assert len(result["dataset_fingerprint"]) == 64


def test_compare_audits_finds_renamed_content_and_group_relation_changes() -> None:
    left = {
        "dataset_fingerprint": "left",
        "group_id_by_filename": {"a.jpg": "g1", "b.jpg": "g1"},
        "image_perceptual_hash": {"a.jpg": "p1", "b.jpg": "p2"},
        "image_sha256": {"a.jpg": "h1", "b.jpg": "h2"},
    }
    right = {
        "dataset_fingerprint": "right",
        "group_id_by_filename": {"a.jpg": "x", "b.jpg": "y", "c.jpg": "y"},
        "image_perceptual_hash": {"a.jpg": "p1", "b.jpg": "p3", "c.jpg": "p2"},
        "image_sha256": {"a.jpg": "h1", "b.jpg": "h3", "c.jpg": "h2"},
    }

    result = compare_dataset_audits(left, right)

    assert result["shared_filename_count"] == 2
    assert result["identical_shared_filename_count"] == 1
    assert result["changed_shared_filenames"] == ["b.jpg"]
    assert result["exact_content_hash_count"] == 2
    assert result["left_images_with_exact_content_match"] == 2
    assert result["right_images_with_exact_content_match"] == 2
    assert result["perceptual_hash_count"] == 2
    assert result["shared_filename_relationship_pairs_checked"] == 1
    assert result["shared_filename_relationship_disagreement_count"] == 1
