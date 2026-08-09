"""Dataset fingerprinting and sample-package audit helpers."""

from __future__ import annotations

import csv
import hashlib
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import cv2
import numpy as np

SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png"}


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        while chunk := input_file.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def dataset_fingerprint(manifest_path: Path, image_hashes: Mapping[str, str]) -> str:
    """Fingerprint a labeled package from its manifest and named image bytes."""

    digest = hashlib.sha256()
    digest.update(f"manifest:{sha256_file(manifest_path)}\n".encode())
    for filename, file_hash in sorted(
        image_hashes.items(), key=lambda item: (item[1], item[0])
    ):
        digest.update(f"image:{filename}:{file_hash}\n".encode())
    return digest.hexdigest()


def _distribution(values: Counter[int]) -> dict[str, int]:
    return {str(key): value for key, value in sorted(values.items())}


def _summary(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    array = np.asarray(values, dtype=np.float64)
    return {
        "max": float(np.max(array)),
        "median": float(np.median(array)),
        "min": float(np.min(array)),
    }


def read_manifest(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    """Read the public manifest while retaining all advertised columns."""

    with path.open(newline="", encoding="utf-8-sig") as input_file:
        reader = csv.DictReader(input_file)
        columns = reader.fieldnames or []
        required = {"filename", "group_id"}
        if not required.issubset(columns):
            raise ValueError(f"manifest must contain headers {sorted(required)}")
        if len(columns) != len(set(columns)):
            raise ValueError("manifest headers must be unique")
        rows = list(reader)

    filenames: list[str] = []
    for line_number, row in enumerate(rows, start=2):
        if None in row:
            raise ValueError(f"unexpected extra manifest value on line {line_number}")
        filename = row.get("filename", "")
        group_id = row.get("group_id", "")
        if not filename or Path(filename).name != filename or "/" in filename or "\\" in filename:
            raise ValueError(f"invalid manifest filename on line {line_number}: {filename}")
        if not group_id:
            raise ValueError(f"empty manifest group_id on line {line_number}")
        filenames.append(filename)
    duplicates = sorted(name for name, count in Counter(filenames).items() if count > 1)
    if duplicates:
        raise ValueError(f"duplicate manifest filenames: {duplicates}")
    return rows, columns


def _perceptual_hash(grayscale: np.ndarray) -> str:
    resized = cv2.resize(grayscale, (9, 8), interpolation=cv2.INTER_AREA)
    bits = resized[:, 1:] > resized[:, :-1]
    return np.packbits(bits.reshape(-1)).tobytes().hex()


def audit_dataset(
    dataset_root: Path,
    manifest_path: Path,
    archive_path: Path | None = None,
) -> dict[str, Any]:
    """Audit one labeled package without treating names or metadata as model input."""

    rows, columns = read_manifest(manifest_path)
    manifest_filenames = {row["filename"] for row in rows}
    group_sizes = Counter(row["group_id"] for row in rows)

    discovered_paths = sorted(
        path
        for path in dataset_root.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )
    directory_counts = Counter(
        path.relative_to(dataset_root).parent.as_posix() for path in discovered_paths
    )
    by_basename: dict[str, list[Path]] = defaultdict(list)
    for path in discovered_paths:
        by_basename[path.name].append(path)

    duplicate_basenames = sorted(
        basename for basename, paths in by_basename.items() if len(paths) > 1
    )
    missing_images = sorted(manifest_filenames - set(by_basename))
    extra_images = sorted(set(by_basename) - manifest_filenames)

    format_counts: Counter[str] = Counter()
    dimension_counts: Counter[str] = Counter()
    exact_hashes: dict[str, list[str]] = defaultdict(list)
    image_hashes: dict[str, str] = {}
    perceptual_hashes: dict[str, list[str]] = defaultdict(list)
    corrupt_images: list[str] = []
    luminance_medians: list[float] = []
    dark_clipped_fractions: list[float] = []
    bright_clipped_fractions: list[float] = []
    sharpness_values: list[float] = []
    total_bytes = 0

    unique_manifest_paths = [
        by_basename[filename][0]
        for filename in sorted(manifest_filenames)
        if len(by_basename.get(filename, [])) == 1
    ]
    for index, image_path in enumerate(unique_manifest_paths, start=1):
        if index == 1 or index % 50 == 0 or index == len(unique_manifest_paths):
            print(f"Auditing image {index}/{len(unique_manifest_paths)}", flush=True)
        total_bytes += image_path.stat().st_size
        format_counts[image_path.suffix.lower()] += 1
        file_hash = sha256_file(image_path)
        image_hashes[image_path.name] = file_hash
        exact_hashes[file_hash].append(image_path.name)

        grayscale = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if grayscale is None:
            corrupt_images.append(image_path.name)
            continue
        height, width = grayscale.shape
        dimension_counts[f"{width}x{height}"] += 1
        perceptual_hashes[_perceptual_hash(grayscale)].append(image_path.name)

        if max(grayscale.shape) > 256:
            scale = 256 / max(grayscale.shape)
            grayscale = cv2.resize(
                grayscale,
                (max(1, round(width * scale)), max(1, round(height * scale))),
                interpolation=cv2.INTER_AREA,
            )
        luminance_medians.append(float(np.median(grayscale)))
        dark_clipped_fractions.append(float(np.mean(grayscale <= 2)))
        bright_clipped_fractions.append(float(np.mean(grayscale >= 253)))
        sharpness_values.append(float(cv2.Laplacian(grayscale, cv2.CV_64F).var()))

    manifest_hash = sha256_file(manifest_path)

    archive: dict[str, Any] | None = None
    if archive_path is not None:
        archive = {
            "path": archive_path.name,
            "sha256": sha256_file(archive_path),
            "size_bytes": archive_path.stat().st_size,
        }

    prefix_matches = sum(
        row["filename"].startswith(f"g{row['group_id']}_") for row in rows
    )
    exact_duplicate_sets = [
        sorted(filenames) for filenames in exact_hashes.values() if len(filenames) > 1
    ]
    perceptual_collisions = [
        sorted(filenames)
        for filenames in perceptual_hashes.values()
        if len(filenames) > 1
    ]
    group_by_filename = {row["filename"]: row["group_id"] for row in rows}
    cross_group_perceptual_collisions = [
        filenames
        for filenames in perceptual_collisions
        if len({group_by_filename[filename] for filename in filenames}) > 1
    ]

    return {
        "archive": archive,
        "audit_schema_version": 1,
        "corrupt_images": sorted(corrupt_images),
        "dataset_fingerprint": dataset_fingerprint(manifest_path, image_hashes),
        "dataset_root": str(dataset_root),
        "directory_image_counts": dict(sorted(directory_counts.items())),
        "discovered_image_count": len(discovered_paths),
        "duplicate_basenames": duplicate_basenames,
        "exact_duplicate_sets": sorted(exact_duplicate_sets),
        "exposure": {
            "bright_clipped_fraction": _summary(bright_clipped_fractions),
            "dark_clipped_fraction": _summary(dark_clipped_fractions),
            "luminance_median": _summary(luminance_medians),
            "sharpness_laplacian_variance": _summary(sharpness_values),
        },
        "extra_images": extra_images,
        "filename_group_prefix_matches": prefix_matches,
        "filename_group_prefix_fraction": prefix_matches / len(rows) if rows else 0.0,
        "format_counts": dict(sorted(format_counts.items())),
        "group_count": len(group_sizes),
        "group_size_distribution": _distribution(Counter(group_sizes.values())),
        "image_sha256": dict(sorted(image_hashes.items())),
        "manifest_columns": columns,
        "manifest_image_count": len(rows),
        "manifest_sha256": manifest_hash,
        "missing_images": missing_images,
        "non_label_metadata_columns": sorted(set(columns) - {"filename", "group_id"}),
        "perceptual_hash_collision_sets": sorted(perceptual_collisions),
        "perceptual_cross_group_collision_sets": sorted(
            cross_group_perceptual_collisions
        ),
        "total_image_bytes": total_bytes,
        "unique_dimension_count": len(dimension_counts),
        "dimension_counts": dict(sorted(dimension_counts.items())),
    }
