from __future__ import annotations

import shutil
from pathlib import Path

import cv2
import numpy as np

from autohdr_eval.dataset import audit_dataset


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
    assert set(result["image_sha256"]) == {"g1_a.jpg", "g1_b.jpg", "g2_c.png"}
    assert result["perceptual_cross_group_collision_sets"] == [
        ["g1_a.jpg", "g1_b.jpg", "g2_c.png"]
    ]
    assert len(result["dataset_fingerprint"]) == 64
