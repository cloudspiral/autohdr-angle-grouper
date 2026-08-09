# AutoHDR results and decision record

This is the living human-readable summary. The machine-readable run registry and per-run artifacts remain the detailed source of truth.

## Current status

- **Phase:** Phase 5 — finalist frozen; human publication/upload handoff pending
- **Current champion:** Screened dual-view CLAHE submission entrypoint (single recommended finalist)
- **Frozen config:** `configs/phase4/b2-screened-dual-clahe.json`, config hash `8edd0d656ac4…`; protected evaluation source `532cc1b`
- **Protected holdout touched:** Yes, exactly once; 109/110 exact groups, zero merge damage
- **Submission published:** No
- **Last updated:** 2026-08-09

## Current recommendation

Retain the screened dual-view config as the single recommended submission
candidate while retaining B1, single-view Phase 2, and full-pair Phase 3 as
controls. The screen uses B1 structural distance only to nominate the union of
12 nearest neighbors above 64 images; every group edge still requires the
frozen dual-view RootSIFT/RANSAC evidence. It reproduces all six full-dual
development partitions byte-for-byte: 161/162 exact groups, zero merge damage,
995/998 same-group candidate recall, and connectivity for 161/162 groups. At
100 images it retains at most 17.394% of pairs; at 366 images it retains 4.785%.
The exact cache-free entrypoint completes the 366-image native probe twice in
about 119 seconds with at most 637 MB RSS and identical output. Its one protected
400-image run scores 109/110 exact groups with zero merges in 161.57 seconds and
574 MB RSS; candidate recall/connectivity are complete and the lone error is a
conservative split. Required Python and pinned `linux/amd64` container CI pass
for the Phase 5 source under read-only/no-network execution. Representative x86
machine-profile timing, photoshoot-level split independence, public image
publication, and leaderboard evidence remain unavailable.

## Source and rule audit

| Item | Observed result | Source/date | Consequence |
|---|---|---|---|
| Live contract checked | Upstream `main` remains `e2b08ffebbd0281e24567c1d5fc0e2111b1a6d85`; exact-group denominator verified | Live starter, 2026-08-08 | Lock scorer tests to official examples |
| Runtime limit | Conflicting: PDF/README say 60 min; submission guide says 30/45 min | Live starter + supplied PDF, 2026-08-08 | Engineer to 30 min `cpu-large` / 45 min `cpu-xlarge` until clarified |
| 266K vs 276K corpus discrepancy | Live starter advertises 276K; supplied PDF says 266K | PDF vs live starter, 2026-08-08 | Record as documentation drift; do not download full corpus |
| Labeled 500/5K/10K packages available | Sample and advertised 5K downloaded and verified; advertised 5K actually contains 2,126 images; 10K intentionally not downloaded | Live starter/S3 + local audits, 2026-08-08 | Record actual inventory rather than advertised names |
| Package overlap/nesting | All 366 sample images and all 69 sample groups are byte-for-byte nested in the medium package with unchanged label relations | Cross-audit, 2026-08-08 | Exclude every sample group from larger-package checks; scores are not independent otherwise |
| Shoot/property metadata | Sample manifest has only `group_id,filename` | Sample audit | No leakage-safe photoshoot/property split can be claimed |
| Pretrained-model rules | Unknown | Rules audit | Gates learned-model experiments |

## Dataset audit

### Package inventory

| Package | Images | Groups | Size | Fingerprint | Overlaps | Notes |
|---|---:|---:|---:|---|---|---|
| Advertised 500 sample | 366 | 69 | 1,497,174,241-byte ZIP | `144796b2fbc2…` | Fully nested in medium | Valid archive; 366 JPEGs; no corrupt, missing, extra, duplicate-basename, or exact-duplicate files |
| Advertised 5K medium | 2,126 | 538 | 9,175,266,809-byte ZIP | `b06b3319f878…` | Contains all 366 sample images exactly | Valid archive and CRCs; no corrupt, missing, extra, duplicate-basename, exact-duplicate, or cross-group perceptual-collision files |
| 10K | Not downloaded | — | Advertised ~42 GB | — | Unknown | Out of Phase 0 scope |

### Data characteristics

- Group-size distribution: 69 groups; sizes 1–25, including 26 triplets and 18 groups of five.
- Singleton fraction: 5/69 reference groups (7.25%).
- Image formats/dimensions: 366 JPEGs across 38 dimensions, from 2794×1865 through 9504×6336. The training archive is not resized to the advertised 1024 px maximum.
- Corrupt/duplicate images: zero corrupt, missing, extra, duplicate-basename, or exact-duplicate files. All 38 coarse perceptual-hash collision sets stay within one reference group; none crosses reference groups.
- Post-audit integrity: the local audit artifact records all 366 image SHA-256 values, and scored runs re-hash the package before evaluation to reject any changed image bytes.
- Exposure/clipping distribution: median image luminance median 104.5; individual dark/bright clipped fractions reach 0.951/0.937, confirming extreme brackets.
- Verified evaluation unit: unavailable. The manifest has no photoshoot/property/source-sequence field.
- Split limitation: all 366 images are one provisional smoke unit. Every filename begins with its group ID; names and paths are forbidden model inputs.
- Medium-package drift: the advertised 5K archive contains 2,126 JPEGs in 538 groups, spans 126 dimensions, and exposes only `group_id,filename`; its 142 perceptual collision sets stay within reference groups.
- Medium overlap: 366 shared filenames have identical SHA-256 values, all 366 sample images have a perceptual-hash match, and all 66,795 shared-image label relations agree. The sample is a strict subset, not independent evidence.

### Frozen splits

