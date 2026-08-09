# AutoHDR architecture

## Status

This is the current target architecture, not a claim that every component will survive evaluation. Begin with the simplest classical system and add complexity only when a held-out ablation demonstrates a specific benefit.

## Design principles

1. **Geometry first.** Semantic or global visual similarity can nominate candidates but cannot prove a shared viewpoint.
2. **All-pairs first.** Runtime input is expected to be one photoshoot. Use exact all-pairs comparison until measured batch sizes or runtime show that candidate pruning is necessary.
3. **Classical baseline first.** Begin with exposure-robust normalization, local features, robust transform estimation, and post-alignment structure. Do not begin with multiple learned models.
4. **Tri-state pair evidence.** Distinguish positive evidence, negative evidence, and insufficient evidence. A failed match under an extreme exposure gap is often unknown, not proof of a different angle.
5. **Group evidence is not just edge thresholding.** Store transforms and detailed pair evidence, then make support-aware group decisions. Avoid irreversible incremental union-find chaining.
6. **Exact-match-aware conservatism.** False merges are costly, but strict cliques can over-split genuine brackets. Use strong negative evidence to veto; do not let missing evidence veto by itself.
7. **Evidence before complexity.** Retrieval models, learned local features, learned matchers, and pair calibrators are later experiments, not default architecture.

## Baseline ladder

Build in this order and retain each stage as a reproducible benchmark.

### B0 — Contract baseline

- Every image is a singleton.
- Purpose: validate discovery, CSV generation, scoring, run logging, and container mechanics.

### B1 — Direct structural baseline

- Create exposure-normalized grayscale and gradient views.
- Test inexpensive near-identity alignment, such as ECC or phase-correlation-assisted alignment.
- Score post-alignment gradient/edge agreement.
- Purpose: establish how far a very small deterministic method can go.

### B2 — Classical geometry baseline

- Detect and describe local features, initially SIFT or RootSIFT-style descriptors.
- Match descriptors with mutual-nearest and ratio/distance filtering.
- Estimate a low-degree-of-freedom transform with RANSAC.
- Compute geometry, coverage, transform-plausibility, and post-warp structural evidence.
- Form groups with a deterministic tri-state, support-aware policy.
- Use all unordered image pairs initially.

### B3+ — Evidence-gated enhancements

Only after B2 plateaus or misses a measured requirement:

- a small calibrated pair classifier;
- a stronger classical or learned local feature model;
- a learned local matcher;
- global retrieval and candidate pruning;
- approximate nearest-neighbor search;
- model/runtime conversion such as ONNX.

Each enhancement must beat the current champion on development folds without unacceptable runtime, memory, or robustness loss.

## End-to-end flow

```text
discover and decode images deterministically
  -> create normalized, gradient, and statistics views
  -> extract reusable local features
  -> enumerate candidate pairs (all-pairs by default)
  -> compute pair evidence and directed transforms
  -> classify each pair as positive, negative, or unknown
  -> form groups using support, representatives, negatives, and transform consistency
  -> validate the exact partition
  -> write predictions.csv and diagnostics
```

## 1. Image discovery and preprocessing

For each image:

- decode with orientation applied;
- keep the original dimensions and a deterministic content fingerprint;
- construct a configurable working-resolution image;
- derive:
  - grayscale/luminance view;
  - mildly exposure-normalized luminance view;
  - gradient or edge view;
  - optional raw-color view for diagnostics;
- calculate exposure and quality statistics:
  - luminance quantiles and median;
  - dark-clipped and bright-clipped fractions;
  - contrast/dynamic-range proxy;
  - sharpness proxy;
  - aspect ratio and resolution.

Initial normalization candidates:

- percentile luminance scaling;
- mild CLAHE on luminance;
- no normalization as a control.

Retinex or more aggressive normalization is a later experiment only if simpler normalization causes measured misses.

### Representative quality

Compute a deterministic information-quality score from clipping, contrast, and sharpness. Use it to choose likely group representatives. A normally exposed, sharp image is usually more useful than the first filename or an extreme bracket.

## 2. Candidate-pair generation

### Default

Evaluate all unordered pairs for the classical baseline. First measure:

- runtime as a function of batch size;
- actual private-like photoshoot size distribution if it can be inferred from labeled data;
- proportion of runtime spent in feature extraction versus pair matching.

### Optional cheap screening

A cheap similarity or structural filter may skip obviously unrelated pairs only after its true-partner recall and true-group connectivity are measured. The filter must have generous recall headroom.

### Optional retrieval path

Add global embeddings and top-`K`/threshold candidate retrieval only when all-pairs is shown to threaten the runtime budget. Retrieval similarity may be a weak pair feature, but it is never sufficient match proof.

If approximate search is introduced, measure it against exact retrieval. Candidate generation must be independent of insertion order and must deduplicate unordered pairs.

## 3. Pair evidence

Every evaluated pair produces a versioned record. Preserve raw features so thresholds and grouping policies can be rerun without repeating image matching.

Recommended evidence:

- tentative match count;
- mutual-match and ratio-test counts;
- robust inlier count and inlier ratio;
- symmetric reprojection/transfer error;
- inlier coverage in both images, including grid or convex-hull coverage;
- estimated overlap area;
- rotation, scale, translation, shear, and projective distortion;
- transform-model type and stability;
- post-warp gradient/edge residual or correlation;
- exposure difference and clipping fractions;
- aspect-ratio/resolution compatibility;
- optional weak global similarity;
- reasons for failure or insufficient evidence.

### Transform hierarchy

Start with the lowest-complexity plausible model:

1. similarity or partial affine;
2. full affine if justified;
3. homography as an ablation or fallback.

