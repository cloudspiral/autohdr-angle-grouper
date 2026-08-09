from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import numpy as np

import solution
from autohdr_eval.candidates import CandidateScreenConfig, generate_structural_candidates
from solution import StructuralConfig


def screen_config(*, all_pairs_max_images: int = 2, top_k: int = 1) -> CandidateScreenConfig:
    return CandidateScreenConfig(
        all_pairs_max_images=all_pairs_max_images,
        top_k=top_k,
        structural=asdict(StructuralConfig()),
    )


def fixture_paths(tmp_path: Path, names: list[str]) -> list[str]:
    paths = []
    for name in names:
        path = tmp_path / name
        path.write_bytes(b"fixture")
        paths.append(str(path))
    return paths


def test_small_batch_candidate_path_is_complete_without_decoding(tmp_path: Path) -> None:
    paths = fixture_paths(tmp_path, ["c.jpg", "a.jpg", "b.jpg"])

    outcome = generate_structural_candidates(
        paths,
        screen_config(all_pairs_max_images=3),
    )

    assert outcome.candidate_pairs == (
        ("a.jpg", "b.jpg"),
        ("a.jpg", "c.jpg"),
        ("b.jpg", "c.jpg"),
    )
    assert outcome.resources["candidate_screen_mode"] == "all_pairs"
    assert outcome.resources["screen_descriptor_count"] == 0


def test_structural_top_k_uses_pixel_distance_and_unions_neighbors(
    tmp_path: Path, monkeypatch
) -> None:
    paths = fixture_paths(tmp_path, ["d.jpg", "b.jpg", "a.jpg", "c.jpg"])
    descriptors = {
        "a.jpg": np.asarray([1.0, 0.0], dtype=np.float32),
        "b.jpg": np.asarray([0.99, 0.1], dtype=np.float32),
        "c.jpg": np.asarray([-1.0, 0.0], dtype=np.float32),
        "d.jpg": np.asarray([-0.99, 0.1], dtype=np.float32),
    }
    monkeypatch.setattr(
        solution,
        "_build_descriptor",
        lambda path, _config: descriptors[Path(path).name],
    )

    outcome = generate_structural_candidates(paths, screen_config())

    assert outcome.candidate_pairs == (("a.jpg", "b.jpg"), ("c.jpg", "d.jpg"))
    assert outcome.resources["candidate_pair_count"] == 2
    assert outcome.resources["all_pair_count"] == 6


def test_structural_top_k_keeps_all_boundary_ties_without_filename_selection(
    tmp_path: Path, monkeypatch
) -> None:
    paths = fixture_paths(tmp_path, ["z.jpg", "q.jpg", "m.jpg", "a.jpg"])
    monkeypatch.setattr(
        solution,
        "_build_descriptor",
        lambda _path, _config: np.asarray([1.0, 0.0], dtype=np.float32),
    )

    outcome = generate_structural_candidates(paths, screen_config())

    assert len(outcome.candidate_pairs) == 6
    assert outcome.resources["candidate_fraction"] == 1.0


def test_structural_screen_falls_back_corrupt_input_to_singleton(
    tmp_path: Path, monkeypatch
) -> None:
    paths = fixture_paths(tmp_path, ["good-a.jpg", "corrupt.jpg", "good-b.jpg"])

    def build(path: str, _config: StructuralConfig) -> np.ndarray:
        if Path(path).name == "corrupt.jpg":
            raise ValueError("fixture decode failure")
        return np.asarray([1.0, 0.0], dtype=np.float32)

    monkeypatch.setattr(solution, "_build_descriptor", build)

    outcome = generate_structural_candidates(paths, screen_config())

    assert outcome.fallback_filenames == ("corrupt.jpg",)
    assert outcome.candidate_pairs == (("good-a.jpg", "good-b.jpg"),)