| Split ID | Unit | Source package | Count | Seed/fingerprint | Purpose |
|---|---|---|---:|---|---|
| sample-smoke-v1 | Reference-group-only fallback; all rows in one provisional batch | Advertised 500 sample | 366 images / 69 groups | Dataset `144796b2fbc2…`; split `a11febf2c049…` | Harness validation only |
| sample-scale-051-v1 | Nested whole-reference-group subset | Advertised 500 sample | 51 images / 11 groups | Split `5b2f0844e58e…` | Runtime curve only |
| sample-scale-102-v1 | Nested whole-reference-group subset | Advertised 500 sample | 102 images / 20 groups | Split `6749c5088095…` | Runtime curve only |
| sample-scale-203-v1 | Nested whole-reference-group subset | Advertised 500 sample | 203 images / 36 groups | Split `2d57a4f2c105…` | Runtime curve only |
| medium-exclusive-100-v1 | Reference-group-only fallback; all sample group IDs excluded | Advertised 5K medium | 100 images / 24 groups | Dataset `b06b3319f878…`; split `b71a717e8fad…` | Fixed Phase 1 generalization check only |
| medium-dev-a/b/c-v1 | Reference-group-only fallback; sample and reserved groups excluded | Advertised 5K medium | 300 images / 76 distinct groups across three 100-image folds | Splits `f7194b1ce20e…`, `88f9dfad6992…`, `e568d3f37aa4…` | Phase 2 configuration selection only |
| medium-phase3-dev-a/b/c-v1 | Reference-group-only fallback; all 169 prior sample, reserved, and Phase 2 development groups excluded | Advertised 5K medium | 300 images / 86 distinct groups across three 100-image folds | Splits `ff309ac0285b…`, `87386062b168…`, `b8ebb028ac6c…` | Fresh Phase 3 architecture selection only |
| medium-final-holdout-v1 | Reference-group-only fallback; all 255 previously used groups excluded | Advertised 5K medium | 400 images / 110 groups | Dataset `b06b3319f878…`; split `d54349e11053…` | One-time protected validation; scored once from `532cc1b` |

## Baselines

| Run | System | Split | Exact score | Non-singleton exact | Merge damage | Split groups | Runtime | Peak RSS | Status |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| B0 | Singleton contract baseline | sample-smoke-v1 | 5/69 = 0.0725 | 0/64 | 0 | 64 | 0.006 s | 70.1 MB | Passed from clean commit; smoke only |
| B1 | Direct structural baseline, threshold 0.16 | sample-smoke-v1 | 60/69 = 0.8696 | 55/64 = 0.8594 | 0 | 9 | 45.03 s | 386.9 MB | Passed from clean commit; retained structural control |
| B2 | RootSIFT + partial-affine RANSAC + tri-state support grouping | sample-smoke-v1 | 67/69 = 0.9710 | 62/64 = 0.9688 | 0 | 2 | 202.60 s cold / 7.39 s cached | 456.1 MB cold | Passed from clean commit; untuned smoke only |
| B1-medium | Direct structural baseline, threshold 0.16 | medium-exclusive-100-v1 | 22/24 = 0.9167 | 21/23 = 0.9130 | 0 | 2 | 13.08 s | 306.8 MB | Passed from clean commit; fixed sample-exclusive slice |
| B2-medium | Fixed classical geometry baseline | medium-exclusive-100-v1 | 22/24 = 0.9167 | 21/23 = 0.9130 | 0 | 2 | 26.71 s cold / 0.94 s cached | 375.4 MB cold | Passed from clean commit; byte-identical to B1 on this slice |
| B2-Phase2-dev | Frozen Phase 2 classical config | medium-dev-a/b/c-v1 | 76/76 = 1.0000 | 71/71 = 1.0000 | 0 | 0 | 2.67 s fully cached confirmation; cold block timings recorded separately | 105.1 MB process peak during cached confirmation | Selected on development folds only; reference-group fallback |
| B2-Phase2-reserved | Frozen Phase 2 classical config | medium-exclusive-100-v1 | 22/24 = 0.9167 | 21/23 = 0.9130 | 0 | 2 | 23.43 s cold | 364.4 MB cold | First and only Phase 2 post-selection run; byte-identical to Phase 1 B2 |
| B2-Phase3-baseline | Frozen Phase 2 single-view config | medium-phase3-dev-a/b/c-v1 | 84/86 = 0.9767 | 74/76 = 0.9737 | 0 | 2 | 64.25 s cold comparison | 554.7 MB max | Fresh-fold control; no selection changes |
| B2-Phase3-dual | Baseline + percentile-CLAHE decision fusion | medium-phase3-dev-a/b/c-v1 | 85/86 = 0.9884 | 75/76 = 0.9868 | 0 | 1 | 128.69 s cold | 551.2 MB max | Selected after passing fresh and prior-development gates |
| B2-Phase3-regression | Selected dual-view config | medium-dev-a/b/c-v1 | 76/76 = 1.0000 | 71/71 = 1.0000 | 0 | 0 | 121.92 s cold | 467.1 MB max | Required no-regression gate; not fresh selection evidence |
| B2-Phase4-screened | Structural top-12 candidates + selected dual views | All six Phase 2/3 development folds | 161/162 = 0.9938 | 146/147 = 0.9932 | 0 | 1 | 250.09 s cold across six sequential folds | 439.6 MB max fresh / 425.5 MB max prior | Byte-identical to full dual on all six folds; packaging selection |
| B2-Phase4-scale | Exact cache-free `solution.py` entrypoint | Nested sample resource probes | Not used for accuracy selection | Not used | Not scored | Not scored | 12.02 / 38.65 / 74.76 / 119.22 s at 51/102/203/366 images | 637.1 MB max | Repeated 366 hash-identical; native arm64 resource evidence only |
| B2-Phase5-holdout | Frozen screened dual entrypoint | medium-final-holdout-v1 | 109/110 = 0.9909 | 99/100 = 0.9900 | 0 | 1 | 161.57 s | 574.0 MB | One and only protected run from clean commit `532cc1b`; no post-result tuning |

