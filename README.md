# AutoHDR Angle Grouper

An offline, Dockerized Python solution for the [AutoHDR Image Grouping
Challenge](https://github.com/AutoHDRHackathon/autohdr-challenge-starter). Given
the JPEGs from one real-estate photoshoot, it must group exposure brackets and
other images captured from the same camera angle.

The repository is also configured as a small OpenAI Symphony software factory:
an issue labeled `symphony-ready` can be implemented on an isolated branch and
handed back as a tested pull request for human review.

## Current status

The checked-in implementation is a deterministic, CPU-only structural baseline.
It normalizes exposure and groups sufficiently similar image geometry while
preserving the challenge's I/O contract. On the complete official sample package,
it scores 60/69 exact reference groups as a smoke result. That package is not a
valid development fold, so this is not a leaderboard or generalization claim.

Phase 0 evaluation infrastructure now keeps that implementation as B1 and adds a
singleton B0 control, official exact-group scoring, strict CSV validation,
content-hashed configs and splits, a SQLite run registry, dataset auditing, and a
protected-holdout gate. See [`docs/EVALUATION.md`](docs/EVALUATION.md).

The evaluation-only B2 classical pipeline is intentionally separate from the
default `solution.py` entrypoint. Its frozen Phase 2 config scores 76/76 exact
groups with zero merge damage across three 100-image reference-group-disjoint
development folds, then ties Phase 1 B2 at 22/24 with a byte-identical partition
on the one-time reserved slice. These are provisional local measurements, not a
protected-holdout or leaderboard claim; promotion into the submission entrypoint
belongs to a later packaging issue after x86/container validation.

## Grouping algorithm

For each image, `solution.py` decodes grayscale pixels with EXIF orientation
applied solely for correct pixel decoding, resizes them to a fixed working canvas,
and applies a percentile contrast stretch followed by histogram equalization. No
other metadata is a grouping signal. The descriptor concatenates:

- a blurred, mean-centered luminance layout; and
- six unsigned Sobel-gradient orientation channels, with soft orientation-bin
  assignment.

Both feature families are Gaussian pooled onto a small spatial grid and normalized
before a weighted concatenation. Pooling makes modest translations less likely to
cause an automatic split, while gradients retain view geometry after global
exposure changes. Pairwise cosine distances form an undirected threshold graph;
connected components become groups. Filenames and paths are used only to read the
pixels and produce stable filename-only output. They do not affect graph edges or
group membership.

For `N` images, `P` decoded pixels per image, and descriptor length `D`, descriptor
construction is `O(NP)` and all-pairs clustering is `O(N^2 D)`. The working
descriptor has `D = (1 + 6) * 16^2 = 1,792` values. Memory is `O(ND + N)` beyond
the image decoder; the code does not allocate an `N`-by-`N` distance matrix.

### Calibration points

The named constants in `solution.py` are deliberately exposed for later tuning on
labeled AutoHDR data:

| Constant | Baseline value | Purpose |
| --- | ---: | --- |
| `DESCRIPTOR_IMAGE_SIZE` | 96 px | Fixed canvas balancing retained geometry and CPU cost. |
| `DESCRIPTOR_GRID_SIZE` | 16 px | Spatial pooling resolution and descriptor size. |
| `EXPOSURE_LOW_PERCENTILE` / `EXPOSURE_HIGH_PERCENTILE` | 2 / 98 | Robust endpoints for exposure normalization. |
| `GRADIENT_ORIENTATION_BINS` | 6 | Unsigned structural direction resolution. |
| `SPATIAL_POOLING_SIGMA` | 2.0 px | Translation tolerance versus edge localization. |
| `LUMINANCE_FEATURE_WEIGHT` / `GRADIENT_FEATURE_WEIGHT` | 0.35 / 0.65 | Layout versus exposure-robust edge evidence. |
| `STRUCTURAL_DISTANCE_THRESHOLD` | 0.16 | Maximum cosine distance that creates a graph edge. |

The distance threshold, pooling strength, and component-linkage policy are the
highest-priority calibration targets because exact-match scoring penalizes both
over-merging and over-splitting.

### Known risks

- False merges can occur for repeated room layouts, nearly featureless images, or
  a chain of individually similar images connected transitively through the
  threshold graph.
- False splits can occur after severe highlight/shadow clipping, translations
  larger than the pooling tolerance, crop/rotation/parallax changes, or geometry
  that disappears at the fixed descriptor resolution.
- Resizing every image to a square can weaken discrimination between images with
  materially different aspect ratios.
- Synthetic fixtures prove deterministic mechanics only. Threshold quality and
  runtime headroom still require measurement on representative, labeled AutoHDR
  shoots without leaking filenames or metadata into the model.

## Challenge contract

- Read JPEG/PNG images from the read-only `/input/images/` mount.
- Write `/output/predictions.csv` with `filename,group_id` columns.
- Include every input filename exactly once and never include paths.
- Run offline and print progress to stdout.
- Until the organizer resolves conflicting official documentation, target the
  stricter advertised limits: 30 minutes on `cpu-large` and 45 minutes on
  `cpu-xlarge`; the starter README and supplied PDF instead say 60 minutes.
- Build for `linux/amd64` when developing on Apple Silicon.

The local source brief was verified page by page and is summarized in
[`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md). The current official starter is
tracked as the `upstream` Git remote.

## Local development

Python 3.11 is the reference runtime.

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --requirement requirements-dev.txt
.venv/bin/ruff check .
.venv/bin/python -m pytest
```

Run the contract locally without Docker:

```bash
.venv/bin/python solution.py --input-dir /path/to/images --output-dir /tmp/autohdr-output
```

Build and run the challenge container:

```bash
docker build --platform linux/amd64 -t autohdr-angle-grouper:local .
docker run --rm \
  --network none \
  --mount type=bind,src=/path/to/images,dst=/input/images,readonly \
  --mount type=bind,src=/tmp/autohdr-output,dst=/output \
  autohdr-angle-grouper:local
```

## Data and evaluation

Training data is intentionally not committed. AutoHDR currently publishes sample,
medium, and large downloads through the official starter repository. The archive
advertised as the 500-image sample currently contains 366 images plus its
manifest; this is recorded as documentation drift rather than silently treated as
500 observations. Downloaded images, local outputs, experiment artifacts, and
packaged submissions are ignored by Git.

Scoring gives credit only when a predicted group exactly matches a labeled
group; partial overlaps receive no credit. See [`SCORING.md`](SCORING.md).

## Submission boundary

The repository can build a submission, but no unattended agent may register for
the contest, publish a Docker image, upload to Codabench, or merge its own pull
request. Those remain explicit human actions. Copy and edit `submission.yaml`
only when you are ready to publish under your own Docker Hub and contest account.

## Upstream provenance

Bootstrapped from
[`AutoHDRHackathon/autohdr-challenge-starter`](https://github.com/AutoHDRHackathon/autohdr-challenge-starter)
at commit `e2b08ffebbd0281e24567c1d5fc0e2111b1a6d85`.
