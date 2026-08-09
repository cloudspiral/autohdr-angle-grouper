# AutoHDR Angle Grouper

An offline, Dockerized Python solution for the [AutoHDR Image Grouping
Challenge](https://github.com/AutoHDRHackathon/autohdr-challenge-starter). Given
the JPEGs from one real-estate photoshoot, it must group exposure brackets and
other images captured from the same camera angle.

The repository is also configured as a small OpenAI Symphony software factory:
an issue labeled `symphony-ready` can be implemented on an isolated branch and
handed back as a tested pull request for human review.

## Current status

The checked-in `solution.py` is the deterministic, CPU-only Phase 5 finalist.
It uses a cheap structural screen to nominate pairs, then
requires local geometric evidence before grouping. It preserves the challenge's
public function, input mount, and CSV output contracts without runtime downloads,
model weights, persistent caches, filename-derived grouping, or network services.

Phase 0 evaluation infrastructure retains the original structural implementation
as B1 and adds a singleton B0 control, official exact-group scoring, strict CSV
validation, content-hashed configs and splits, a SQLite run registry, dataset
auditing, and a protected-holdout gate. See
[`docs/EVALUATION.md`](docs/EVALUATION.md).

The screened entrypoint reproduces the full Phase 3 dual-view partition on all
six development folds: 161/162 exact groups with zero merge damage. Its single
protected run from clean frozen commit `532cc1b` scores 109/110 exact groups
(99.09%) with zero merge damage and one conservative split. At 100
images it evaluates at most 861 of 4,950 possible pairs per view. The exact
cache-free native path completes the 366-image public resource probe twice in
about 119 seconds with a maximum 637 MB RSS and identical predictions. GitHub
Actions also passes the nontrivial native smoke and the read-only, no-network
`linux/amd64` container job. The holdout is reference-group-disjoint from all
previous evidence but is not photoshoot/property-disjoint because the organizer
did not supply that metadata. Representative x86 full-batch timing and
leaderboard performance remain unmeasured.

## Grouping algorithm

For batches of 64 images or fewer, the runtime evaluates every unordered pair.
Larger batches first compute the retained B1 exposure-normalized structural
descriptor and take the union of each image's 12 nearest neighbors, including
every exact distance tie. This screen only nominates expensive comparisons; its
similarity never creates a group edge.

Each candidate pair is evaluated under two grayscale views: CLAHE alone and a
1st–99th percentile stretch followed by CLAHE. Both extract RootSIFT features,
apply mutual ratio matching, fit a partial-affine transform with seeded RANSAC,
and measure inliers, coverage, transfer error, transform plausibility, and
post-warp gradient correlation. Each view classifies the pair as strong-positive,
positive, negative, or unknown. A negative in either view vetoes the pair;
otherwise the stronger nonnegative state survives. Support-aware grouping then
requires strong geometric evidence and distributed cross-group support while
treating missing or ambiguous evidence as neutral.

The structural screen computes exact cheap similarities in `O(N^2 D)` for the
1,792-value B1 descriptor. Expensive local comparison is all-pairs below the
crossover and approximately `O(NK)` above it for `K = 12`, with deterministic
tie expansion. Features and pair evidence remain in memory and are not written
to the read-only container filesystem. Filenames identify inputs and stable CSV
rows only; they do not rank candidates or determine membership.

### Calibration points

The runtime values are frozen in `configs/phase4/b2-screened-dual-clahe.json`:

| Parameter | Value | Purpose |
| --- | ---: | --- |
| All-pairs crossover / structural top-K | 64 / 12 | Keep small batches exact; bound expensive large-batch pairs. |
| Structural screen canvas / grid | 96 / 16 px | Cheap exposure-robust candidate ranking. |
| Local working dimension / SIFT features | 384 px / 256 | Bounded geometry feature budget. |
| Ratio / RANSAC threshold | 0.78 / 4 px | Mutual-match and robust-transform controls. |
| Strong-positive minimum | 6 inliers, 0.50 ratio, 0.125 coverage | Low-count evidence with strict multi-signal guards. |
| Group support / negative veto | 3 edges / enabled | Distributed attachment without unsafe chaining. |
| Requested OpenCV workers | 2 | Lowest worker count on the measured native timing plateau. |

### Known risks

- The known remaining development error is a conservative split where one label
  spans visibly shifted kitchen compositions and no safe wrong-group margin was
  found.
- Candidate screening can miss unusual true partners. Across the six development
  folds it retains 995/998 same-group pairs and connectivity for 161/162 groups;
  the one disconnected group is the already-unrecovered adjacent-view label.
- The protected holdout's candidate graph contains every true group, but one
  five-image group is conservatively split 4+1 by insufficient direct geometry.
  No tuning was performed after that one-time result.
- Feature extraction and the cheap exact structural screen still grow with input
  count, and representative private photoshoot sizes are unavailable.
- `linux/amd64` build and contract behavior are proven in CI, but representative
  8-vCPU/16-GB and 16-vCPU/32-GB x86 timing remains unmeasured.

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
.venv/bin/python -m pip install --requirement requirements-dev.lock
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

The repository can build and validate the human-gated `submission.zip`, but no
unattended agent may register for the contest, publish a Docker image, upload to
Codabench, or merge its own pull request. Those remain explicit human actions.
Copy and edit `submission.yaml` only when you are ready to publish under your
own Docker Hub and contest account.
See [`docs/SUBMISSION_HANDOFF.md`](docs/SUBMISSION_HANDOFF.md) for the frozen
tag, exact commands, remaining placeholders, and external-action checklist.

## Upstream provenance

Bootstrapped from
[`AutoHDRHackathon/autohdr-challenge-starter`](https://github.com/AutoHDRHackathon/autohdr-challenge-starter)
at commit `e2b08ffebbd0281e24567c1d5fc0e2111b1a6d85`.