## Champion summary

| Field | Value |
|---|---|
| Run ID | Screened fresh `5db86b6b01`, `f04205bf73`, `d3403b0413`; screened prior `0af7adca29`, `060f0f0529`, `0e255e5288`; protected `20260809T053342Z-b2-screened-dual-clahe-b4da2aeebf`; Phase 4 CI `31296540040` |
| Git commit | Screen implementation `c2ac7e5`; two-worker scale source `3847c128059f29319c82eb58e24551c26fa89e6d`; protected evaluation source `532cc1b81211871198b0ec9c00ed8b986ed4b102` |
| Config hash | `8edd0d656ac43ca210dbecb8fd1c88d8ea12ad92bd91c0600e7b663e12fe709e` |
| Architecture | B1 structural top-12 candidate union above 64 images; complete baseline-CLAHE and percentile-stretched RootSIFT/RANSAC evidence on candidates; negative-veto fusion; support-aware grouping |
| Mean fresh exact score | 0.9872 across three folds; micro 85/86 = 0.9884 |
| Worst-fold exact score | 0.9615 fresh; 1.0000 on the prior-development regression folds |
| Non-singleton exact score | Fresh 75/76 = 0.9868; prior development 71/71 = 1.0000 |
| Merge damage | 0 across all six development/regression folds |
| Split groups | 1 fresh; 0 prior-development regression |
| Protected holdout | 109/110 exact, 99/100 non-singleton, 10/10 singleton; 0 merges and 1 split; candidate recall/connectivity 1.0 |
| Runtime / batch size | Exact cache-free entrypoint: 119.22 s maximum across two 366-image native arm64 runs; 3,196/66,795 candidates per view |
| Peak RSS | 637.1 MB maximum on repeated 366-image native runs |
| Why selected | Produces the full dual-view partition byte-for-byte on all six development folds, removes over 82% of expensive 100-image pairs, remains deterministic at 366 images, and passes the exact offline container contract without model assets |
| Known risks | One development candidate disconnect and one protected geometry split; cheap structural screen remains quadratic; private batch sizes and representative x86 timing are unknown; reference-group-only split boundary; no leaderboard evidence |

## Experiment log

Add one row per meaningful sweep batch or architectural comparison. Do not add hundreds of individual config trials here; link to the machine-readable registry/report.

