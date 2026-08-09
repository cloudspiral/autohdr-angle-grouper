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
```

Score an existing CSV or inspect recent registered runs:

```bash
.venv/bin/python -m autohdr_eval score \
  --reference data/sample/public_manifest.csv \
  --predictions /path/to/predictions.csv

.venv/bin/python -m autohdr_eval summarize
```

Run outputs are stored under content-addressed paths in `artifacts/runs/` and
indexed by `artifacts/run-registry.sqlite3`. Both locations are ignored by Git.
Each run records the git commit and dirty-tree state, canonical config and split
hashes, dataset fingerprint, environment, exact-group metrics, wall time, peak
RSS, and artifact paths.

The audit artifact records a SHA-256 for every manifest image. Supplying
`--audit` makes the runner re-hash the requested package and fail before scoring
if the manifest, inventory, or any image bytes differ from the audited package.

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
