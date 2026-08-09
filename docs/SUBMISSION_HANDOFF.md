# Phase 5 human submission handoff

The recommended candidate is the frozen screened dual-view CLAHE entrypoint.
Its protected result is 109/110 exact groups with zero merge damage. The
evaluation source is commit `532cc1b81211871198b0ec9c00ed8b986ed4b102`;
post-holdout changes are limited to the documented base-image pin, submission
packaging, tests, and evidence.

Nothing has been pushed to Docker Hub or uploaded to Codabench. Those two
external actions remain human-only.

## One-time setup owned by the human submitter

1. Have a Docker Hub account and choose the namespace that will own a public
   `autohdr-angle-grouper` repository.
2. Run `docker login` interactively. Do not put a password or token in this
   repository, shell history, issue, or pull request.
3. Register at the AutoHDR bounty site, verify the required phone number, and
   note the exact email registered for Codabench.
4. Replace `YOUR_DOCKERHUB_NAMESPACE` and `YOUR_CODABENCH_EMAIL` in
   `submission.yaml` only on the trusted submission checkout.

GitHub authentication is already sufficient for repository work. No OpenAI,
model-hosting, cloud, database, or other application credentials are needed.

## Build and verify the exact candidate

Use the reviewed Phase 5 branch after its required CI is green. The public tag
is deliberately tied to the frozen evaluation revision:

```bash
export AUTOHDR_DOCKERHUB_NAMESPACE="replace-me"
export AUTOHDR_CODABENCH_EMAIL="replace-me@example.com"
export AUTOHDR_IMAGE="${AUTOHDR_DOCKERHUB_NAMESPACE}/autohdr-angle-grouper:phase5-532cc1b"

docker build --platform linux/amd64 --tag "${AUTOHDR_IMAGE}" .
docker image inspect "${AUTOHDR_IMAGE}" --format 'local_image_id={{.Id}} size_bytes={{.Size}}'
```

Run the exact offline contract against a local input directory before
publication. The output directory must already exist.

```bash
mkdir -p /private/tmp/autohdr-final-output
docker run --rm --platform linux/amd64 --network none --read-only \
  --mount type=bind,src="${PWD}/data/sample/images",dst=/input/images,readonly \
  --mount type=bind,src=/private/tmp/autohdr-final-output,dst=/output \
  "${AUTOHDR_IMAGE}"

head /private/tmp/autohdr-final-output/predictions.csv
```

The local Docker daemon was unavailable to Codex, so GitHub Actions is the
authoritative `linux/amd64`, read-only, no-network build/smoke proof. Record the
final Phase 5 CI job and image ID here after it completes:

- Phase 5 CI run: [`31297253738`](https://github.com/cloudspiral/autohdr-angle-grouper/actions/runs/31297253738)
- CI-local image ID: `sha256:99e2ff5febe1beb801ffc31588c0992902432d93d4f81586b2bff53d954dddaf`
- CI-local image size: `365,280,872` bytes

The CI-local ID is a content-addressed image configuration ID, not a Docker Hub
registry digest. The registry digest remains unavailable until the human push.

## Prepare the Codabench ZIP

After replacing the two placeholders, validate and build the deterministic ZIP:

```bash
python3 scripts/prepare_submission.py
unzip -l submission.zip
```

The validator permits placeholders during review, rejects missing/extra keys,
and packages exactly `submission.yaml`. The selected `cpu-large` profile has 8
vCPU and 16 GB RAM; the algorithm requests only two OpenCV workers and the
400-image native holdout used about 574 MB RSS in 162 seconds. Representative
x86 full-batch timing remains unmeasured, so keep the much stricter 30-minute
budget as the operational limit.

## Human publication and upload

Only after the reviewed candidate is explicitly approved:

```bash
docker push "${AUTOHDR_IMAGE}"
docker pull --platform linux/amd64 "${AUTOHDR_IMAGE}"
docker image inspect "${AUTOHDR_IMAGE}" --format '{{json .RepoDigests}}'
```

Then confirm the Docker Hub repository is public, re-run
`python3 scripts/prepare_submission.py`, and upload `submission.zip` on the
Codabench competition page. Record the immutable registry digest, submission ID,
score, and timestamp in `autohdr_codex_plan/RESULTS.md`; do not tune against the
leaderboard with adjacent threshold variants.
