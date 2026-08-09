# AutoHDR results and decision record

This is the living human-readable summary. The machine-readable run registry and per-run artifacts remain the detailed source of truth.

## Current status

- **Phase:** Phase 2 — controlled classical configuration optimization complete
- **Current champion:** B2 Phase 2 selected classical configuration (provisional; no protected holdout)
- **Frozen config:** `configs/phase2/b2-selected.json` at commit `6a2069354b3a1b128b6b481057dadea078f444ec`, config hash `855c7c577719…`
- **Protected holdout touched:** No
- **Submission published:** No
- **Last updated:** 2026-08-08

## Current recommendation

Retain B1 and the Phase 1 B2 config as controls, and promote the frozen Phase 2
B2 config as the provisional classical leader. Five bounded, predeclared blocks
used three disjoint 100-image medium-only development folds that exclude both
the nested sample and reserved Phase 1 slice. The selected config improves the
Phase 1 B2 development result from 75/76 to 76/76 exact groups with zero merge
damage, mainly by accepting a six-inlier edge whose geometry remains strict.
Count 5, count 6, and both nearby geometric-guard variants preserve 76/76 with
zero merges; count 7 loses the recovered group, so the integer boundary remains
a documented sensitivity. The single post-selection reserved-slice comparison
tied Phase 1 B2 at 22/24, produced a byte-identical partition, and retained zero
merge damage while reducing cold native runtime from 26.71 to 23.43 seconds on
100 images. This is a no-regression generalization check, not protected-holdout,
leaderboard, photoshoot-level, or full-package evidence. The source manifest
still lacks a photoshoot/property boundary, filenames still expose group IDs,
and all-pairs execution over all 2,126 medium images remains out of scope.

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
| final-holdout-v1 | Pending | — | — | — | One-time final validation |

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

## Champion summary

