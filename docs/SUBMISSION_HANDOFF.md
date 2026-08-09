# AutoHDR submission handoff

The Phase 5 finalist is frozen, publicly available, and technically ready for
review. The remaining delivery work is human-owned: record the requested Loom,
complete the Gauntlet submission form if applicable, and email the requested
links and artifact identity.

## Current delivery route

The original challenge PDF and upstream `SUBMISSION_GUIDE.md` describe a
Codabench upload tied to `bounty.autohdr.com`. Both referenced endpoints returned
HTTP 404 when rechecked on 2026-08-09. Gauntlet's updated partner instructions
instead request an under-five-minute Loom showing the code breakdown,
methodology, logic, and performance/results, delivered by email.

Do not claim a Codabench submission or private leaderboard score. The retained
`submission.yaml` and ZIP tooling are a legacy fallback if AutoHDR supplies a
replacement endpoint.

## Published artifact

- **GitHub:** <https://github.com/cloudspiral/autohdr-angle-grouper>
- **Docker Hub:** <https://hub.docker.com/r/cloudspires/autohdr-angle-grouper/tags>
- **Image reference:** `cloudspires/autohdr-angle-grouper:phase5-532cc1b`
- **Registry digest:** `sha256:2a096d2b7d6195f749551e730341042617708bbe03ca878e35cd6ca241e8ad8b`
- **Immutable reference:** `cloudspires/autohdr-angle-grouper@sha256:2a096d2b7d6195f749551e730341042617708bbe03ca878e35cd6ca241e8ad8b`
- **Runtime platform:** `linux/amd64`

The tag and top-level OCI digest were verified against the public registry on
2026-08-09. The registry contains the required `linux/amd64` image manifest plus
its build-attestation manifest.

## Pull and reproduce the exact artifact

Pulling by digest prevents a mutable tag from silently selecting different
content:

```bash
export AUTOHDR_IMAGE="cloudspires/autohdr-angle-grouper@sha256:2a096d2b7d6195f749551e730341042617708bbe03ca878e35cd6ca241e8ad8b"

docker pull --platform linux/amd64 "${AUTOHDR_IMAGE}"
mkdir -p /private/tmp/autohdr-final-output
docker run --rm \
  --platform linux/amd64 \
  --network none \
  --read-only \
  --mount type=bind,src="${PWD}/data/sample/images",dst=/input/images,readonly \
  --mount type=bind,src=/private/tmp/autohdr-final-output,dst=/output \
  "${AUTOHDR_IMAGE}"

head -n 5 /private/tmp/autohdr-final-output/predictions.csv
wc -l /private/tmp/autohdr-final-output/predictions.csv
```

The human-run publication smoke processed all 366 sample images, evaluated
3,196 of 66,795 possible pairs in each preprocessing view, predicted 71 groups,
and wrote 366 data rows plus the CSV header. The repository scorer reported
67/69 exact public-sample groups (97.10%), zero merge-damaged reference groups,
and two conservative splits.

## Evaluation and container evidence

- Six development/regression folds: 161/162 exact groups, zero merge damage;
  screened predictions are byte-identical to the full-pair dual-view champion.
- One predeclared 400-image public-data holdout: 109/110 exact groups (99.09%),
  zero merge damage, one conservative split, 161.57 seconds, and approximately
  574 MB peak RSS. No tuning occurred afterward.
- Native 366-image resource probe: approximately 119 seconds, at most 637 MB
  RSS, deterministic repeated prediction hash.
- Current local gate: Ruff passes and 64 tests pass.
- GitHub repository: public; the Phase 5 implementation merge at `4b74e5b` has
  green CI.
- Final pinned container proof: [workflow run 31297696268, attempt 1](https://github.com/cloudspiral/autohdr-angle-grouper/actions/runs/31297696268/job/93205364788)
  and [attempt 2](https://github.com/cloudspiral/autohdr-angle-grouper/actions/runs/31297696268/job/93205509762)
  both built and passed the read-only, no-network `linux/amd64` contract.

The holdout is reference-group-disjoint from prior folds but cannot be proven
photoshoot/property-disjoint because the organizer supplied no such metadata.
Representative private-data performance and a private leaderboard score remain
unmeasured.

## Human delivery checklist

- [x] Freeze the selected algorithm and configuration.
- [x] Pass Python tests and the `linux/amd64` container contract.
- [x] Build and run the exact image under no-network/read-only restrictions.
- [x] Publish the public Docker image and record its immutable digest.
- [x] Verify the public GitHub repository and current `main` CI.
- [ ] Record an under-five-minute Loom covering code, methodology, logic, and
      measured results.
- [ ] Set the Loom to “anyone with the link can view.”
- [ ] Submit or email the Loom together with the GitHub URL, Docker image
      reference, and immutable digest listed above.

No Railway service, web UI, cloud database, model host, API key, or additional
deployment is required. The Docker image is the deployed executable artifact.

## Legacy Codabench fallback

Only use this section if AutoHDR provides a working replacement competition URL
and explicitly requests the original ZIP format.

1. Keep the real email only in the local `submission.yaml`; never commit it.
2. Validate and rebuild the ignored archive:

   ```bash
   python3 scripts/prepare_submission.py
   unzip -l submission.zip
   ```

3. Confirm the validator reports no placeholders and that the ZIP contains only
   `submission.yaml`.
4. Upload the ZIP only to the organizer-provided endpoint, then record the
   submission ID, score, and timestamp without tuning against adjacent variants.

The original PDF, verified Markdown companion, and upstream submission guide are
preserved for provenance; they do not prove that the legacy endpoints are live.
