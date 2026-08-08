# Repository agent instructions

These instructions apply to all work in this repository, including unattended
OpenAI Symphony runs.

## Scope and safety

- Work only inside the provided repository workspace.
- Treat the GitHub issue as the scope boundary and avoid unrelated cleanup.
- Read `README.md`, `docs/REQUIREMENTS.md`, and relevant tests before editing.
- Never merge a pull request, force-push, change repository settings, create a
  release, publish a Docker image, submit to Codabench, or expose credentials.
- Do not download the multi-gigabyte AutoHDR datasets unless the issue explicitly
  requires it and the environment has enough space. Prefer generated fixtures for
  focused regression tests.
- Preserve user changes and avoid destructive Git operations.

## Implementation contract

- Keep `solution.py` importable and retain
  `group_images(image_paths: list[str]) -> list[list[str]]`.
- Preserve the default `/input/images/` to `/output/predictions.csv` container
  contract and the `filename,group_id` schema.
- Every input filename must appear exactly once. Do not use paths, filenames, or
  network access as grouping signals.
- Prefer deterministic, CPU-compatible algorithms that fit the 60-minute limit.
- Distinguish synthetic-fixture evidence from measured performance on labeled
  AutoHDR data. Never claim a leaderboard score without an actual scored run.

## Development workflow

- Use the repository `.venv` prepared by Symphony when it exists.
- Run `.venv/bin/ruff check .` and `.venv/bin/python -m pytest` as the minimum
  pre-commit gate.
- Run the most focused relevant test while iterating.
- Unattended Symphony workers must not invoke the local Docker daemon because it
  requires a host approval that the worker cannot answer. When dependencies, the
  Dockerfile, or runtime behavior change, use the required GitHub Actions
  `container` job as the `linux/amd64` build proof and record its result. Human-run
  local sessions may additionally run
  `docker build --platform linux/amd64 -t autohdr-angle-grouper:test .`.
- Review `git diff`, `git diff --check`, and `git status` before handoff.

## Git and handoff

- Stage only files that belong to the issue.
- Write comprehensive commit messages describing all material changes, rationale,
  and validation. Longer messages are preferred when they make the record clearer.
- Symphony must commit through `gakucho git-handoff commit "<message>"` and push
  through `gakucho git-handoff push`.
- Reopened issues with merged or closed prior pull requests must use the next
  `symphony/gh-<number>-attempt-<n>` branch rather than updating a closed branch.
- Open a pull request against `main` with `Closes #<issue-number>` in its body.
- Leave the issue and pull request in `human-review`; never merge your own work.
