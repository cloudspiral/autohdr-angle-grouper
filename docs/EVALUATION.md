# Evaluation workflow

Phase 0 treats scoring, dataset fingerprints, split definitions, and the run
registry as test infrastructure. The existing structural algorithm remains the
B1 benchmark; it is not assumed to be the final architecture.

## Commands

Audit the official sample after downloading and extracting it under the ignored
`data/` directory:

```bash
.venv/bin/python -m autohdr_eval audit \
  --dataset-root data/sample \
  --manifest data/sample/public_manifest.csv \
  --archive data/downloads/autohdr_sample_500.zip \
  --output artifacts/datasets/autohdr-sample-500-audit.json
```

Run the singleton contract control and structural baseline through the same
scorer:

```bash
.venv/bin/python -m autohdr_eval run \
  --config configs/b0-singletons.json \
  --dataset-root data/sample \
  --manifest data/sample/public_manifest.csv \
  --audit artifacts/datasets/autohdr-sample-500-audit.json \
  --split splits/sample-smoke-v1.json

.venv/bin/python -m autohdr_eval run \
  --config configs/b1-structural.json \
  --dataset-root data/sample \
  --manifest data/sample/public_manifest.csv \
  --audit artifacts/datasets/autohdr-sample-500-audit.json \
  --split splits/sample-smoke-v1.json

.venv/bin/python -m autohdr_eval run \
  --config configs/b2-classical.json \
  --dataset-root data/sample \
  --manifest data/sample/public_manifest.csv \
  --audit artifacts/datasets/autohdr-sample-500-audit.json \
  --split splits/sample-scale-051-v1.json
```

The B2 configuration extracts RootSIFT descriptors, measures every unordered
pair with mutual ratio matches and partial-affine RANSAC, and groups only with
positive geometric support. Raw pair measurements are cached separately from
the classification thresholds under ignored `artifacts/cache/`, so changing
state or grouping thresholds does not repeat feature matching. The 51-image
split above is a bounded smoke and cache check; do not infer that all-pairs is
viable for the complete 5K package.

Score an existing CSV or inspect recent registered runs:

```bash
.venv/bin/python -m autohdr_eval score \
  --reference data/sample/public_manifest.csv \
  --predictions /path/to/predictions.csv

.venv/bin/python -m autohdr_eval summarize
```

Compare two enriched dataset audits before treating their scores as independent,
then render the filename-level group failures from any completed run:

```bash
.venv/bin/python -m autohdr_eval compare-audits \
  --left artifacts/datasets/autohdr-sample-500-audit.json \
  --right artifacts/datasets/autohdr-medium-5000-audit.json \
  --output artifacts/datasets/sample-vs-medium-overlap.json

.venv/bin/python -m autohdr_eval gallery \
  --dataset-root data/sample \
  --diagnostics /path/to/run/diagnostics.json \
  --output-dir /path/to/run/gallery
```

Run outputs are stored under content-addressed paths in `artifacts/runs/` and
indexed by `artifacts/run-registry.sqlite3`. Both locations are ignored by Git.
Each run records the git commit and dirty-tree state, canonical config and split
hashes, dataset fingerprint, environment, exact-group metrics, wall time, peak
RSS, and artifact paths.

B2 runs additionally write `classical_summary.json` and
`pair_diagnostics.json`. Pair diagnostics report positive precision,
same-group-pair recall, negative precision, state coverage, and bounded examples;
they support failure analysis but do not replace exact-group scoring.

The audit artifact records SHA-256, difference hash, and manifest group for every
image. Supplying `--audit` makes the runner re-hash the requested package and
fail before scoring if the manifest, inventory, or any image bytes differ from
the audited package. `compare-audits` measures shared names, exact content,
perceptual collisions, and pairwise label-relation disagreements without
assuming that numeric group IDs are stable between packages.

## Early scale curve

The committed `sample-scale-051-v1.json`, `sample-scale-102-v1.json`, and
`sample-scale-203-v1.json` files are nested whole-reference-group subsets. Run B1
with each one by substituting it for the `--split` value above, followed by the
complete `sample-smoke-v1.json` split. Record `image_count`,
`candidate_pair_count`, `wall_seconds`, and `peak_rss_bytes` from each run.

These subsets are resource probes only. They are selected in a fixed group-ID
order, are not independent folds, and must not be used to compare accuracy or
tune thresholds. The measured Phase 0 curve is summarized in
`autohdr_codex_plan/RESULTS.md`.

## Larger-package check

The archive advertised as 5K audited to 2,126 images and completely nests the
366-image sample byte-for-byte. `medium-exclusive-100-v1.json` excludes every
sample group ID, then selects 24 complete medium-only reference groups totaling
100 images. Run B1 and B2 against the same fixed slice:

```bash
.venv/bin/python -m autohdr_eval run \
  --config configs/b1-structural.json \
  --dataset-root data/medium \
  --manifest data/medium/public_manifest.csv \
  --audit artifacts/datasets/autohdr-medium-5000-audit.json \
  --split splits/medium-exclusive-100-v1.json

.venv/bin/python -m autohdr_eval run \
  --config configs/b2-classical.json \
  --dataset-root data/medium \
  --manifest data/medium/public_manifest.csv \
  --audit artifacts/datasets/autohdr-medium-5000-audit.json \
  --split splits/medium-exclusive-100-v1.json
```

This is a fixed Phase 1 generalization check, not a tuning fold. Its groups are
content-exclusive from the sample, but neither package exposes the photoshoot or
property boundary required for a leakage-safe development-fold claim. Do not run
B2 all-pairs over all 2,126 images: that would require 2,258,875 pair
comparisons, beyond the measured Phase 1 runtime profile.

## Configuration sweeps

Phase 2 sweep definitions commit candidate configs, fold paths, limitations, and
the fixed zero-merge ranking policy before execution. Run one definition with:

```bash
.venv/bin/python -m autohdr_eval sweep \
  --repo-root . \
  --definition experiments/phase2/sweep-01-feature.json \
  --dataset-root data/medium \
  --manifest data/medium/public_manifest.csv \
  --audit artifacts/datasets/autohdr-medium-5000-audit.json \
  --output experiments/phase2/results-01-feature.json
```

The report records every config and split hash, per-fold run ID, exact metrics,
aggregate micro/mean/worst-fold scores, merge and split damage, runtime, memory,
and feature/pair-cache reuse. A candidate with any merge damage ranks behind all
zero-merge candidates regardless of mean score. The Phase 1 exclusive slice is
not part of sweep definitions and is evaluated only after selecting the Phase 2
candidate.

## Split and holdout safety

The sample package is smoke evidence only. It is not a protected holdout and is
not suitable for final model selection.

Ordinary `run` rejects a split with `"protected": true`. The separate
`final-evaluate` command requires all of the following before scoring:

- a clean working tree at the declared frozen commit;
- the exact frozen config hash;
- the exact canonical split hash;
- a split explicitly marked protected.

No protected split should be created until package overlap and the best available
photoshoot/property grouping unit are known.

## Interpretation boundaries

- Exact-group score is the selection metric. Pair diagnostics are supporting
  evidence only.
- The public filenames visibly encode group IDs, so filenames and paths must
  never be model inputs.
- If the manifest exposes only `filename,group_id`, reference-group-disjoint
  folds do not prove photoshoot- or property-level leakage safety.
- A corrupt image deterministically falls back to a singleton so every input is
  still represented exactly once.
