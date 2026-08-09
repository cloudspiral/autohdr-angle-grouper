# AutoHDR system architecture master plan

> Historical planning document. The reconciled, eval-driven handoff under
> `autohdr_codex_plan/` supersedes this monolithic draft. It is retained for
> provenance and should not override the current contract, experiment plan, or
> recorded results.

This is the single source of truth for the planned AutoHDR grouping system. It records
architecture principles, provisional stack choices, empirical gates, and unresolved
evidence without treating the current implementation as a constraint.

## Problem and submission contract

Partition an unordered photoshoot into groups representing the same underlying camera
viewpoint. A group may span extreme exposure changes, modest capture drift, and repeated
bracket passes. Different compositions or materially different camera positions must
remain separate. Every image must appear in exactly one group.

- Input is one photoshoot mounted read-only at `/input/images/`; the brief describes
  randomized JPEG filenames and a maximum image dimension of 1024 px.
- Preserve `group_images(image_paths: list[str]) -> list[list[str]]`.
- Write `/output/predictions.csv` with `filename,group_id`; use filenames without paths
  and include every input exactly once. Only `/output` is writable at runtime.
- Run offline on CPU within 60 minutes, print progress, and package for `linux/amd64`.
- Do not use paths, filenames, EXIF metadata, or network access as grouping signals.
- Scoring is exact matched reference groups divided by total reference groups; partial
  overlaps receive no credit.
- The final image is published publicly and submitted through Codabench by a human; no
  unattended agent performs publication or submission.

## Locked decisions

- Use a geometry-first hybrid approach. Semantic similarity alone is not proof that two
  images share a viewpoint.
- Treat candidate retrieval as an optional, high-recall acceleration step, never as the
  authoritative match decision. Missing a true partner before geometry is worse than
  admitting extra candidates; small batches may use all-pairs verification.
- Make local geometric consistency the primary match evidence, supplemented by
  exposure-normalized appearance and other calibrated signals.
- Run the submitted solution completely offline; external APIs cannot be runtime
  dependencies.
- Near the end, benchmark OpenAI vision as a development-only judge on a balanced set of
  matching and difficult non-matching pairs. Use it for additional testing or error
  analysis, not final grouping.

## Unresolved evidence and decisions before implementation

All component and stack defaults remain provisional pending these checks.

### Blocking evidence gaps

- Obtain a complete official labeled package before real evaluation. The repository has
  only synthetic fixtures and a small, incomplete local inspection cache.
- Obtain organizer-provided photoshoot/property/source-sequence metadata or a predefined
  leakage-safe split. The promised manifest maps filenames to groups only: a group-disjoint
  split cannot rule out same-shoot or same-property leakage and cannot support held-out
  generalization claims.
- Clarify whether the large S3 corpus has authoritative labels, whether it contains 266K
  or 276K images, and whether it is approved for training and evaluation.
- Confirm current terms for pretrained models, external training data, and offline model
  training before relying on them.

### Empirical selections after the gaps close

Select the global and local models, normalization, retrieval `K` and overflow threshold,
ANN recall, descriptor matching and geometry, pair calibration, anti-chaining controls,
and runtime/memory/footprint tradeoffs only on complete data with verified licenses.

Maintain separate evidence tiers: contract/mechanics tests, synthetic behavioral tests,
official labeled validation, and an untouched final holdout. Never make accuracy or
generalization claims from synthetic fixtures alone.

## End-to-end processing flow

```text
decode, orient, exposure-normalize, and cache every image's retrieval and local features
  -> build one index over the complete global-vector set
  -> select top K plus threshold overflow and deduplicate directed selections
  -> match cached descriptors and verify one coherent transform per candidate
  -> store one calibrated confidence and its evidence per pair in a sparse graph
  -> run anti-chaining grouping on the completed graph
  -> validate the exact partition and write the CSV
```

The primary retrieval signal is a separate global embedding from exposure-normalized
images. An aggregate derived from the already-computed local descriptors is optional: use
the union of both candidate sets only when a held-out ablation shows that the aggregate
materially rescues true pairs or group connectivity missed by global retrieval, subject
to runtime and memory. Otherwise remove it. Raw-image variants remain experiments unless
they materially improve held-out candidate recall. Raw versus normalized is an input-view
choice, not a third kind of vector.

For modest batches, exact all-pairs global similarity may replace the index; small batches
may skip retrieval and geometrically verify all unordered pairs. For large batches, never
query an incrementally built index before all images are represented. Candidate pairs may
be processed in any order, including highest retrieval similarity first, but order must
not affect the result. Retrieval similarity ranks candidates and is not match evidence.