| Date | Hypothesis / sweep | Baseline | Candidate(s) | Development result | Resource result | Decision | Run/report |
|---|---|---|---|---|---|---|---|
| 2026-08-08 | Trustworthy Phase 0 harness and untuned full-sample smoke | B0 | B1 at existing 0.16 | B0 5/69; B1 60/69; no threshold sweep; both repeated from clean commit `b482089` | B1 45.03 s, 386.9 MB on 366-image batch | Retain B1 unchanged; diagnose splits and move calibration to larger audited data | Clean runs `4087578661`, `597087c3ee` |
| 2026-08-08 | Early B1 scale curve on nested whole-group smoke subsets | B1-51 | B1-102, B1-203, B1-366 | Accuracy is non-comparable across nested smoke subsets and was not used for selection | 51: 7.04 s / 1,275 pairs; 102: 15.27 s / 5,151; 203: 27.84 s / 20,503; 366 clean repeat: 45.03 s / 66,795 | Keep all-pairs B1 as a measured baseline; private batch size and x86 timing remain unknown | Runs `da43343699`, `8a48a89669`, `d0fb52d126`, `597087c3ee` |
| 2026-08-08 | Untuned classical geometry and raw-evidence cache | B1 | B2 fixed before scored sample runs | B2 67/69 versus B1 60/69; zero merge damage; two split groups; positive-pair precision 1.0 and same-group-pair recall 0.8328 | Clean cold: 202.60 s / 456.1 MB / 66,795 pair misses; clean cached: 7.39 s / 273.1 MB / 66,795 pair hits; prediction SHA-256 identical | Promote B2 as provisional smoke leader without tuning; validate on a bounded larger-package slice | Runs `147d53d248`, `3a73776202`; prediction `a19061188dfa…` |
| 2026-08-08 | Fixed generalization check after proving complete sample nesting | B1 | Untuned B2 on 100 images from 24 medium-only groups | Both 22/24 exact with zero merge damage and identical predictions; B2 positive-pair precision 1.0, same-group-pair recall 0.6453 | B1 13.08 s / 306.8 MB; B2 cold 26.71 s / 375.4 MB and cached 0.94 s / 121.7 MB for 4,950 pairs | Retain B2 provisionally because it improves sample and does not regress the exclusive slice; do not tune from two visually explained failures | Runs `f95378c584`, `8563c1d1c0`, `26ea0dbe05`; prediction `94a25cd5e053…` |
| 2026-08-08 | Phase 2 feature budget | Phase 1 B2 at 512 px / 320 features | 384/256 and 640/400 | All three 75/76 across three disjoint folds with zero merges | Cold aggregate 61.78 s at 384/256, 78.34 s baseline, 94.81 s dense | Select 384/256 for equivalent grouping with 21% lower measured runtime than baseline | `experiments/phase2/results-01-feature.json` |
| 2026-08-08 | Matching/RANSAC block with fair cache isolation | Ratio 0.78 / RANSAC 3 px | Ratio 0.74, ratio 0.82, and RANSAC 4 px | All four 75/76 with zero merges | Each candidate: 300 feature hits, 14,850 pair misses; RANSAC 4 measured 22.13 s versus 23.07 s baseline | Select RANSAC 4 by the fixed tie-break; treat the small timing difference conservatively | `experiments/phase2/results-02-match.json` |
| 2026-08-08 | Pair-state threshold block | Phase 1 state thresholds | Positive recall, low-count strong, conservative | Low-count strong reaches 76/76 with zero merges; all others remain 75/76 | Every candidate reuses 14,850 pair records with zero misses | Select six-inlier strong-positive evidence guarded by strict ratio, coverage, transfer, transform, and structural checks | `experiments/phase2/results-03-state.json` |
| 2026-08-08 | Grouping policy and nearby stability | Representative shortcut, two-edge support, negative veto | Distributed support, no veto, three-edge consensus; count and guard neighbors | All grouping policies 76/76; count 5/6 and ±0.05 guards 76/76; count 7 is 75/76; zero merges throughout | Fully cached runs 0.80–0.97 s per fold; timing differences are not material | Freeze balanced count 6 with three-edge distributed support and retained negative veto; document the integer boundary | `experiments/phase2/results-04-grouping.json`, `results-05-stability.json` |
| 2026-08-08 | One post-selection reserved-slice comparison | Phase 1 B2 | Frozen Phase 2 B2 | Both 22/24 with zero merges and byte-identical predictions | Phase 1 26.71 s / 375.4 MB; Phase 2 23.43 s / 364.4 MB, both cold | Promote Phase 2 provisionally as a development improvement with no reserved-slice regression; do not claim a holdout gain | Run `64e4032389`; `experiments/phase2/reserved-comparison.json` |
| 2026-08-08 | Fresh Phase 3 baseline on 300 images from 86 previously unseen groups | Frozen Phase 2 B2 | None | 84/86 exact, zero merges, two folds perfect and fold B at 24/26 | 64.25 s cold comparison; 300 feature and 14,850 pair misses | Rank the two fold-B splits and test only the dominant exposure-normalization failure | `experiments/phase3/results-00-frozen-baseline.json` |
| 2026-08-08 | Cycle 1: percentile stretch before CLAHE can expose structure in clipped brackets | Frozen Phase 2 B2 | Percentile-CLAHE single view | Fresh improves to 85/86 with zero merges, but prior development regresses from 76/76 to 75/76 | 64.90 s fresh cold, 1.010x baseline | Reject as a standalone champion; the two views hold complementary safe evidence | `results-01-percentile-clahe.json`, `results-02-phase2-regression.json` |
| 2026-08-08 | Cycle 2: fuse complete single-view decisions with a negative veto | Frozen Phase 2 B2 | Dual CLAHE views | Fresh 85/86 and prior development 76/76, zero merges throughout; cumulative 161/162 | 128.69 s fresh cold, 2.003x single view; 551.2 MB max | Accept as the Phase 3 evaluation champion; stop architecture search because the remaining adjacent-view label has no safe margin | `results-03-dual-fresh.json`, `results-04-dual-phase2-regression.json` |
| 2026-08-09 | Screen expensive pairs with the retained B1 structural descriptor | Full-pair Phase 3 dual view | Top-12 union above 64 images | Byte-identical partitions on all six folds: 161/162 exact, zero merges; 995/998 same-pair candidates and 161/162 group connectivity | 814–861 candidates per 100 images, at most 17.394% of all pairs; 250.09 s cold across six folds | Accept for packaging; the sole candidate disconnect is the already-split group 39901 | `experiments/phase4/candidate-screen-decision.json` |
| 2026-08-09 | Bound OpenCV workers on the smallest machine profile | Host default | Requested 1, 2, 4, 8 | All prediction hashes identical | 18.44 s at 1; 12.00/11.99/12.06 s at 2/4/8 on 51 images | Select 2 by the predeclared lower-thread tie rule | `experiments/phase4/thread-benchmark-decision.json` |
| 2026-08-09 | Exact cache-free submission scale and determinism | 51-image all-pairs probe | 102/203/366 screened probes | Accuracy intentionally not compared on nested resource subsets; repeated 366 partition hashes match | 12.02/38.65/74.76/119.22 s; 366 max 637.1 MB and 3,196/66,795 candidates | Accept native scale gate with 15.1x headroom under 30 minutes; retain x86 timing limitation | `experiments/phase4/native-scale-results.json` |
| 2026-08-09 | Exact native and read-only/no-network `linux/amd64` contract | Trivial Phase 0 smoke | Textured identical-pixel pair through promoted entrypoint | Native and container both place the two randomized names in one group | Python 18 s; container build/smoke 22 s | Accept Phase 4 packaging gate; no local daemon bypass or image publication | CI run `31296540040`, jobs `93202426775`, `93202426802` |
| 2026-08-09 | One-time protected validation after complete Phase 5 freeze | Frozen screened dual entrypoint | No comparison candidate permitted | 109/110 exact; 99/100 non-singleton; 10/10 singleton; zero merge damage; one split; candidate recall/connectivity 1.0 | 161.57 s / 574.0 MB / 3,515 of 79,800 candidates on locked native arm64 Python 3.11 | Accept the frozen finalist without tuning; proceed only with packaging, CI, and human handoff | `experiments/phase5/final-holdout-result.json` |
| 2026-08-09 | Pinned Phase 5 `linux/amd64` contract | Phase 4 mutable-base CI proof | Digest-pinned Python 3.11 base and exact runtime lock | Native and container smoke place the randomized identical-pixel pair in one group | Python job 16 s; container job 19 s; CI-local image 365,280,872 bytes | Accept packaging-only base pin; image ID is not a public registry digest | CI run `31297253738`, jobs `93204279645`, `93204279673` |