| Field | Value |
|---|---|
| Run ID | Development confirmation `20260809T040534Z-b2-group-three-edge-consensus-433eecd590`; reserved run `20260809T040908Z-b2-phase2-selected-64e4032389` |
| Git commit | Frozen config commit `6a2069354b3a1b128b6b481057dadea078f444ec`; reserved run recorded `dirty_tree: false` |
| Config hash | `855c7c577719163178b2c861ea1f36dbf012a32c7f46b81ecdddc0381c9f54d5` |
| Architecture | CLAHE + RootSIFT + mutual ratio matches + partial-affine RANSAC + post-warp gradient correlation + tri-state support grouping |
| Mean dev exact score | 1.0000 across three folds |
| Worst-fold exact score | 1.0000 |
| Non-singleton exact score | Development 71/71 = 1.0000; reserved 21/23 = 0.9130 |
| Merge damage | 0 across all three development folds and the reserved slice |
| Split groups | 0 development; 2 reserved |
| Runtime / batch size | 23.43 s cold / 100 images / 4,950 pairs on the reserved slice; 2.67 s fully cached across three development folds |
| Peak RSS | 364.4 MB cold on the selected reserved run |
| Why selected | Improves the Phase 1 B2 development result by one exact group without merge damage, remains exact under count-5 and nearby guard perturbations, uses the more conservative passing thresholds, and exactly preserves the Phase 1 reserved partition |
| Known risks | Reference-group folds do not prove photoshoot/property separation; the count-7 neighbor loses one group; filenames leak labels but are forbidden inputs; two reserved adjacent-view/extreme-exposure labels remain split; all-pairs is not viable for the complete medium package; x86 Phase 2 runtime, protected holdout, and leaderboard evidence remain unavailable |

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
| 1 | Adjacent-view / composition-shift false split | 1 reserved group | Medium-only group 11393 remains three predicted components matching three visibly different compositions in both Phase 1 and frozen Phase 2 | Conservative same-view geometry correctly avoids unrelated merges but cannot recover a coarse reference label spanning neighboring camera positions | Treat as a later isolated architecture experiment; do not relax pair thresholds against the already-read reserved slice |
| 2 | Extreme-exposure false split | 1 reserved group | In medium-only group 11479, four images connect while the fifth nearly white frame remains isolated in both Phase 1 and frozen Phase 2 | The clipped frame has insufficient direct structure and no safe alternate chain under the frozen evidence | Test a new normalization or exposure-specific attachment architecture only on fresh development data |
| 3 | Low-texture exposure attachment boundary | 0 selected development groups; 1 group at count 7 | Dev group 18608 needs one six-inlier edge with 0.75 inlier ratio, 0.125 coverage, 0.46 px error, and 0.44 structural correlation | Strict multi-signal geometry can safely use a small absolute match count, but the recovery sits at an explicit integer boundary | Preserve the frozen count-6 policy and collect new independent low-texture cases before changing it |

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
| Builds for `linux/amd64` | Local pass plus GitHub Actions pass | Local image ID `sha256:51f24d5f0c5d224b68040aad1e2ac1991904bf809734d86310354f650cdd1333`, 130,729,877 bytes, reports `amd64 linux`; [CI container job 93187979812](https://github.com/cloudspiral/autohdr-angle-grouper/actions/runs/31290986687/job/93187979812) passed in 16 seconds |
| Runs with read-only input | Pass on one-image generated smoke fixture | Bind input mounted `readonly`; container root used `--read-only` |
| Runs without network | Pass on smoke fixture | Container run used `--network none` |
| Writes valid CSV | Pass | Dependency-free validator confirmed one filename exactly once with required headers |
| Native/container predictions match | Pass on smoke fixture | Both CSVs SHA-256 `bbc7fc14db616169382d9f163b443e36f94eaaea27ee5ac7a112798267af239a` |
| 8 vCPU / 16 GB benchmark | Pending | — |
| 16 vCPU / 32 GB benchmark | Pending | — |
| Runtime headroom | Partial only | Frozen Phase 2 native cold run: 23.43 s / 364.4 MB for 100 images / 4,950 pairs, versus Phase 1 B2 at 26.71 s / 375.4 MB. Phase 1 required 202.60 s for 366 / 66,795. The actual 2,126-image medium package would require 2,258,875 all-pairs comparisons and is intentionally not attempted; candidate screening is required before package-scale execution, while private batch size and x86 Phase 2 runtime remain unknown |
| Packaged asset licenses/checksums | No model assets | Runtime image contains Python, NumPy, OpenCV, source package, and solution entrypoint only |

## Submission candidates

| Candidate | Image digest | Config hash | Local dev | Holdout | Runtime | Risk profile | Recommendation |
|---|---|---|---:|---:|---:|---|---|
| A | Pending Phase 2 CI image | `855c7c577719…` | 76/76 across three fallback folds | Reserved slice 22/24; no protected holdout | 23.43 s / 364.4 MB native cold per 100 images | Conservative classical; six-inlier boundary; all-pairs scaling | Provisional leader; do not publish or submit yet |
| B | — | — | — | — | — | Higher-recall grouping | — |
| C | — | — | — | — | — | Learned/retrieval variant | — |

## Submission handoff

Complete this section before asking for human approval. Do not place credentials in the repository.

- **Recommended candidate:**
- **Local image tag:**
- **Local image digest:**
- **Public tag to use after approval:**
- **`submission.yaml` path:**
- **`submission.zip` path:**
- **Docker Hub push commands prepared:** Yes / No
- **Codabench upload checklist prepared:** Yes / No
- **Human approval received:** No
- **Public image pushed:** No
- **Codabench upload performed:** No

## Submission preparation checklist

- [ ] Recommended finalist image tag and immutable digest recorded
- [ ] Public Docker repository name chosen by the user
- [ ] `submission.yaml` validated with the selected machine type and registered email placeholder/value
- [ ] `submission.zip` created and inspected
- [ ] Exact Docker tag/push commands documented
- [ ] Exact Codabench upload steps documented
- [ ] Human approval obtained before any external publication or submission

## Codabench submissions

| Date | Candidate | Submission ID | Private/public score | Notes | Next action |
|---|---|---|---:|---|---|
| — | — | — | — | — | — |

## Final recommendation

> Retain the frozen Phase 2 classical config as the provisional candidate because
> it improves development exact groups from 75/76 to 76/76 without merge damage,
> is stable across the bounded guard neighborhood, and exactly preserves the Phase
> 1 reserved partition. Do not publish or submit it yet: the count-7 sensitivity,
> reference-group-only split boundary, absent protected holdout, unknown x86 runtime,
> and all-pairs package-scale limit remain unresolved.