Each query always selects its configured top `K`, ordered by the global-vector metric
(normally cosine similarity after L2 normalization or equivalent distance). When the
index supports range queries, also select every additional neighbor at or above a
generous similarity threshold. The threshold never removes top-`K` candidates: top `K`
is the recall floor, while overflow protects dense groups with more than `K` plausible
partners. Include a pair when either endpoint selects the other and deduplicate unordered
pairs. If an index only exposes top `K`, retrieve enough neighbors to reproduce overflow
or use an exact or compatible evaluation alternative. Approximate-neighbor recall must be
measured against exact retrieval on representative validation data.

## Pair evidence and grouping

Each candidate pair receives one deciding confidence from detailed correspondence and
geometry: inlier count and ratio, reprojection error, spatial coverage, transform
plausibility, and other calibrated evidence. This score is distinct from retrieval rank.

Store every evaluated candidate as an undirected edge in an in-memory sparse scored graph,
with confidence, evidence, and decision status. Retrieval rank is diagnostic only. The
completed adjacency lists or edge table are the grouping source of truth, and no final
groups exist merely because pair evaluation has finished. Apply pair thresholds, then
make reversible, support-aware anti-chaining decisions over the completed graph. Do not
incrementally union accepted edges; union-find may label final components only after
group edges are approved.

Bridge case: strong `A-B`, borderline `B-C`, and no support for `A-C` must not
automatically produce `{A, B, C}`.

### Tunable pair and grouping controls

- Pair-confidence calibration: how geometric evidence becomes one edge score.
- Pair rejection threshold and the higher strong-edge eligibility threshold.
- Borderline-edge policy; a borderline edge cannot be the sole bridge.
- Minimum independent support into a group, by link count and/or combined strength.
- Representative-selection strategy and representative-support threshold.
- Group-consistency aggregation rule, including required support strength and spread.
- Bridge-acceptance rule defining the extra evidence needed to join two components.

The pair score controls individual edge decisions. Bridge safety is a separate group-level
decision over multiple edge scores and graph structure. Tune both layers on held-out
photoshoots using exact-group accuracy, false merges, false splits, runtime, and memory;
do not select them only by intuition.

### Complexity discipline

Grouping operates on sparse candidate edges using adjacency lookups, cached group
summaries, and bounded support checks. It must never rerun image comparisons or perform
new all-pairs checks inside proposed groups. Scale follows the sparse edge count rather
than all possible image pairs.

## Runtime and model packaging

The recommended hybrid baseline plans for two distinct local model assets:

1. A compact global image encoder producing one retrieval vector per normalized image.
2. A local feature model producing landmarks and descriptors for geometric verification.

Their code, configuration, and fixed weights must ship inside the runtime container so
inference requires no network. Normalization, index construction and queries, geometric
verification, scored-graph grouping, and CSV export remain deterministic non-model code.
A later pair-score calibrator is optional and may be a small non-neural artifact rather
than a third neural model.

Exact architectures, sizes, licenses, CPU performance, and total packaged footprint
remain benchmark decisions. Weight files will often be large relative to project source,
but framework and computer-vision runtime dependencies may dominate the Docker image;
measure before making size claims. The challenge documentation specifies offline
execution, `linux/amd64`, CPU resources, and a 60-minute limit, but no Docker-image or
model-weight size limit. This repository currently specifies no weight-file storage or
versioning policy, so that remains an open packaging decision.

### Provisional runtime stack; benchmark-gated baseline choices

- Ship one self-contained `linux/amd64` Docker image running one offline Python CLI
  pipeline. Do not add a web server, queue, microservices, or database.
- Start with PyTorch inference. Treat ONNX export/runtime as a later optimization only if
  measurement shows a material CPU-runtime or packaged-footprint improvement.
- Use bounded, configurable CPU parallelism with long-lived workers and explicit PyTorch
  thread limits to prevent oversubscription. Benchmark against sequential execution and
  retain the simpler mode when it is faster.
- Keep active per-image features in memory and spill caches only when needed to the
  contract-permitted writable workspace (currently `/output`). Namespace temporary cache
  files, clean them before completion, and leave the required prediction output intact.
- Require a versioned manifest for every packaged model asset: exact name, version,
  source, license, cryptographic checksum, expected size, and build/startup validation.
  Missing or mismatched assets must fail clearly; never download weights at runtime.

