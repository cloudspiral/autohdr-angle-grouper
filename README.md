# AutoHDR Angle Grouper

An offline, Dockerized Python solution for the [AutoHDR Image Grouping
Challenge](https://github.com/AutoHDRHackathon/autohdr-challenge-starter). Given
the JPEGs from one real-estate photoshoot, it must group exposure brackets and
other images captured from the same camera angle.

The repository is also configured as a small OpenAI Symphony software factory:
an issue labeled `symphony-ready` can be implemented on an isolated branch and
handed back as a tested pull request for human review.

## Current status

The checked-in implementation is the deterministic singleton baseline. It
satisfies the I/O contract and provides a tested foundation, but it intentionally
does not identify HDR brackets yet. Algorithm improvements are developed through
bounded GitHub issues so their code, tests, and tradeoffs remain reviewable.

## Challenge contract

- Read JPEG/PNG images from the read-only `/input/images/` mount.
- Write `/output/predictions.csv` with `filename,group_id` columns.
- Include every input filename exactly once and never include paths.
- Run offline, print progress to stdout, and complete within 60 minutes.
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

Training data is intentionally not committed. AutoHDR currently publishes
sample, medium, and large downloads through the official starter repository.
Downloaded images, local outputs, and packaged submissions are ignored by Git.

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
