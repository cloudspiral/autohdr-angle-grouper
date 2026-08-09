# AutoHDR results and decision record

This is the living human-readable summary. The machine-readable run registry and per-run artifacts remain the detailed source of truth.

## Current status

- **Phase:** Phase 1 — classical geometry baseline and larger-package audit
- **Current champion:** B2 classical geometry baseline (provisional smoke leader only)
- **Frozen config:** None
- **Protected holdout touched:** No
- **Submission published:** No
- **Last updated:** 2026-08-08

## Current recommendation

Retain B1 unchanged as the structural control and promote the untuned B2
classical geometry baseline as the provisional smoke leader. On the complete
official sample, B2 scored 67/69 exact groups versus B1's 60/69 and B0's 5/69,
with no observed merge damage and two split groups. Its pair-level positive
precision was 1.0 on this package, while 244/1,459 true same-group pairs remained
unknown; this is conservative evidence, not a generalization guarantee. Do not
tune on this package: it has no photoshoot boundary, contains only 366 of the
advertised 500 images, and leaks every group ID in the public filename. The
clean, cold B2 run took 202.60 seconds and 456.1 MB peak RSS; a fully cached
repeat took 7.39 seconds and produced a byte-identical CSV. Complete the 5K
audit and bounded larger-package slice before development-fold selection or any
configuration optimization. On the fixed 100-image sample-exclusive medium
slice, B1 and B2 produced the same partition and tied at 22/24 exact groups with
zero merge damage. B2 therefore remains provisional because it improves the
sample without regressing this first independent content slice, not because it
won every comparison.

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
| dev-folds-v1 | Pending | — | — | — | Model/config selection |
| final-holdout-v1 | Pending | — | — | — | One-time final validation |

## Baselines

| Run | System | Split | Exact score | Non-singleton exact | Merge damage | Split groups | Runtime | Peak RSS | Status |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| B0 | Singleton contract baseline | sample-smoke-v1 | 5/69 = 0.0725 | 0/64 | 0 | 64 | 0.006 s | 70.1 MB | Passed from clean commit; smoke only |
| B1 | Direct structural baseline, threshold 0.16 | sample-smoke-v1 | 60/69 = 0.8696 | 55/64 = 0.8594 | 0 | 9 | 45.03 s | 386.9 MB | Passed from clean commit; retained structural control |
| B2 | RootSIFT + partial-affine RANSAC + tri-state support grouping | sample-smoke-v1 | 67/69 = 0.9710 | 62/64 = 0.9688 | 0 | 2 | 202.60 s cold / 7.39 s cached | 456.1 MB cold | Passed from clean commit; untuned smoke only |
| B1-medium | Direct structural baseline, threshold 0.16 | medium-exclusive-100-v1 | 22/24 = 0.9167 | 21/23 = 0.9130 | 0 | 2 | 13.08 s | 306.8 MB | Passed from clean commit; fixed sample-exclusive slice |
| B2-medium | Fixed classical geometry baseline | medium-exclusive-100-v1 | 22/24 = 0.9167 | 21/23 = 0.9130 | 0 | 2 | 26.71 s cold / 0.94 s cached | 375.4 MB cold | Passed from clean commit; byte-identical to B1 on this slice |

## Champion summary

| Field | Value |
|---|---|
| Run ID | `20260809T030917Z-b2-classical-147d53d248` |
| Git commit | `bd6da81791287eaef9ef433eac723320c03bd845` with `dirty_tree: false` recorded by the run harness |
| Config hash | `ab0151c223f715c7671c251c424f36aa90a5ab1b2ea5375de1d46e3f6aa0ca65` |
| Architecture | CLAHE + RootSIFT + mutual ratio matches + partial-affine RANSAC + post-warp gradient correlation + tri-state support grouping |
| Mean dev exact score | Not measured; sample smoke score 0.9710 |
| Worst-fold exact score | Not measured; no valid folds yet |
| Non-singleton exact score | Sample smoke 62/64 = 0.9688 |
| Merge damage | 0 sample reference groups |
| Split groups | 2 sample reference groups |
| Runtime / batch size | 202.60 s cold / 7.39 s cached / 366 high-resolution images / 66,795 candidate pairs on Apple Silicon host Python |
| Peak RSS | 456.1 MB cold |
| Why selected | Untuned geometry raises exact sample smoke score by 7 groups over B1 while retaining zero observed merge damage and 1.0 sample positive-pair precision |
| Known risks | Neither package exposes a photoshoot unit; filenames leak labels; true adjacent-view pairs can remain unknown; B2 only ties B1 on the first sample-exclusive slice; all-pairs is not viable for the complete medium package without screening; no dev-fold, x86 B2 runtime, or leaderboard evidence |

