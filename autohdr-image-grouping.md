> This Markdown file is an agent-friendly companion to the original PDF. The PDF remains the authoritative source. Any conflict or ambiguity must be verified against the PDF.

## Source

- **PDF:** `autohdr-image-grouping.pdf`
- **SHA-256:** `28b4f79a8e4673257480944fd614545d08824b864ff712f4b57fcf174e3efd0e`
- **Physical pages:** 2
- **Extraction backend:** `pypdf 6.10.0`
- **Verification status:** Verified

# Task

<a id="req-001"></a>**REQ-001** - Given a folder of real-estate photos from photoshoots, identify which images were taken from the same camera angle and group the images that belong together. An angle may have multiple exposures (HDR brackets). [PDF p. 1]

## Input and output

<a id="req-002"></a>**REQ-002** - The input is a folder of JPEG images resized to a maximum of 1024 px and assigned randomized filenames. [PDF p. 1]

<a id="req-003"></a>**REQ-003** - The output must be a CSV file that groups images by camera angle. [PDF p. 1]

# How It Works

The participant builds a Docker container that reads the images and writes a predictions CSV. The organizers run the container against a private test set, score its output, and update the leaderboard. [PDF p. 1]

# Your Container's Contract

<a id="table-001"></a>**TABLE-001 - Container paths** [PDF p. 1]

| Direction | Path | Description |
| --- | --- | --- |
| Input | `/input/images/` | Test images, mounted read-only |
| Output | `/output/predictions.csv` | Grouping predictions |

<a id="req-004"></a>**REQ-004** - The container must read the test images from the read-only mount at `/input/images/`. [PDF p. 1]

<a id="req-005"></a>**REQ-005** - The container must write its grouping predictions to `/output/predictions.csv`. [PDF p. 1]

# `predictions.csv` Format

The PDF gives this example: [PDF p. 1]

```csv
filename,group_id
a7f3b2c1.jpg,0
d4e5f6a7.jpg,0
b8c9d0e1.jpg,1
f2a3b4c5.jpg,2
```

<a id="req-006"></a>**REQ-006** - The predictions CSV must use the columns `filename,group_id`. [PDF p. 1]

<a id="req-007"></a>**REQ-007** - Every input image must appear exactly once in the predictions CSV. [PDF p. 1]

<a id="req-008"></a>**REQ-008** - Images placed in the same group must share a `group_id`. [PDF p. 1]

<a id="req-009"></a>**REQ-009** - A `group_id` may be any string or number. [PDF p. 1]

<a id="req-010"></a>**REQ-010** - The CSV must use filenames only, without paths. [PDF p. 1]

# Quick Start

## 1. Get the Starter Kit

Clone the starter repository: [PDF p. 1]

```bash
git clone https://github.com/AutoHDRHackathon/autohdr-challenge-starter.git
```

The starter kit contains `solution.py`, `Dockerfile`, and `submission.yaml`. [PDF p. 1]

## 2. Implement Your Algorithm

<a id="req-011"></a>**REQ-011** - Implement the algorithm by editing `solution.py` and providing `group_images(image_paths: list[str]) -> list[list[str]]`; the returned nested lists group filenames that share a camera angle. [PDF p. 1]

The PDF provides this example implementation shape: [PDF p. 1]

```python
def group_images(image_paths: list[str]) -> list[list[str]]:
    return [
        ["a7f3b2c1.jpg", "d4e5f6a7.jpg"],    # same camera angle
        ["b8c9d0e1.jpg"],                    # different angle
        ["f2a3b4c5.jpg", "e6f7a8b9.jpg"],   # another angle
    ]
```

## 3. Build and Test Locally

The PDF gives these local build-and-run commands: [PDF p. 1]

```bash
docker build --platform linux/amd64 -t my-solution:v1 .
docker run -v /path/to/images:/input/images:ro -v /tmp/output:/output my-solution:v1
```

<a id="req-012"></a>**REQ-012** - Mac users must build with `--platform linux/amd64`; the PDF warns that the container will crash without it. [PDF p. 1]

## 4. Push to Docker Hub

The procedure continues across the page break: [PDF pp. 1-2]

```bash
docker login
docker tag my-solution:v1 yourusername/autohdr-solution:v1
docker push yourusername/autohdr-solution:v1
```

