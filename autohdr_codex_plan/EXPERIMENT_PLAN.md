# AutoHDR experiment and eval plan

## Purpose

This project uses eval-driven development. The evaluator measures a run; an experiment changes a controlled part of the system; the Codex loop chooses, executes, and records experiments.

```text
Codex/orchestrator
  + immutable evaluator
  + deterministic configs
  + versioned caches
  + run registry
  + error analysis
  + promotion and stopping rules
  = the bounded software-factory loop
```

The goal is not to keep changing code until one number spikes. The goal is to freeze the simplest configuration that performs robustly across unseen development folds, survives a protected holdout, and fits the container budget.

## Non-negotiable guardrails

- Never tune against the protected final holdout.
- Never change the evaluator or split to rescue a disappointing result.
- Never select a solution using pair metrics alone.
- Never run a huge Cartesian product across architecture, features, geometry, grouping, and runtime knobs simultaneously.
- Never accept an architectural change without a stated hypothesis and a controlled comparison.
- Never publish or submit automatically.
- Record failed and reverted experiments; do not erase them.

## 1. Data audit and split construction

### Step 1 — 500-image package

Download the labeled 500-image package first. Audit and record:

- manifest columns and semantics;
- archive directory structure;
- number of images and groups;
- group-size distribution;
- image format, dimensions, corruption rate, and duplicates;
- whether shoot/property/source-sequence identifiers exist;
- whether multiple photoshoots are distinguishable;
- exposure/clipping distributions;
- actual all-pairs runtime at this scale.

Use this package for smoke tests, visual inspection, and evaluator validation—not final model selection.

### Step 2 — package overlap

Before treating 500, 5K, and 10K as independent data, check overlap using:

- exact filenames;
- cryptographic file hashes;
- perceptual hashes for recompressed duplicates;
- manifest group relationships where possible.

If smaller packages are subsets of the 10K package, use one canonical copy and construct all splits from it.

### Step 3 — development and holdout units

Preferred split unit, in order:

1. organizer-provided photoshoot/source-sequence ID;
2. archive directory or other verified photoshoot boundary;
3. property ID;
4. reference group as a fallback.

Never split images from the same reference group across folds.

If only `filename,group_id` is available, use deterministic group-disjoint folds and explicitly record that this does not guarantee shoot/property isolation. Do not claim leakage-safe generalization beyond what the metadata supports.

### Recommended partition

After overlap and metadata audit:

- reserve approximately 15–20% of the largest labeled package as a protected final holdout at the best available unit;
- use the remainder for three to five deterministic development folds;
- optionally reserve a training partition inside development data if fitting a pair calibrator.

Store split manifests under version control. Include a seed, source-package fingerprint, and split-generation code. Once frozen, do not regenerate because a result is inconvenient.

### Pair-sampling data

Pair-level datasets are for diagnostics and calibrator training only.

- Positive pairs: stratify by exposure difference, clipping, group size, and visual quality.
- Negative pairs: prioritize hard negatives from similar rooms, adjacent viewpoints, and nearest neighbors; do not let random unrelated rooms dominate.
- Keep all pairs from one reference group on one side of any train/validation boundary.
- Final acceptance still uses complete grouping runs.

## 2. Evaluation layers

### Layer A — contract tests

Fast tests for discovery, partition validity, CSV output, determinism, and official scoring examples.

### Layer B — synthetic/behavioral tests

Small constructed cases for algorithm behavior:

- all singletons;
- perfect triplet;
- dark–mid–bright chain with unknown dark–bright edge;
- false bridge between two groups;
- strong negative veto;
- corrupt image fallback;
- deterministic output under shuffled input order.

These tests protect logic but make no accuracy claim.

### Layer C — official labeled development evaluation

Run the entire grouping pipeline on complete evaluation units and score exact groups. This is the main optimization layer.

### Layer D — protected holdout

Run only after development selection is frozen. A holdout result may reveal risk but must not trigger repeated tuning against that same holdout. Ordinary development commands must exclude the holdout by default; require an explicit holdout command that records the frozen commit, config hash, and split fingerprint before revealing the score.

### Layer E — exact container benchmark

Run a minimal container smoke test early to catch path, platform, and dependency failures. Near freeze, build the actual `linux/amd64` submission image and run it with realistic CPU/RAM limits, read-only input mount, cold startup, and no network. Native and container predictions must match.

### Layer F — Codabench

Use only for a few materially distinct finalists. Do not spend the three-per-day allowance on tiny threshold changes.

## 3. Metrics

### Primary selection metric

- `exact_group_score = exact_reference_groups / total_reference_groups`

### Required group diagnostics

- exact score for singleton reference groups;
- exact score for non-singleton reference groups;
- exact score by true group size bucket;
- count and fraction of reference groups damaged by a predicted merge;
- count and fraction of reference groups split across multiple predictions;
- predicted exact-group precision, as a diagnostic;
- predicted and reference group-size distributions;
- number of singleton predictions.

### Candidate/pair diagnostics

