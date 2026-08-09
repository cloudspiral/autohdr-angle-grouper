# AutoHDR Codex handoff

> **Status update (2026-08-09):** The plan is complete and the selected
> `linux/amd64` image is public at
> `cloudspires/autohdr-angle-grouper:phase5-532cc1b`, with registry digest
> `sha256:2a096d2b7d6195f749551e730341042617708bbe03ca878e35cd6ca241e8ad8b`.
> The original Codabench/bounty endpoints are unavailable; the remaining current
> delivery is the human-owned Gauntlet Loom/email handoff. The planning rules
> below are retained for provenance.

## Mission

Build, evaluate, and freeze an offline CPU solution that groups all images from one real-estate photoshoot by camera angle. Exposure-bracketed images of the same view belong together; materially different viewpoints do not.

The intended workflow is eval-driven:

```text
implement a simple measurable baseline
  -> run reproducible evaluations
  -> tune configuration against development folds
  -> diagnose the largest failure mode
  -> test one targeted architectural change
  -> accept or revert from evidence
  -> freeze the simplest robust winner
```

Proceed autonomously through this workflow. Ask for user input only when blocked by missing credentials, missing data access, ambiguous competition rules, or an action requiring explicit human approval.

## Read order

1. `CONTRACT.md` — immutable rules, project policies, and known documentation drift.
2. `ARCHITECTURE.md` — current technical direction and the baseline-to-advanced ladder.
3. `EXPERIMENT_PLAN.md` — evaluator, datasets, experiment loop, knobs, promotion rules, and stopping rules.
4. `RESULTS.md` — living summary of evidence and decisions. Update it throughout the work.
5. `sources/PROJECT_REQUIREMENTS.pdf` — original challenge brief.

These documents supersede the earlier monolithic architecture plan. They intentionally separate facts, current design, planned experiments, and observed results.

## First actions

1. Inspect the existing repository before changing it. Reuse working code where sensible, but do not preserve an architecture merely because it already exists.
2. Re-check the live official starter repository and record any contract changes or discrepancies in `RESULTS.md`.
3. Download only the labeled 500-image package first. Audit its manifest, directory structure, group-size distribution, and whether it contains shoot/property identifiers.
4. Implement and test:
   - the official exact-group evaluator;
   - partition/CSV contract validation;
   - deterministic run configuration and logging;
   - a singleton baseline;
   - one simple classical end-to-end geometry baseline.
5. After the harness is trustworthy, continue through the phases in `EXPERIMENT_PLAN.md` without waiting for approval after every routine experiment.

## Operating rules

- Treat the evaluator, dataset split definitions, and protected holdout as test infrastructure. Do not change them to make a solution look better.
- Normal evaluation and sweep commands must exclude the protected holdout. Access it only through a separate final-evaluation command that requires the frozen commit, config hash, and split fingerprint and writes an audit record before scoring.
- Configuration sweeps may run autonomously. Architectural code changes require a written hypothesis and a controlled comparison.
- Change one architectural idea at a time. Do not mix multiple new models, thresholds, and grouping rules in one uninterpretable experiment.
- Cache expensive intermediate results so pair scoring and grouping configurations can be retested cheaply.
- Prefer a broad, stable region of good configurations over one isolated best score.
- Prefer the simpler solution when accuracy is effectively tied.
- Do not use leaderboard submissions as the main optimization loop.
- Do not download the full roughly 1.1 TB corpus, publish a public Docker image, or submit to Codabench without explicit human approval.
- Codex should prepare the local final image, immutable digest, `submission.yaml`, `submission.zip`, and exact Docker Hub/Codabench handoff instructions. Missing credentials may remain placeholders, but pushing and uploading are human-gated.
- Do not add a runtime dependency on internet access or external APIs.

## Definition of done

The handoff is complete when the repository contains:

- a deterministic, validated end-to-end pipeline;
- reproducible development and holdout splits;
- a run registry and cached experiment artifacts;
- a frozen champion configuration selected from development evidence;
- one untouched holdout result;
- an exact `linux/amd64` container benchmark within the competition resource limits;
- a concise error gallery and final decision record in `RESULTS.md`;
- one to three materially distinct submission candidates, with a recommendation;
- a completed `submission.yaml`, `submission.zip`, and copy-paste human handoff checklist for Docker Hub publication and Codabench upload.