## Decision log

### D-001 — Classical, geometry-first baseline

- **Status:** Accepted as starting direction
- **Reason:** The task is viewpoint identity under exposure variation. Semantic similarity is insufficient proof, and a simple measurable baseline is needed before learned complexity.
- **Revisit when:** Classical pair evidence reaches a demonstrated accuracy ceiling or runtime requires candidate pruning.

### D-002 — All-pairs candidate evaluation first

- **Status:** Accepted provisionally
- **Reason:** Runtime input is expected to be one photoshoot; actual batch sizes and costs must be measured before retrieval is justified.
- **Revisit when:** Measured private-like batch sizes or profiling threaten the runtime budget.

### D-003 — Positive / negative / unknown pair states

- **Status:** Accepted
- **Reason:** Extreme exposure pairs can lack direct evidence without contradicting a shared viewpoint. Unknown must not be treated as negative.
- **Revisit when:** Development ablations show no group-level benefit.

### D-004 — Reuse the merged structural implementation as B1

- **Status:** Accepted
- **Hypothesis:** The existing deterministic descriptor is a useful measurable control and should not be discarded merely because the new plan was written greenfield.
- **Evidence:** On the complete public sample smoke batch, B1 scored 60/69 versus B0's 5/69, with zero merge-damaged reference groups and nine split groups.
- **Tradeoffs:** Connected-component chaining remains architecturally risky, and the sample cannot establish a robust threshold or generalization score.
- **Decision:** Preserve B1 and its 0.16 threshold; add B2 and tri-state grouping only as controlled comparisons.
- **Revisit when:** Larger audited development folds show B1 failure modes or a controlled candidate materially improves exact-group performance.
- **Related runs:** `20260809T024233Z-b0-singletons-4087578661`, `20260809T024238Z-b1-structural-597087c3ee`

### D-005 — Promote untuned B2 as the provisional smoke champion

- **Status:** Accepted provisionally
- **Hypothesis:** Exposure-normalized local geometry will recover B1 false splits without creating connected-component false merges.
- **Evidence:** B2 improves the complete sample from 60/69 to 67/69 exact groups, leaves zero merge-damaged reference groups, and classifies all 1,215 positive pair edges within their reference groups. On the fixed 100-image sample-exclusive medium slice, B2 ties B1 at 22/24 with an identical partition and no merges. Cold and cached predictions are byte-identical on both slices.
- **Tradeoffs:** The cold run is 4.5 times slower than B1, the sample is not a valid development fold, negative evidence remained unused because unrelated low-match pairs were correctly unknown, and both residual split labels span noticeable camera movement.
- **Decision:** Keep the fixed B2 config as the Phase 1 leader without threshold tuning. Preserve B1 and B0 as controls and use the larger-package slice as the next independent check.
- **Revisit when:** The larger slice shows false merges, substantially lower recall, or a runtime profile that requires candidate screening.
- **Related runs:** `20260809T030917Z-b2-classical-147d53d248`, `20260809T030749Z-b2-classical-3a73776202`

### D-006 — Freeze the balanced Phase 2 classical configuration

- **Status:** Accepted provisionally
- **Hypothesis:** A smaller feature budget, slightly wider RANSAC tolerance, strict low-count geometry, and distributed group support can recover a low-texture exposure frame without increasing merge damage.
- **Evidence:** The selected config reaches 76/76 exact groups over three disjoint development folds versus 75/76 for Phase 1 B2, with zero merge damage. Count 5, count 6, and both ±0.05 strong-guard neighbors reproduce 76/76; count 7 loses the recovered group. All grouping-policy candidates reproduce 76/76. The single frozen post-selection reserved run ties Phase 1 B2 at 22/24 with a byte-identical CSV and zero merges.
- **Tradeoffs:** The gain is one development group and depends on accepting exactly six inliers for its best attachment. Cached runtime differences among threshold/grouping variants are too small to interpret. Neither development nor reserved slices are photoshoot/property-disjoint, and the two Phase 1 reserved failures remain.
- **Decision:** Freeze `configs/phase2/b2-selected.json` with balanced count-6 guards, three-edge distributed support, and the negative veto. Prefer it over the automatically runtime-ranked loose-guard variant because grouping evidence is identical and the balanced thresholds are stricter. Preserve B0, B1, and Phase 1 B2 as controls.
- **Revisit when:** A valid photoshoot-level unit, protected holdout, representative x86 container benchmark, or new development failures contradict the provisional choice.
- **Related runs:** Development `433eecd590`, stability report `phase2-stability-v1`, reserved `20260809T040908Z-b2-phase2-selected-64e4032389`

### D-007 — Select complementary preprocessing with a negative veto

- **Status:** Accepted provisionally for evaluation; packaging pending
- **Hypothesis:** Baseline CLAHE and percentile-stretched CLAHE expose complementary safe local geometry, so decision-level fusion can retain both recovered attachments without relaxing any geometric threshold.
- **Evidence:** The percentile view alone improves fresh development from 84/86 to 85/86 but regresses prior development from 76/76 to 75/76. Negative-veto fusion scores 85/86 fresh and restores 76/76 prior development, with zero merge damage on all six folds. It passes the predeclared worst-fold and 2.25x runtime gates at 0.9615 and 2.003x respectively.
- **Tradeoffs:** Two complete views approximately double feature and pair work. The remaining fresh group 39901 spans visibly shifted compositions, and both the B1 structural descriptor and direct gradient comparisons lack a safe margin from wrong-group images.
- **Decision:** Freeze `configs/phase3/b2-dual-clahe.json` as the Phase 3 evaluation champion. Stop the researcher loop instead of adding a risky adjacent-view fallback; preserve all single-view systems as controls and defer runtime architecture to Phase 4.
- **Revisit when:** Candidate screening, representative x86 container benchmarks, a valid photoshoot-level unit, or protected-holdout evidence changes the accuracy/runtime balance.
- **Related runs:** Fresh `440af1ffb8`, `ab66a7d842`, `3dec020a50`; prior-development regression `1fba9018d8`, `ca5607d71e`, `468b936eab`; `experiments/phase3/cycle-02-decision.json`