## Experiment log

Add one row per meaningful sweep batch or architectural comparison. Do not add hundreds of individual config trials here; link to the machine-readable registry/report.

| Date | Hypothesis / sweep | Baseline | Candidate(s) | Development result | Resource result | Decision | Run/report |
|---|---|---|---|---|---|---|---|
| 2026-08-08 | Trustworthy Phase 0 harness and untuned full-sample smoke | B0 | B1 at existing 0.16 | B0 5/69; B1 60/69; no threshold sweep; both repeated from clean commit `b482089` | B1 45.03 s, 386.9 MB on 366-image batch | Retain B1 unchanged; diagnose splits and move calibration to larger audited data | Clean runs `4087578661`, `597087c3ee` |
| 2026-08-08 | Early B1 scale curve on nested whole-group smoke subsets | B1-51 | B1-102, B1-203, B1-366 | Accuracy is non-comparable across nested smoke subsets and was not used for selection | 51: 7.04 s / 1,275 pairs; 102: 15.27 s / 5,151; 203: 27.84 s / 20,503; 366 clean repeat: 45.03 s / 66,795 | Keep all-pairs B1 as a measured baseline; private batch size and x86 timing remain unknown | Runs `da43343699`, `8a48a89669`, `d0fb52d126`, `597087c3ee` |
| 2026-08-08 | Untuned classical geometry and raw-evidence cache | B1 | B2 fixed before scored sample runs | B2 67/69 versus B1 60/69; zero merge damage; two split groups; positive-pair precision 1.0 and same-group-pair recall 0.8328 | Clean cold: 202.60 s / 456.1 MB / 66,795 pair misses; clean cached: 7.39 s / 273.1 MB / 66,795 pair hits; prediction SHA-256 identical | Promote B2 as provisional smoke leader without tuning; validate on a bounded larger-package slice | Runs `147d53d248`, `3a73776202`; prediction `a19061188dfa…` |
| 2026-08-08 | Fixed generalization check after proving complete sample nesting | B1 | Untuned B2 on 100 images from 24 medium-only groups | Both 22/24 exact with zero merge damage and identical predictions; B2 positive-pair precision 1.0, same-group-pair recall 0.6453 | B1 13.08 s / 306.8 MB; B2 cold 26.71 s / 375.4 MB and cached 0.94 s / 121.7 MB for 4,950 pairs | Retain B2 provisionally because it improves sample and does not regress the exclusive slice; do not tune from two visually explained failures | Runs `f95378c584`, `8563c1d1c0`, `26ea0dbe05`; prediction `94a25cd5e053…` |

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
| 1 | Adjacent-view / composition-shift false split | 3 | Sample groups 22994 and 40615 shift camera position; medium-only group 11393 contains three visually distinct neighboring compositions that B1 and B2 both split | Conservative pair evidence avoids unrelated merges but cannot bridge coarse labels spanning neighboring views without indirect group support | Test transform-chain or group-level structural support as a later isolated architecture change, not a threshold relaxation |
| 2 | Extreme-exposure false split | 1 | In medium-only group 11479, four images connect while the fifth is almost entirely clipped white; B1 and B2 both isolate it | The most clipped frame has insufficient direct structure and no alternate same-view chain under the fixed grouping evidence | Test a bounded exposure-normalization or representative-attachment ablation on development folds once valid folds exist |

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
| Runtime headroom | Partial only | Clean-commit native B2 cold runs: 26.71 s for 100 images / 4,950 pairs and 202.60 s for 366 / 66,795. The actual 2,126-image medium package would require 2,258,875 all-pairs comparisons and is intentionally not attempted; candidate screening is required before package-scale execution, while private batch size and x86 B2 runtime remain unknown |
| Packaged asset licenses/checksums | No model assets | Runtime image contains Python, NumPy, OpenCV, source package, and solution entrypoint only |

## Submission candidates

| Candidate | Image digest | Config hash | Local dev | Holdout | Runtime | Risk profile | Recommendation |
|---|---|---|---:|---:|---:|---|---|
| A | — | — | — | — | — | Conservative classical | — |
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

> Fill after freeze. State which candidate to submit, why it is preferred, and which unresolved risks remain.