## Candidate components to benchmark; not locked decisions

### Learned candidates

- **Global retrieval:** DINOv2 ViT-S/14 as a compact general embedding baseline; NetVLAD
  or another place-recognition encoder as a retrieval-specific baseline.
- **Local features:** DISK and SuperPoint for landmarks and descriptors. Verify the exact
  code and pretrained-weight licenses before selection; SuperPoint is not assumed clear.
- **Optional local matcher:** LightGlue only as a later accuracy-versus-CPU experiment;
  it adds a learned component beyond the two-model baseline.
- **Optional pair calibration:** start with a deterministic weighted rule, then test an
  offline-trained logistic regression or similarly lightweight non-neural artifact.

### Deterministic and classical candidates

- **Decode/orientation:** Pillow or OpenCV with EXIF orientation handling.
- **Normalization:** fixed working resolution plus mild, color-preserving luminance
  percentile scaling; test luminance CLAHE, and use stronger illumination normalization
  or Retinex only with held-out benefit. Raw inputs remain an evidence-gated fallback.
- **Descriptor matching:** mutual nearest neighbors with ratio and distance filters.
- **Geometry:** robust RANSAC-family estimation comparing partial/full affine transforms
  and homography; score inliers, inlier ratio, reprojection error, coverage, and transform
  plausibility.
- **Retrieval engine:** exact cosine or inner-product search on L2-normalized vectors;
  test FAISS HNSW for large batches only after measuring recall against exact retrieval.
- **Grouping/output:** compact arrays, a scored edge table, sparse adjacency lists, sorted
  edge processing, and deterministic partition/CSV validation; no graph database.

Choose components only after held-out photoshoot-level evaluation of exact-group accuracy,
candidate recall and connectivity, false merges and splits, CPU runtime, memory, packaged
footprint, and licenses.

## Final validation and output

Only after anti-chaining returns proposed groups, validate exactly-once membership,
non-singleton internal-support rules, bridge-rule compliance, deterministic ordering, and
the required CSV schema and filenames. Final validation can reject an invalid partition,
but it cannot recover a true partner omitted by retrieval; candidate recall and true-group
connectivity therefore require separate held-out photoshoot-level validation.

## Evaluation sequence

1. Compare normalization and local-feature configurations on difficult positive pairs and
   hard negatives from similar rooms or nearby viewpoints.
2. Compare global retrieval alone with global plus aggregated-local retrieval, including
   candidate recall, group connectivity, runtime, and memory.
3. Evaluate conservative `K` budgets such as 50, 100, and 200 and independent overflow
   thresholds as experiments. Tune them on held-out photoshoots for candidate recall,
   true-group connectivity, geometric workload, runtime, and memory. Extra checks are
   acceptable; missed true partners are not recoverable downstream.
4. Tune geometric verification and pair-score calibration.
5. Compare grouping algorithms using the official exact-group metric, runtime, and memory.
6. Freeze the smallest fast configuration that preserves held-out grouping accuracy.

Split data by photoshoot or source sequence when the labels permit it. Never create random
pair-level train and validation splits that place images from one group in both sets. Keep
a final holdout untouched until configuration selection is complete.

## Main experimental knobs

- Exposure normalization and whether raw plus normalized views are both retained.
- Local feature model, landmark confidence threshold, and landmark budget.
- Local descriptor compression, if any; native descriptor length is fixed by the model.
- Global-vector size and whether aggregated-local retrieval earns its complexity.
- Top `K` recall floor and retrieval-similarity overflow threshold.
- Pair-score calibration, rejection threshold, and strong-edge threshold.
- Borderline, independent-support, representative, consistency, and bridge rules.

### Evidence-gated fallback experiments

- Add raw-image input variants only when normalization causes held-out retrieval misses.
- Increase `K` or threshold overflow when candidate recall lacks required headroom.
- Use all-pairs geometry wherever the measured batch-size regime makes it affordable.
- Add a separately trained retrieval encoder only when simpler retrieval cannot meet the
  recall target.

Each fallback requires held-out benefit and must not replace geometry as match proof.

## Open empirical decisions

1. Local feature model and whether it needs a classical-feature fallback.
2. Pair-score features, training, and calibration.
3. Retrieval-signal ablation and candidate budget.
4. Grouping algorithm and safeguards against transitive false merges.
5. Exact dataset split strategy after inspecting the available source metadata.
6. Runtime stack, parallelism, resource budget, and packaged model assets.
7. Confidence handling, fallbacks, diagnostics, and final submission experiments.
