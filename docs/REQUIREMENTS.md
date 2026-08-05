# AutoHDR image-grouping requirements

This is an implementation-oriented summary of the two-page brief
`project_1778728143185.pdf` (SHA-256
`28b4f79a8e4673257480944fd614545d08824b864ff712f4b57fcf174e3efd0e`).
The original PDF remains authoritative; it was inspected at full-page resolution
and its companion document passed the PDF-to-Markdown structural validator.

The current public [AutoHDR starter
repository](https://github.com/AutoHDRHackathon/autohdr-challenge-starter) is the
online operational reference. If it conflicts with the brief, verify the live
competition rules before submitting.

## Runtime and output contract

| ID | Requirement | Source |
| --- | --- | --- |
| REQ-001 | Group images taken from the same camera angle, including HDR exposures that belong together. | PDF p. 1 |
| REQ-002 | Accept randomized JPEG filenames with images resized to a maximum of 1024 px. | PDF p. 1 |
| REQ-003 | Read test images from the read-only `/input/images/` mount. | PDF p. 1 |
| REQ-004 | Write predictions to `/output/predictions.csv`. | PDF p. 1 |
| REQ-005 | Use the CSV columns `filename,group_id`. | PDF p. 1 |
| REQ-006 | Include every input image exactly once, using filenames without paths. | PDF p. 1 |
| REQ-007 | Assign the same string or numeric `group_id` to images in one group. | PDF p. 1 |
| REQ-008 | Expose `group_images(image_paths: list[str]) -> list[list[str]]` in `solution.py`. | PDF p. 1 |
| REQ-009 | Build for `linux/amd64` on Apple Silicon. | PDF p. 1 |
| REQ-010 | Run without internet access, within 60 minutes, and print progress to stdout. | PDF p. 2 |

## Evaluation contract

The score is `exact_matches / total_groups`. A group earns credit only when its
set of filenames exactly equals one reference group. There is no partial credit,
so both over-merging and over-splitting can erase otherwise-correct groups.
[PDF p. 2]

Group sizes can include singletons as well as 3, 5, or 7+ exposure brackets.
Filename UUIDs carry no grouping signal. [PDF p. 2]

## Publication requirements

The brief says the final Docker image must be public on Docker Hub and submitted
through Codabench using a zipped `submission.yaml`. It also states that entrants
must be US-based and may submit at most three times per day. These are human-owned
competition actions and are outside Symphony's unattended permissions. [PDF p. 2]

## Acceptance checklist for repository changes

- [ ] Tests prove every input filename is emitted exactly once.
- [ ] Tests cover exposure variants of the same view and visibly different views.
- [ ] The algorithm does not depend on filenames, EXIF metadata, network access,
      or writable input files.
- [ ] `ruff check .` and `python -m pytest` pass.
- [ ] Runtime or dependency changes preserve the `linux/amd64` Docker build.
- [ ] Performance claims are backed by a named dataset and evaluation command.
- [ ] Known false-merge and false-split risks are documented.

## Known ambiguity

The brief does not define a geometric or perceptual tolerance for “same camera
angle.” Thresholds therefore require validation against labeled training data;
synthetic tests establish mechanics but cannot prove leaderboard quality.
