# Evaluation split registry

Split definitions are test infrastructure. They are committed only after the
source package, available grouping unit, and package overlap have been audited.

Each split JSON must include:

- `schema_version`;
- a stable `split_id`;
- the source package name and dataset fingerprint;
- the split unit (`photoshoot`, `property`, or explicitly limited
  `reference_group` fallback);
- a deterministic seed and selection rule;
- whether the split is protected;
- limitations on leakage or representativeness.

Ordinary `autohdr_eval run` commands reject protected splits. The separate
`final-evaluate` command additionally requires a clean frozen commit, matching
config hash, and matching split fingerprint before it reveals a score.

No protected holdout is defined during the sample-only Phase 0 audit. The
official sample is for harness validation and smoke evidence, not final model
selection.

`sample-smoke-v1.json` selects the complete sample. The nested `sample-scale-*`
splits select whole reference groups in a fixed order to provide 51-, 102-, and
203-image points for the early B1 runtime curve. They are resource measurements,
not accuracy folds.

`medium-exclusive-100-v1.json` is the first larger-package generalization check.
The medium audit proved that every sample image is nested byte-for-byte, so this
split excludes all 69 sample group IDs before selecting 24 complete medium-only
reference groups totaling 100 images. It is fixed before B1/B2 scoring, but the
lack of photoshoot/property metadata still prevents treating it as a valid
tuning fold or protected holdout.