The same camera angle should normally require only modest transform freedom. Penalize implausible transforms rather than allowing a flexible homography to explain unrelated compositions.

Store transforms in a canonical pair direction and store inverses when valid. This enables composition and cycle-consistency checks during grouping.

## 4. Tri-state pair classification

Each pair receives a state plus confidence and reason codes.

### Positive

There is coherent evidence for the same viewpoint, such as:

- enough spatially distributed inliers;
- low transfer error;
- plausible transform;
- adequate overlap;
- compatible post-warp structure.

Use at least two positive strengths, for example `positive` and `strong_positive`, because seeding and attaching need not use the same threshold.

### Negative

There is affirmative evidence of incompatible viewpoints. Examples include:

- abundant informative features but no plausible coherent transform;
- a stable alignment hypothesis with strong structural contradiction;
- mutually incompatible geometry between well-exposed images;
- an implausible transform required to force agreement.

A lack of matches alone is not a negative.

### Unknown

The comparison is inconclusive, often because:

- one or both images are heavily clipped;
- too few useful features are visible;
- overlap is uncertain;
- the transform estimate is unstable.

Unknown edges neither merge groups by themselves nor veto an otherwise well-supported group.

### Pair calibration

Begin with an inspectable deterministic rule. After enough labeled evidence exists, compare it with a small calibrated model such as logistic regression or gradient-boosted trees. Train only on development data, use hard negatives, and select by full-group performance—not pair AUC alone.

## 5. Group formation

Use a completed pair-evidence table. Do not permanently union components as soon as one edge passes a threshold.

### Initial implementation

1. Seed provisional components from `strong_positive` edges.
2. Choose one or more high-information representatives per component.
3. Consider remaining images/components in deterministic evidence order.
4. Accept a merge when one of these is satisfied:
   - strong direct support to a representative;
   - at least two sufficiently independent positive links into the group;
   - a positive chain whose composed transforms are plausible and cycle-consistent.
5. Reject a merge when a strong negative exists between informative members or when transform composition creates a clear contradiction.
6. Treat unknown cross-pairs as neutral.
7. Re-score or revisit provisional merges before finalizing; use union-find only to label a final approved partition.

### Important bridge case

For strong `A-B`, strong `B-C`, and weak/absent `A-C`:

- allow `{A,B,C}` when `A-C` is unknown and the `A->B->C` transform composition is consistent;
- reject or split when `A-C` contains strong contradictory evidence;
- do not accept a borderline `B-C` as the sole bridge without representative, independent, or transform-consistency support.

This handles legitimate dark–mid–bright chains without allowing arbitrary transitive merges.

### Group-size and exposure priors

Group sizes such as 1, 3, 5, and 7+ and monotonic exposure sequences may be weak tie-breakers. They are never hard constraints: repeated passes, missing brackets, and unusual group sizes are possible.

### Grouping variants to compare

- connected components using only very strong positives;
- representative-based attachment;
- constrained agglomerative merging with positive/negative/unknown evidence;
- transform-consistent graph grouping.

The final choice is empirical.

## 6. Output validation

Before writing the CSV:

- ensure every discovered image appears in exactly one group;
- ensure no unknown or extra filenames appear;
- ensure basenames are case-preserved exactly;
- ensure groups are nonempty;
- ensure output is deterministic;
- log counts of inputs, groups, singletons, non-singletons, errors, and fallback decisions.

If validation fails, fail loudly during development. In the submission path, use a tested deterministic recovery—typically singleton placement for unassigned images—rather than silently dropping files.

## 7. Caching and artifacts

Use layered, content-addressed caches:

```text
preprocessed views and image statistics
  -> local/global features
  -> candidate-pair list
  -> raw pair evidence and transforms
  -> calibrated pair states
  -> grouping result
```

Each cache key must include the source image fingerprint, code/schema version, and relevant config subset. Changing grouping thresholds must not invalidate local features or raw pair evidence. Changing feature extraction must invalidate downstream evidence.

Do not store large caches in the final image. Development caches belong under a gitignored artifact directory. Runtime may use bounded temporary storage without relying on persistence across submissions.

## 8. Runtime and packaging

- One offline Python process/CLI inside one `linux/amd64` image.
- No web server, queue, database, or service mesh.
- Start with OpenCV/NumPy and classical features.
- Add PyTorch or another model runtime only when an accepted learned component requires it.
- Benchmark sequential versus bounded parallel execution. Prevent nested BLAS/OpenCV/PyTorch oversubscription.
- Record wall time, CPU time where practical, peak RSS, image count, pair count, and cache hit rates.
- Leave substantial headroom below 60 minutes; a locally marginal configuration is not submission-safe.
- Add a deterministic runtime safety path for unexpectedly large inputs. Select an execution tier from the input count and benchmarked cost curves before expensive matching begins: use all-pairs when safe, otherwise switch to the validated cheap-screening or bounded-retrieval path. Reserve time for final grouping, validation, and CSV writing; process candidates in deterministic priority order; skip optional expensive work before the soft runtime limit; and conservatively leave unresolved images as singletons. This is a safety valve, not a substitute for benchmarking the chosen container comfortably below the hard limit.
- Package every model asset with source, version, license, checksum, and startup validation.

## 9. Explicitly deferred ideas

The following are not part of the initial baseline:

- DINOv2/NetVLAD retrieval;
- DISK/SuperPoint/LightGlue;
- approximate nearest-neighbor indexes;
- large neural pair classifiers;
- OpenAI or other hosted vision judging;
- full-corpus training.

They remain valid hypotheses, but only after a measured failure mode justifies them.