- candidate recall over true same-group pairs;
- true-group graph connectivity after candidate generation;
- pair precision/recall by positive/negative/unknown state;
- metrics stratified by exposure difference and clipping;
- transform-estimation success and failure reasons;
- calibration curves when using a learned pair score.

### Resource metrics

- wall-clock runtime;
- peak RSS;
- time and memory by pipeline stage;
- number of images and candidate pairs;
- feature counts and cache hit rates;
- Docker image size and cold-start time.

Do not combine accuracy and runtime into one opaque score. Use explicit promotion gates.

## 4. Experiment infrastructure

### Required CLI behavior

Implement equivalent commands, names flexible:

```text
run one config on one split
run a bounded sweep from a sweep specification
summarize selected runs
render an error gallery
build and benchmark the submission container
```

Every run must be reproducible from a committed config plus source revision.

### Run record

Record at least:

```yaml
run_id: unique-stable-id
started_at: timestamp
git_commit: revision
dirty_tree: true|false
config_path: path
config_hash: hash
dataset_fingerprint: hash
split_id: identifier
cache_schema_versions: {}
seed: integer
status: running|passed|failed|reverted
parent_run_id: optional
hypothesis_id: optional
metrics: {}
resources: {}
artifact_paths: {}
notes: string
```

Use JSONL, SQLite, or another queryable local registry as the source of truth. `RESULTS.md` is the curated human summary, not the only run database.

### Artifacts per run

- resolved config;
- logs and timing profile;
- predictions CSV;
- metrics JSON;
- pair/group diagnostic summaries;
- sampled false-merge and false-split gallery;
- environment and package versions;
- cache fingerprints.

### Cache boundaries

Cache in layers so cheap experiments remain cheap:

1. preprocessing/statistics;
2. local/global features;
3. candidate pairs;
4. raw pair evidence and transforms;
5. calibrated pair state;
6. grouping result.

A grouping sweep should reuse layer 4 or 5. A threshold change must not rerun feature extraction or RANSAC.

## 5. Development phases and exit criteria

### Phase 0 — Audit and trustworthy evaluator

Tasks:

- inspect repository and live rules;
- audit the 500-image package;
- treat the maximum private runtime batch size as unknown even if the expected unit is one photoshoot: verify what the live sources support, inspect any usable public shoot boundaries, and record the uncertainty in `RESULTS.md`;
- add an early scale benchmark and measure representative input sizes as soon as the first pair-comparison path exists; do not defer the first all-pairs scale curve to Phase 4;
- implement official scorer and contract validator;
- create immutable splits and run registry skeleton;
- implement B0 singleton baseline;
- add behavioral tests;
- build and run an early starter-compatible Docker smoke image to catch path, platform, and dependency failures without waiting for final packaging.

Exit when:

- official scoring examples pass;
- repeat runs are deterministic;
- invalid partitions are caught;
- B0 produces a fully valid result and recorded score;
- the private-batch-size uncertainty and initial scale-benchmark procedure are recorded.

### Phase 1 — Simple end-to-end classical baseline

Tasks:

- implement preprocessing views and stats;
- implement B1 direct structural baseline;
- implement B2 SIFT/RootSIFT-style pair evidence;
- implement a minimal tri-state grouping policy;
- run all pairs;
- render error galleries.

Exit when:

- the pipeline runs end-to-end on 500 and at least one larger development slice;
- pair records and transforms are cached;
- exact score, merge/split diagnostics, runtime, and memory are available;
- the main failure modes are visible rather than guessed.

### Phase 2 — Controlled configuration optimization

Freeze architecture temporarily and sweep configuration only.

Tune in blocks, not one giant product:

1. preprocessing/working resolution;
2. local-feature and matching controls;
3. transform model and RANSAC controls;
4. pair-state calibration/thresholds;
5. grouping thresholds and support rules;
6. parallelism/runtime settings.

Use coarse-to-fine sweeps. Narrow each block before moving to the next, then run a small joint refinement around the best stable region.

Exit when:

- two bounded sweep batches fail to produce a robust material gain;
- the champion is stable across nearby configurations and folds;
- remaining errors suggest an architectural rather than threshold problem.

### Phase 3 — Codex researcher loop

For each cycle:

1. Rank failure categories by damaged reference groups, not by anecdotal visual interest.
2. Choose one category.
3. Write a falsifiable hypothesis in `RESULTS.md`.
4. Implement one architectural change.
5. Run contract regressions, targeted cases, and full development folds.
6. Accept or revert.
7. Update the decision log and error taxonomy.

Examples:

- Extreme-exposure false splits -> test unknown-edge handling, alternate normalization, or transform-chain support.
- Adjacent-view false merges -> strengthen low-DOF transform plausibility, coverage, or negative evidence.
- Flexible homography false positives -> prefer partial affine or penalize projective distortion.
- Local-feature ceiling -> compare one learned local model against the classical champion.
- Pair matching dominates runtime at realistic `n` -> test cheap screening or retrieval with measured recall.

Exit when:

- two consecutive researcher cycles produce no robust material gain; or
- the remaining gain is not worth complexity/runtime risk.