<a id="req-013"></a>**REQ-013** - Push the solution image to Docker Hub and make the Docker Hub repository public. [PDF p. 2]

## 5. Submit on Codabench

<a id="req-014"></a>**REQ-014** - Create `submission.yaml` using the starter-kit template, with the keys `docker_image`, `machine_type`, and `email`. [PDF p. 2]

The PDF gives this example: [PDF p. 2]

```yaml
docker_image: yourusername/autohdr-solution:v1
machine_type: cpu-xlarge
email: your-registered-email@example.com
```

<a id="req-015"></a>**REQ-015** - Set `machine_type` to either `cpu-large` (8 vCPU, 16 GB) or `cpu-xlarge` (16 vCPU, 32 GB). [PDF p. 2]

<a id="req-016"></a>**REQ-016** - Set `email` to the address used for registration at `bounty.autohdr.com`. [PDF p. 2]

<a id="req-017"></a>**REQ-017** - Package `submission.yaml` as `submission.zip`. [PDF p. 2]

```bash
zip submission.zip submission.yaml
```

<a id="req-018"></a>**REQ-018** - Upload `submission.zip` on the **My Submissions** tab. [PDF p. 2]

The PDF says execution can take about an hour and that the organizers will email the participant if something goes wrong. [PDF p. 2]

# Scoring

The score is calculated as: [PDF p. 2]

```text
score = exact_matches / total_groups
```

An exact match means that a predicted group contains exactly the same set of filenames as the labeled group. There is no partial credit. [PDF p. 2]

<a id="table-002"></a>**TABLE-002 - Scoring scenarios** [PDF p. 2]

| Scenario | Score |
| --- | ---: |
| All groups predicted perfectly | 1.0 |
| Baseline: each image alone | ~0.09 |
| All images in one group | 0.0 |

# Training Data

The full dataset contains 266K images. The PDF provides this unsigned-download command: [PDF p. 2]

```bash
aws s3 sync s3://grouping-dataset-solution/images/ ./images/ --no-sign-request
```

# Rules

<a id="req-019"></a>**REQ-019** - Contestants must be based in the United States. [PDF p. 2]

<a id="req-020"></a>**REQ-020** - The submitted container must run without internet access. [PDF p. 2]

<a id="req-021"></a>**REQ-021** - Each submission has a 60-minute time limit. [PDF p. 2]