### D-008 — Use structural top-12 screening above 64 images

- **Status:** Accepted for the submission entrypoint
- **Hypothesis:** The retained B1 descriptor can nominate a generous local-feature candidate graph without becoming grouping evidence, preserving every recovery of the full dual-view champion while avoiding quadratic expensive matching.
- **Evidence:** Across six 100-image development folds, the screen evaluates 814–861/4,950 pairs, retains 995/998 same-group pairs and connectivity for 161/162 groups, and produces byte-identical full-dual predictions: 161/162 exact groups with zero merge damage. The only disconnected label is group 39901, already split by the full champion.
- **Tradeoffs:** Exact cheap structural similarity remains quadratic and adds enough overhead that 100-image cold runtime is approximately unchanged. Candidate recall is measured on reference-group-only folds, not a valid photoshoot unit.
- **Decision:** Use all pairs through 64 images, then the union of each image's 12 nearest structural neighbors with every numeric boundary tie retained. Keep RootSIFT/RANSAC, pair states, fusion, and grouping unchanged.
- **Revisit when:** Representative private batch sizes, x86 profiles, or protected evidence expose a recovered-group candidate miss or insufficient runtime headroom.
- **Related runs:** `experiments/phase4/results-01-screened-phase3.json`, `results-02-screened-phase2.json`, `candidate-screen-decision.json`

### D-009 — Promote the cache-free two-worker runtime

- **Status:** Accepted for Phase 4 packaging
- **Hypothesis:** In-memory features plus bounded OpenCV workers will preserve deterministic predictions and fit comfortably below the stricter runtime and memory limits without writable caches.
- **Evidence:** Requested 2/4/8 workers form a native wall-time plateau with identical hashes; two is selected by the lower-thread tie rule. The exact two-worker entrypoint completes 366 images twice in 119.22/119.11 seconds, peaks at 637.1 MB, and emits the same hash. CI run `31296540040` passes native tests and the read-only/no-network `linux/amd64` container with a nontrivial grouped pair.
- **Tradeoffs:** The macOS OpenCV getter reports the 14-host-CPU default after every requested value, and native arm64 timing cannot stand in for representative x86 machine profiles. The CI fixture proves behavior, not scale.
- **Decision:** Enforce two requested OpenCV workers, keep BLAS/OpenMP layers at one, run without persistent caches, package the frozen config, and promote `solution.group_images` to the screened dual-view implementation.
- **Revisit when:** Actual 8-vCPU/16-GB or 16-vCPU/32-GB container benchmarks contradict native headroom.
- **Related runs:** `experiments/phase4/thread-benchmark-decision.json`, `native-scale-results.json`, `selection.json`; CI jobs `93202426775`, `93202426802`

### D-010 — Freeze one finalist after the protected holdout

- **Status:** Accepted for human publication review
- **Hypothesis:** The screened dual-view entrypoint selected entirely on development evidence will retain its high exact-group rate and zero-merge profile on 400 previously unused images without requiring a second finalist.
- **Evidence:** The fail-closed command ran once from clean commit `532cc1b81211871198b0ec9c00ed8b986ed4b102` with matching config and split hashes. It scored 109/110 exact groups, including 99/100 non-singletons and 10/10 singletons, with zero merge damage and one 4+1 split. Screening retained every same-group pair and connected all 110 reference groups. The cache-free locked Python 3.11 run took 161.57 seconds and 574.0 MB RSS for 400 images.
- **Tradeoffs:** The source manifest still cannot establish photoshoot/property independence, representative x86 full-batch timing is unavailable, and the holdout must not become another tuning fold. A post-result Dockerfile-only exception pins the already-resolved official Python 3.11 Linux/AMD64 manifest digest; solution code, config, split, and Python dependencies remain unchanged.
- **Decision:** Advance candidate A as the single finalist. Do not run candidate B on the holdout and do not adjust geometry or grouping thresholds. Prepare deterministic submission artifacts and wait for human Docker Hub/Codabench action.
- **Revisit when:** Only a clear container contract defect, organizer rule change, or materially different future dataset justifies new work; never reuse this holdout for selection.
- **Related runs:** `experiments/phase5/freeze.json`, `final-holdout-result.json`, `selection.json`

### Decision template

#### D-XXX — Title

- **Status:** Proposed / Accepted / Rejected / Reverted
- **Hypothesis:**
- **Evidence:**
- **Tradeoffs:**
- **Decision:**
- **Revisit when:**
- **Related runs:**

## Failure taxonomy

Rank by the number of reference groups damaged, not merely the number of pair errors.

