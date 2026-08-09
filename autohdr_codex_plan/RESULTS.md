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
configuration optimization.

## Source and rule audit

| Item | Observed result | Source/date | Consequence |
|---|---|---|---|
| Live contract checked | Upstream `main` remains `e2b08ffebbd0281e24567c1d5fc0e2111b1a6d85`; exact-group denominator verified | Live starter, 2026-08-08 | Lock scorer tests to official examples |
| Runtime limit | Conflicting: PDF/README say 60 min; submission guide says 30/45 min | Live starter + supplied PDF, 2026-08-08 | Engineer to 30 min `cpu-large` / 45 min `cpu-xlarge` until clarified |
| 266K vs 276K corpus discrepancy | Live starter advertises 276K; supplied PDF says 266K | PDF vs live starter, 2026-08-08 | Record as documentation drift; do not download full corpus |
| Labeled 500/5K/10K packages available | Public URLs advertised; sample downloaded and verified; 5K/10K intentionally not downloaded | Live starter/S3, 2026-08-08 | Phase 0 remains sample-only |
| Package overlap/nesting | Unknown | Audit required | Prevents accidental leakage/duplicate weighting |
| Shoot/property metadata | Sample manifest has only `group_id,filename` | Sample audit | No leakage-safe photoshoot/property split can be claimed |
| Pretrained-model rules | Unknown | Rules audit | Gates learned-model experiments |

## Dataset audit

### Package inventory

| Package | Images | Groups | Size | Fingerprint | Overlaps | Notes |
|---|---:|---:|---:|---|---|---|
| Advertised 500 sample | 366 | 69 | 1,497,174,241-byte ZIP | `144796b2fbc2…` | Unknown | Valid archive; 366 JPEGs; no corrupt, missing, extra, duplicate-basename, or exact-duplicate files |
| 5K | Not downloaded | — | Advertised ~21 GB | — | Unknown | Out of Phase 0 scope |
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

### Frozen splits

| Split ID | Unit | Source package | Count | Seed/fingerprint | Purpose |
|---|---|---|---:|---|---|
| sample-smoke-v1 | Reference-group-only fallback; all rows in one provisional batch | Advertised 500 sample | 366 images / 69 groups | Dataset `144796b2fbc2…`; split `a11febf2c049…` | Harness validation only |
| sample-scale-051-v1 | Nested whole-reference-group subset | Advertised 500 sample | 51 images / 11 groups | Split `5b2f0844e58e…` | Runtime curve only |
| sample-scale-102-v1 | Nested whole-reference-group subset | Advertised 500 sample | 102 images / 20 groups | Split `6749c5088095…` | Runtime curve only |
| sample-scale-203-v1 | Nested whole-reference-group subset | Advertised 500 sample | 203 images / 36 groups | Split `2d57a4f2c105…` | Runtime curve only |
| dev-folds-v1 | Pending | — | — | — | Model/config selection |
| final-holdout-v1 | Pending | — | — | — | One-time final validation |

## Baselines

| Run | System | Split | Exact score | Non-singleton exact | Merge damage | Split groups | Runtime | Peak RSS | Status |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| B0 | Singleton contract baseline | sample-smoke-v1 | 5/69 = 0.0725 | 0/64 | 0 | 64 | 0.006 s | 70.1 MB | Passed from clean commit; smoke only |
| B1 | Direct structural baseline, threshold 0.16 | sample-smoke-v1 | 60/69 = 0.8696 | 55/64 = 0.8594 | 0 | 9 | 45.03 s | 386.9 MB | Passed from clean commit; retained structural control |
| B2 | RootSIFT + partial-affine RANSAC + tri-state support grouping | sample-smoke-v1 | 67/69 = 0.9710 | 62/64 = 0.9688 | 0 | 2 | 202.60 s cold / 7.39 s cached | 456.1 MB cold | Passed from clean commit; untuned smoke only |

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
| Known risks | Smoke package is not a photoshoot unit; filenames leak labels; true adjacent-view pairs can remain unknown; all-pairs is not viable for the complete 5K package without screening; no dev-fold, x86 B2 runtime, or leaderboard evidence |

## Experiment log

Add one row per meaningful sweep batch or architectural comparison. Do not add hundreds of individual config trials here; link to the machine-readable registry/report.

| Date | Hypothesis / sweep | Baseline | Candidate(s) | Development result | Resource result | Decision | Run/report |
|---|---|---|---|---|---|---|---|
| 2026-08-08 | Trustworthy Phase 0 harness and untuned full-sample smoke | B0 | B1 at existing 0.16 | B0 5/69; B1 60/69; no threshold sweep; both repeated from clean commit `b482089` | B1 45.03 s, 386.9 MB on 366-image batch | Retain B1 unchanged; diagnose splits and move calibration to larger audited data | Clean runs `4087578661`, `597087c3ee` |
| 2026-08-08 | Early B1 scale curve on nested whole-group smoke subsets | B1-51 | B1-102, B1-203, B1-366 | Accuracy is non-comparable across nested smoke subsets and was not used for selection | 51: 7.04 s / 1,275 pairs; 102: 15.27 s / 5,151; 203: 27.84 s / 20,503; 366 clean repeat: 45.03 s / 66,795 | Keep all-pairs B1 as a measured baseline; private batch size and x86 timing remain unknown | Runs `da43343699`, `8a48a89669`, `d0fb52d126`, `597087c3ee` |
| 2026-08-08 | Untuned classical geometry and raw-evidence cache | B1 | B2 fixed before scored sample runs | B2 67/69 versus B1 60/69; zero merge damage; two split groups; positive-pair precision 1.0 and same-group-pair recall 0.8328 | Clean cold: 202.60 s / 456.1 MB / 66,795 pair misses; clean cached: 7.39 s / 273.1 MB / 66,795 pair hits; prediction SHA-256 identical | Promote B2 as provisional smoke leader without tuning; validate on a bounded larger-package slice | Runs `147d53d248`, `3a73776202`; prediction `a19061188dfa…` |

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
- **Evidence:** B2 improves the complete sample from 60/69 to 67/69 exact groups, leaves zero merge-damaged reference groups, and classifies all 1,215 positive pair edges within their reference groups. Cold and cached predictions are byte-identical.
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
| 1 | Adjacent-view / composition-shift false split | 2 | B2 splits the two-image aerial group 22994 and separates the last two images from the 12-image interior group 40615; both galleries show substantial camera-position or composition change rather than exposure alone | Conservative partial-affine evidence correctly avoids unrelated merges but cannot bridge labels that span adjacent views without indirect support | Measure the same category on the larger package before testing transform chains, group-level structural support, or a broader attachment rule |

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
| Runtime outliers | — | — | — |

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
| Runtime headroom | Partial only | Clean-commit native B2 cold smoke batch: 202.60 s for 366 high-resolution images and 66,795 pairs; complete 5K all-pairs would be 12,497,500 pairs and is intentionally not attempted, while private batch size and x86 B2 runtime remain unknown |
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