The allowed machine types and their resources are defined once in [REQ-015](#req-015). [PDF p. 2]

<a id="req-022"></a>**REQ-022** - A contestant may submit at most three times per day. [PDF p. 2]

<a id="req-023"></a>**REQ-023** - The container must print progress to standard output; this progress appears in the submission logs. [PDF p. 2]

# Tips

The PDF offers the following guidance, not additional formal rules: [PDF p. 2]

- Images from the same angle are typically exposure brackets (dark, mid, and bright) of the same scene.
- Filenames are randomized UUIDs.
- Group sizes vary, including singles and groups of 3, 5, or 7+ brackets.
- Test locally before submitting to conserve the daily submission limit.

## Critical Requirement Indexes

### Mandatory Conditions

- [REQ-001](#req-001) - Group images taken from the same camera angle.
- [REQ-004](#req-004) - Read images from the read-only input mount.
- [REQ-005](#req-005) - Write predictions to the required output path.
- [REQ-006](#req-006) through [REQ-010](#req-010) - Follow the predictions CSV schema and row rules.
- [REQ-012](#req-012) - Mac users must target `linux/amd64`.
- [REQ-013](#req-013) - Publish the image in a public Docker Hub repository.
- [REQ-014](#req-014) through [REQ-018](#req-018) - Create, package, and upload the required Codabench submission.
- [REQ-019](#req-019) through [REQ-023](#req-023) - Follow the eligibility and execution rules.

### Automatic-Failure Conditions

None stated.

### Deadlines

None stated.

### Numeric Thresholds

- [REQ-002](#req-002) - Input images are resized to a maximum of 1024 px.
- [REQ-015](#req-015) - `cpu-large` provides 8 vCPU and 16 GB; `cpu-xlarge` provides 16 vCPU and 32 GB.
- [REQ-021](#req-021) - Each submission has a 60-minute time limit.
- [REQ-022](#req-022) - At most three submissions are allowed per day.

### Required Paths

- [REQ-004](#req-004) - `/input/images/`
- [REQ-005](#req-005) - `/output/predictions.csv`

### Deliverables

- [REQ-005](#req-005) - Runtime output: `/output/predictions.csv`.
- [REQ-013](#req-013) - A solution image in a public Docker Hub repository.
- [REQ-014](#req-014) - `submission.yaml` with the required keys.
- [REQ-017](#req-017) - `submission.zip` containing `submission.yaml`.
- [REQ-018](#req-018) - The uploaded Codabench submission.

## Source Coverage Audit

| Physical page | Captured content | Visuals/tables | Verification |
| ---: | --- | --- | --- |
| 1 | Task; input/output; workflow; container contract; CSV example and rules; Quick Start steps 1-4 through `docker login` | TABLE-001; CSV, Python, and shell examples | Verified against the full-resolution page render; selectable text was present and no OCR was needed. |
| 2 | Docker Hub push continuation; public-repository condition; Codabench submission; scoring; training data; rules; tips | TABLE-002; YAML, shell, formula, and S3 command examples | Verified against the full-resolution page render; selectable text was present and no OCR was needed. |

## Acceptance Checklist

- [ ] [REQ-001](#req-001): Images are grouped by camera angle, including multiple HDR exposures from one angle where applicable.
- [ ] [REQ-002](#req-002): The implementation accepts the stated JPEG input characteristics: randomized filenames and a 1024 px maximum size.
- [ ] [REQ-003](#req-003): The produced CSV groups images by camera angle.
- [ ] [REQ-004](#req-004): The container reads from `/input/images/` without requiring write access there.
- [ ] [REQ-005](#req-005): The container writes `/output/predictions.csv`.
- [ ] [REQ-006](#req-006): The CSV header is `filename,group_id`.
- [ ] [REQ-007](#req-007): Every input image appears exactly once.
- [ ] [REQ-008](#req-008): Files in one predicted group share a `group_id`.
- [ ] [REQ-009](#req-009): Each `group_id` is represented as a string or number.
- [ ] [REQ-010](#req-010): CSV entries contain filenames only, not paths.
- [ ] [REQ-011](#req-011): `solution.py` implements the specified `group_images` interface.
- [ ] [REQ-012](#req-012): On Mac, the image is built for `linux/amd64`.
- [ ] [REQ-013](#req-013): The solution image is pushed to a public Docker Hub repository.
- [ ] [REQ-014](#req-014): `submission.yaml` contains `docker_image`, `machine_type`, and `email`.
- [ ] [REQ-015](#req-015): `machine_type` is `cpu-large` or `cpu-xlarge`.
- [ ] [REQ-016](#req-016): `email` matches the bounty registration.
- [ ] [REQ-017](#req-017): `submission.yaml` is packaged as `submission.zip`.
- [ ] [REQ-018](#req-018): `submission.zip` is uploaded through **My Submissions**.
- [ ] [REQ-019](#req-019): The contestant satisfies the US-based eligibility rule.
- [ ] [REQ-020](#req-020): The container runs with no internet access.
- [ ] [REQ-021](#req-021): The submission completes within 60 minutes.
- [ ] [REQ-022](#req-022): No more than three submissions are made in one day.
- [ ] [REQ-023](#req-023): The container prints progress to stdout.
- [ ] Validate exact-match scoring: each predicted group must contain exactly the filenames in its labeled group; partial matches earn no credit. [PDF p. 2]

## Ambiguities and Questions

- <a id="amb-001"></a>**AMB-001** - The PDF does not define a geometric, perceptual, or pixel-level tolerance for deciding when two photos have the “same camera angle.” The private labeled groups and exact-match scoring are authoritative during evaluation, so implementation choices require validation against available training data. [PDF pp. 1-2]

## Visual Content Index

- [TABLE-001](#table-001) - Container input and output paths, faithfully converted from the simple table on page 1.
- [TABLE-002](#table-002) - Example scoring scenarios and scores, faithfully converted from the simple table on page 2.
- No diagrams, screenshots, photographs, or other non-text visuals appear in the PDF. No asset directory was needed.