| Rank | Failure category | Groups damaged | Typical evidence | Current hypothesis | Next test |
|---:|---|---:|---|---|---|
| 1 | Protected insufficient-geometry split | 1 protected group | The five-image group is split 4+1 even though candidate screening preserves full true-group connectivity; the isolated frame has only unknown direct edges | The conservative positive-evidence policy avoids merging without sufficient geometry | Document only; never tune or rerun the protected split |
| 2 | Adjacent-view / composition-shift false split | 1 fresh Phase 3 group | Group 39901 remains 1+3 under both single and dual views; its bright oblique kitchen frame differs from three darker frontal views | Existing structural and direct-gradient descriptors place wrong-group images as close as the coarse same-label view, so a fallback would risk false merges | Stop the Phase 3 architecture loop; collect genuinely independent cases before designing an adjacent-view model |
| 3 | Extreme-exposure false split | 0 selected fresh groups; 1 under the frozen baseline | Group 18127's dark frame has only seven keypoints and no baseline mutual matches; percentile-CLAHE safely restores the exact group | Complementary normalization can expose enough geometry without globally replacing the baseline view | Preserve dual-view negative-veto fusion and verify its runtime path during packaging |
| 4 | Low-texture exposure attachment boundary | 0 selected prior-development groups; 1 under percentile-only or count 7 | Group 18608 needs one six-inlier baseline edge; percentile-only preprocessing or a count-7 boundary splits it | Neither preprocessing view dominates globally; strict decision fusion retains the safe baseline attachment | Preserve both views and the frozen count-6 policy |
| 5 | Previously observed reserved adjacent-view/extreme-exposure splits | 2 Phase 1 reserved groups, not reevaluated in Phase 3 | Groups 11393 and 11479 remain the one-time Phase 1/2 evidence | Reusing the reserved slice during architecture selection would leak it into the loop | Keep the historical record only; do not infer Phase 3 behavior without a future predeclared validation step |

Suggested categories:

- extreme-exposure false split;
- adjacent-view false merge;
- low-texture room;
- reflective/window-heavy scene;
- large crop or modest camera drift;
- repeated bracket pass;
- flexible-transform false positive;
- candidate-retrieval miss;
- corrupt/decode issue;
- grouping bridge/chaining error.

## Error-gallery index

| Gallery | Split/run | Description | Path |
|---|---|---|---|
| False merges | sample-smoke-v1 / B2 `147d53d248` | Zero merge-damaged reference groups; all 1,215 positive pair decisions stay within one reference group | Run metrics and pair-diagnostics artifacts |
| False splits | sample-smoke-v1 / B2 `147d53d248` | Two rendered contact sheets: aerial group 22994 splits 1+1; interior group 40615 splits 10+2 | `artifacts/cold-b2/runs/144796b2fbc2/ab0151c223f7/20260809T030917Z-b2-classical-147d53d248/gallery/` |
| Determinism | sample-smoke-v1 / cold and cached B2 | Cold and cached full-sample predictions are byte-identical | Predictions SHA-256 `a19061188dfae4f3a2d1579e0fc48b626f6dc877528d60eee2f896b4c17ae3be` |
| Unknown-edge chains | sample-smoke-v1 / B2 | 244 same-group and 65,336 different-group pairs are unknown; missing evidence remains neutral and positive support recovers 67/69 exact groups | Pair diagnostics artifact |
| Medium false splits | medium-exclusive-100-v1 / B2 `8563c1d1c0` | Two rendered sheets: 15-image group 11393 splits by three visible compositions; five-image group 11479 isolates one nearly white frame | `artifacts/runs/b06b3319f878/ab0151c223f7/20260809T033129Z-b2-classical-8563c1d1c0/gallery/` |
| Medium determinism | medium-exclusive-100-v1 / B1, cold B2, cached B2 | All three predictions are byte-identical | Predictions SHA-256 `94a25cd5e053cbc775ba61592c2de14a1f4957d70c930f550fd7546352c6ecec` |
| Runtime outliers | medium-exclusive-100-v1 | B2 is approximately twice B1 cold on 100 images; cache reduces B2 prediction work from 26.71 s to 0.94 s | Run resources artifacts |
| Phase 2 recovered development split | medium-dev-a-v1 / frozen thresholds | Group 18608 changes from 4+1 to one exact five-image group; count-7 neighbor restores the split | State and stability reports plus run `433eecd590` |
| Phase 2 reserved comparison | medium-exclusive-100-v1 / selected `64e4032389` | Same two split groups and byte-identical partition as Phase 1 B2; no new failure category or merge | `experiments/phase2/reserved-comparison.json`; prediction SHA-256 `94a25cd5e053…` |
| Phase 3 percentile recovery | medium-phase3-dev-b-v1 / Cycle 1 | Group 18127 changes from 2+1 to one exact three-image group; dual fusion preserves the recovery | `experiments/phase3/results-01-percentile-clahe.json`, `results-03-dual-fresh.json` |
| Phase 3 remaining split | medium-phase3-dev-b-v1 / dual `ab66a7d842` | Group 39901 remains 1+3; the isolated bright frame also shifts composition, and exploratory fallback distances lack wrong-group margin | `experiments/phase3/cycle-01-decision.json`, `cycle-02-decision.json` |
| Phase 3 regression repair | medium-dev-a-v1 / percentile-only then dual | Percentile-only re-splits group 18608; dual negative-veto fusion restores all 76 prior-development groups | `experiments/phase3/results-02-phase2-regression.json`, `results-04-dual-phase2-regression.json` |

## Reserved Phase 1 slice record

- **Freeze commit:** `6a2069354b3a1b128b6b481057dadea078f444ec`
- **Freeze config hash:** `855c7c577719163178b2c861ea1f36dbf012a32c7f46b81ecdddc0381c9f54d5`
- **Reserved split fingerprint:** `b71a717e8fadb260c1fa5b9a84b746d20633902c8bda4422deeeb046d653e62a`
- **First and only Phase 2 run ID:** `20260809T040908Z-b2-phase2-selected-64e4032389`
- **Exact score:** 22/24 = 0.9167
- **Non-singleton exact score:** 21/23 = 0.9130
- **Merge damage / split groups:** 0 / 2
- **Runtime / peak RSS:** 23.43 s / 364.4 MB, cold cache
- **Interpretation:** Byte-identical to Phase 1 B2. This supports no regression after selection; it is not a protected holdout and was not used for further tuning.