### Phase 4 — Scale and packaging

Tasks:

- benchmark realistic batch sizes;
- decide whether all-pairs remains viable;
- add retrieval only if required;
- tune bounded parallelism;
- build the exact offline `linux/amd64` image;
- test cold runs under both machine profiles when practical;
- verify packaged weights/licenses if any.

Exit when:

- the champion has comfortable time and memory headroom;
- container predictions match native predictions;
- no runtime download or hidden service dependency exists.

### Phase 5 — Freeze and final validation

1. Freeze source revision, dependency lock, config, split manifests, and model assets.
2. Run the protected holdout once.
3. Do not tune on that result. Only fix clear contract/packaging bugs, then document the exception.
4. Produce one to three materially distinct submission candidates.
5. Recommend one default candidate, balancing score, fold stability, false-merge risk, and runtime.
6. Build and tag the exact local image for each finalist; record its image digest, config hash, and benchmark evidence.
7. Prepare a completed `submission.yaml`, `submission.zip`, and copy-paste Docker Hub/Codabench handoff instructions for the recommended candidate.
8. Await explicit human approval before any public Docker push or Codabench upload. Never publish or submit automatically.

## 6. Knob taxonomy

### Fixed before optimization

These are tests or constraints, not knobs:

- exact scorer semantics;
- every image exactly once;
- offline execution;
- output schema and paths;
- deterministic split manifests;
- protected holdout membership;
- runtime/machine limits.

### Config knobs suited to autonomous sweeps

#### Preprocessing

- working dimension;
- normalization mode and mild parameters;
- gradient/edge representation;
- whether raw and normalized evidence are both retained.

#### Local features and matching

- feature family within a frozen architecture;
- feature/landmark budget;
- detector thresholds;
- ratio and distance thresholds;
- mutual-match requirement.

#### Geometry

- transform model;
- RANSAC reprojection threshold, confidence, and iteration budget;
- minimum inliers, inlier ratio, and coverage;
- transform-plausibility limits;
- structural-residual threshold.

#### Pair states

- positive and strong-positive thresholds;
- negative-evidence thresholds;
- unknown policy;
- deterministic score weights or fitted calibrator parameters.

#### Grouping

- minimum independent support;
- representative count and attachment threshold;
- negative veto strength;
- bridge threshold;
- transform cycle/composition tolerance;
- weak group-size/exposure prior weights.

#### Candidate generation, only if needed

- all-pairs/retrieval crossover rule;
- global input view and model;
- top `K` and threshold overflow;
- exact versus approximate search settings.

#### Runtime

- worker count;
- OpenCV/BLAS/model thread limits;
- batch sizes and cache policy.

Initial numeric ranges should be chosen after inspecting metric distributions and runtime profiles. Do not guess one enormous grid in advance.

### Architectural hypotheses, not blind sweep knobs

- direct structural versus local-feature matching;
- SIFT/RootSIFT versus a learned local feature;
- partial affine versus full affine/homography strategy;
- deterministic pair rule versus fitted calibrator;
- connected components versus representative or constrained agglomerative grouping;
- all-pairs versus retrieval-pruned candidates;
- classical matcher versus learned matcher.

Test these one at a time with controlled ablations.

## 7. Promotion rules

A candidate may replace the champion only when it:

- improves mean development exact-group score by a material amount, or achieves an accuracy tie with meaningful simplicity/runtime benefit;
- does not rely on one anomalous fold;
- does not materially worsen worst-fold behavior;
- does not create an unacceptable increase in false-merge damage;
- remains within resource headroom;
- passes contract and behavioral regressions.

Treat a broad plateau as more trustworthy than a narrow peak. Re-run top candidates with multiple seeds only when the algorithm contains actual stochasticity.

When two configurations are effectively tied, choose in this order:

1. lower false-merge damage;
2. better worst-fold score;
3. lower runtime and memory;
4. fewer models and dependencies;
5. simpler implementation.

## 8. Bounded autonomy and stopping

### Optimizer mode

- Code is frozen.
- Only committed config values vary.
- May run tens or hundreds of cached trials.
- Must stop at a configured finite trial count or convergence criterion and produce a ranked report.

### Researcher mode

- Code may change.
- One documented hypothesis per branch/commit.
- Must run regression and development comparisons.
- Must accept or revert explicitly.
- Must stop after the bounded cycle and update `RESULTS.md`.

### Default stopping signals

Stop optimization and move to freeze when any two are true:

- two bounded sweep/research batches yield no robust material gain;
- the best region is stable across folds and neighboring configs;
- remaining errors require disproportionate complexity;
- runtime headroom is shrinking below a safe margin.

Do not leave an unbounded self-modifying loop running indefinitely.

## 9. Leaderboard strategy

Use local labeled data as the main loop. Select up to three daily submissions that test genuinely different risk profiles, for example:

- conservative classical champion;
- higher-recall grouping variant;
- learned/retrieval-enhanced variant if locally justified.

Do not submit adjacent thresholds just to probe the private set. Record every submission image digest, config hash, local metrics, and leaderboard result in `RESULTS.md`.
