# AutoHDR contract and project policies

This file separates official competition requirements from project-level choices. Official requirements are not optimization knobs.

## Source hierarchy

Use this order when sources disagree:

1. The live official competition page and official starter repository at the time of implementation.
2. The supplied `sources/PROJECT_REQUIREMENTS.pdf`.
3. Project policies in this file.
4. Assumptions recorded elsewhere.

Do not silently reconcile conflicts. Record the conflict and chosen interpretation in `RESULTS.md`. Prefer the newer official source after confirming it is genuinely current.

Official starter repository as of 2026-08-08:

- <https://github.com/AutoHDRHackathon/autohdr-challenge-starter>
- Relevant files: `README.md`, `solution.py`, `SCORING.md`, and `SUBMISSION_GUIDE.md`.

## Official task

Given an unordered folder of real-estate photos from a photoshoot, partition the images into groups that share the same camera angle. A camera angle may have multiple exposure-bracketed images. Different viewpoints must remain separate.

The current official `solution.py` describes each runtime input folder as images from a **single photoshoot**. Treat that as the expected runtime unit unless the live contract changes.

## Runtime input and output

- Read images from `/input/images/`.
- The input mount is read-only.
- The brief describes JPEG input resized to a maximum dimension of 1024 px. The current starter code also discovers `.jpg`, `.jpeg`, and `.png`; supporting all three is harmless robustness.
- Write `/output/predictions.csv`.
- Required headers are `filename` and `group_id`.
- Use basenames only, not paths.
- Every discovered input image must appear exactly once.
- Images in the same predicted group must share a `group_id`.
- Group ID values and row order do not matter.
- Preserve the external `group_images(image_paths: list[str]) -> list[list[str]]` behavior expected by the starter, even if the implementation is internally refactored.
- Print useful progress to stdout.

## Scoring

```text
score = exact_matches / total_reference_groups
```

A predicted group receives credit only when its set of filenames exactly equals a reference group. There is no partial credit.

Consequences:

- Merging two true groups can destroy credit for both.
- Splitting one true group destroys credit for that group.
- Pairwise accuracy is diagnostic only; final selection must use exact-group scoring.
- A conservative merge policy is sensible, but an overly strict clique requirement can incorrectly split legitimate extreme-exposure brackets.

Before algorithm work proceeds, inspect the live official `SCORING.md`, explicitly verify that the denominator is the number of reference groups, record the checked source revision or file fingerprint in `RESULTS.md`, implement that behavior locally, and lock regression tests to the official examples.

## Runtime and submission limits

- No internet access during container execution.
- CPU only.
- `cpu-large`: 8 vCPU, 16 GB RAM.
- `cpu-xlarge`: 16 vCPU, 32 GB RAM.
- Runtime documentation currently conflicts: the supplied PDF and live starter
  README say 60 minutes, while the live `SUBMISSION_GUIDE.md` says 30 minutes for
  `cpu-large` and 45 minutes for `cpu-xlarge`. Engineer to the stricter limits
  until the organizer confirms the platform configuration.
- Build and test for `linux/amd64`.
- Maximum three competition submissions per day.
- The final Docker repository must be public according to the supplied brief/submission guide.
- Docker publication and Codabench submission require explicit human approval.

### Submission mechanics

For each approved finalist, Codex should prepare locally:

- a stable Docker image tag plus immutable image digest;
- `submission.yaml` containing `docker_image`, `machine_type`, and the registered competition email;
- `submission.zip` containing `submission.yaml`;
- exact Docker Hub push and Codabench upload instructions.

When Docker Hub credentials, namespace, or the registered email are unavailable, leave explicit placeholders and request them only at the handoff point. Do not log credentials. Do not push a public image or upload to Codabench until the user explicitly approves the selected candidate and external action.

## Currently advertised labeled data

The current official starter repository advertises packages containing images plus `public_manifest.csv` labels:

- 500 images, approximately 2 GB;
- 5,000 images, approximately 21 GB;
- 10,000 images, approximately 42 GB.

It also advertises a full image corpus of 276K images, approximately 1.1 TB. The supplied PDF says 266K images. Treat this as documentation drift, not something to guess about. Verify the live source and record the result.

Do not assume:

- the 500, 5K, and 10K packages are disjoint;
- the smaller packages are not subsets of the larger package;
- the full corpus has authoritative labels;
- the manifest contains photoshoot or property boundaries.

Audit those facts before constructing splits or downloading more than the 500-image package.

## Project policies, not organizer rules

These choices are intended to improve robustness and reproducibility. They may be changed only with a documented reason.

### Metadata policy

- Random filenames and paths are never grouping evidence.
- EXIF orientation may be used only to decode pixels correctly.
- Do not use timestamps, camera serials, sequence numbers, GPS, or other EXIF fields as grouping signals unless the organizer explicitly confirms they are valid and the policy is deliberately revised.

### Determinism

- Sort discovered inputs before processing.
- Seed every stochastic component.
- Make group assignment independent of filesystem iteration order, worker completion order, and candidate-processing order.
- Canonically order filenames inside groups and groups in debug artifacts.

### Failure handling

- A corrupt or unsupported image must not cause other inputs to disappear from the CSV.
- Log the failure and fall back to a singleton for that image unless a safer deterministic recovery exists.
- Validate exactly-once membership immediately before writing output.

### Runtime isolation

- No external API or hosted-model call may be part of the submitted pipeline.
- Any pretrained weights must ship inside the image, pass license/rule review, have checksums, and never be downloaded at runtime.
- An external vision model may be used only as optional development-time error analysis; it is not a scoring authority and must not influence protected holdout labels.

## Open rule questions to verify early

- Current rules for pretrained models and external training data.
- Whether the labeled archives include shoot/property/source-sequence metadata.
- Whether the package hierarchy overlaps or nests.
- Whether the full corpus has labels and is approved for training.
- Whether the platform imposes an undocumented Docker-image-size limit.

A rule question may block a dependent experiment, but it must not block the classical baseline or evaluator work.

## Contract acceptance tests

The repository must include automated tests for at least:

1. Exact reproduction of the official scoring examples.
2. Every input appearing exactly once in a valid partition.
3. Missing, duplicate, extra, and path-containing filenames being rejected by validation.
4. Arbitrary group IDs and row order producing the same score.
5. Empty input producing a valid header-only CSV or another explicitly tested contract behavior.
6. One corrupt image being represented deterministically rather than crashing the full run.
7. Repeat runs with the same config producing byte-equivalent predictions.
8. Container execution with `/input/images` mounted read-only and output written to `/output/predictions.csv`.