## Protected holdout record

Do not fill this section until the champion is frozen.

- **Freeze commit:**
- **Freeze config hash:**
- **Holdout split fingerprint:**
- **First and only planned holdout run ID:**
- **Exact score:**
- **Non-singleton exact score:**
- **Merge damage:**
- **Split groups:**
- **Runtime / peak RSS:**
- **Interpretation:**
- **Any post-holdout change:** None / describe and justify as contract-only

## Container validation

| Check | Result | Evidence |
|---|---|---|
| Builds for `linux/amd64` | Pass on exact Phase 4 source | [CI container job 93202426802](https://github.com/cloudspiral/autohdr-angle-grouper/actions/runs/31296540040/job/93202426802) builds the Dockerfile and passes in 22 seconds; local Docker access was policy-blocked and not bypassed |
| Runs with read-only input | Pass on two-image generated fixture | Bind input is `readonly`; container root uses `--read-only`; runtime uses in-memory features and no cache |
| Runs without network | Pass | Container uses `--network none`; no model assets, services, or runtime downloads exist |
| Writes valid CSV | Pass | Dependency-free validator requires the two case-preserved filenames exactly once with required headers |
| Native/container predictions match | Pass on nontrivial expected partition | [Python job 93202426775](https://github.com/cloudspiral/autohdr-angle-grouper/actions/runs/31296540040/job/93202426775) and the container job both group `same-a.png,same-b.png` together |
| 8 vCPU / 16 GB benchmark | Unverified | Native two-worker 366-image probe provides headroom evidence but is not an x86 machine-profile run |
| 16 vCPU / 32 GB benchmark | Unverified | No representative runner was available; do not infer timing from CI build/smoke duration |
| Runtime headroom | Native pass; x86 partial | Exact arm64 entrypoint: 119.22 s maximum and 637.1 MB maximum for 366 images, 3,196/66,795 candidates, hash-identical repeat. This is 15.1x below the 30-minute target, but representative x86 and private batch-size evidence remain unavailable |
| Packaged asset licenses/checksums | No model assets | Runtime image contains Python, NumPy, OpenCV, source package, and solution entrypoint only |

## Submission candidates

| Candidate | Image digest | Config hash | Local dev | Holdout | Runtime | Risk profile | Recommendation |
|---|---|---|---:|---:|---:|---|---|
| A | 365,280,872-byte CI image; stable timestamp-normalized ID pending; public registry digest unavailable until human push | `8edd0d656ac4…` | 161/162 across six fallback development/regression folds; byte-identical to full dual | 109/110, zero merges, one split | 161.57 s / 574.0 MB native arm64 at 400 images; Phase 5 pinned `linux/amd64` smoke passes twice | Screened dual-view classical; conservative split risk; unknown representative x86 timing | Single recommended finalist |
| B | Not built as a finalist | `855c7c577719…` | 160/162 on the same six folds | Not run; protected comparison intentionally forbidden | 64.25 s / 554.7 MB on fresh three-fold cold comparison | Simpler single view; one additional development split; lower runtime | Preserve as historical runtime control, not a finalist |

## Submission handoff

Complete this section before asking for human approval. Do not place credentials in the repository.

- **Recommended candidate:** A — screened dual-view CLAHE
- **Local image tag:** `YOUR_DOCKERHUB_NAMESPACE/autohdr-angle-grouper:phase5-532cc1b`
- **CI-local image ID:** Pending two matching builds after fixing `SOURCE_DATE_EPOCH`; not a public registry digest
- **Public tag to use after approval:** `YOUR_DOCKERHUB_NAMESPACE/autohdr-angle-grouper:phase5-532cc1b`
- **`submission.yaml` path:** `submission.yaml`
- **`submission.zip` path:** `submission.zip` (local, gitignored; deterministic SHA-256 `100d1058699d…` while placeholders remain)
- **Docker Hub push commands prepared:** Yes, `docs/SUBMISSION_HANDOFF.md`
- **Codabench upload checklist prepared:** Yes, `docs/SUBMISSION_HANDOFF.md`
- **Human approval received:** No
- **Public image pushed:** No
- **Codabench upload performed:** No

## Submission preparation checklist

- [ ] Recommended finalist public registry digest recorded after human push
- [ ] Public Docker repository name chosen by the user
- [x] `submission.yaml` validated with `cpu-large` and explicit namespace/email placeholders
- [x] `submission.zip` created and inspected; it contains only byte-identical `submission.yaml`
- [x] Exact Docker tag/push commands documented
- [x] Exact Codabench upload steps documented
- [ ] Human approval obtained before any external publication or submission

## Codabench submissions

| Date | Candidate | Submission ID | Private/public score | Notes | Next action |
|---|---|---|---:|---|---|
| — | — | — | — | — | — |

## Final recommendation

> Advance the screened dual-view entrypoint as the single Phase 5 finalist. It
> reproduces 161/162 development groups with zero merge damage and scores
> 109/110 on the one-time 400-image protected fallback holdout with zero merges.
> The exact native path remains deterministic and comfortably inside the strict
> runtime/memory targets, and the pinned Phase 5 `linux/amd64` contract CI is
> green. Do not retune or rerun the holdout. Await human Docker Hub/Codabench
> action; public image digest,
> representative x86 full-batch timing, photoshoot-level split independence,
> and leaderboard evidence remain unavailable.
