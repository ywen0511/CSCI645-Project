# Current assignment: publish and verify the final project review

## Mission, authority and stopping point

You are the execution agent for Yan Wen's CSCI 645 project in
`https://github.com/ywen0511/CSCI645-Project`, branch `study/v4-grasp-uncertainty`.
Complete the finite assignment below through public release and fresh-download
verification. This file and the linked repository/public assets contain all required
context. No prior chat, owner-local file or additional owner instruction is required.
All public output is English. The owner already authorized routine fixes, commits,
pushes, new immutable tags, and publication of project artifacts.

**V4 training, evaluation, checkpoints and the original release are already complete.**
This is a CPU-only synthesis/review delivery. Do not run GPU jobs or Isaac Sim, restart
any training matrix, create a V5 study, or repeat the old V4 mission. Do not buy compute,
alter account settings, force-push, delete evidence or replace published assets/tags.
Keep `POST_V3_STATUS.json` as the historical completed-study record; track this assignment
in `FINAL_REVIEW_STATUS.json`.

Finish when a new public supplement release contains every package asset, all new
downloads verify, inherited checkpoints/results remain accessible with their published
hashes, and the branch records verification plus final status. A missing GitHub write
credential is a concrete blocker: commit/push what is possible, record the exact failed
operation, and leave publication flags false. Do not equate a negative result with a blocker.

## Scientific context and completed local work

The task uses Isaac Sim through Isaac Lab / PhysX, two Franka arms with two-finger
parallel-jaw grippers, a rigid bar, fixed commanded orientations and bounded XYZ PPO
residuals. V4 tests unknown static initial in-grasp translation and synthetic translation
measurement corruption. It does not test dynamic slip, vision, new objects or hardware.

Read [the overview](report/final/overview.md), [review corrections](docs/final_review/REVIEW.md)
and [defense notes](docs/final_review/DEFENSE_NOTES.md). The independent CPU audit checked
129,600 published final records, primary confidence intervals, 78 frozen source hashes
and 25 selections from recorded validation summaries. It added a post hoc common-valid
reset analysis (189 boundary cases); the history deficit persists. No original data,
report, checkpoint or experiment tag changed. The six-page supplement was rendered and
visually checked. Local tests passed 105 with one Isaac-import skip.

Preserve these interpretation constraints in release notes and final communication:

- The final calibration comparison changes reference, EMA and alignment bound. It is
  a controller-package contrast; matched development controls are not held-out proof.
- Both primary learning intervals touch zero; claim neither superiority nor equivalence.
- The common-valid analysis is post hoc and conditional; retain the original denominator.
- V2 residual-only learning improved nominal control. Do not say RL never helped.
- A checkpoint index entry is not necessarily a unique weight file or independent run.

## 1. Clean checkout and CPU validation

Use a fresh checkout on the remote machine. Commands are Bash; continue in the same
shell. Python 3.11+ is sufficient for this review; it is separate from the frozen
Python 3.12 simulator environment. PyTorch below is only for CPU regression tests.

```bash
set -eu
REVIEW_WORK=$(mktemp -d "${TMPDIR:-/tmp}/csci645-final-review.XXXXXX")
git clone --branch study/v4-grasp-uncertainty \
  https://github.com/ywen0511/CSCI645-Project.git "$REVIEW_WORK/repo"
cd "$REVIEW_WORK/repo"
git fetch origin --tags
python3 -m venv .venv-cpu
REVIEW_PY="$PWD/.venv-cpu/bin/python"
"$REVIEW_PY" -m pip install numpy==2.4.6 pytest==9.2.0 matplotlib==3.11.2 reportlab==4.4.9
"$REVIEW_PY" -m pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu
export CUDA_VISIBLE_DEVICES=''
mkdir -p outputs/final-review downloads/v4-review
"$REVIEW_PY" -m pytest -q > outputs/final-review/pytest.txt
curl -fL --retry 2 -o downloads/v4-review/raw-final.tar.gz \
  https://github.com/ywen0511/CSCI645-Project/releases/download/v4.0.0/raw-final.tar.gz
"$REVIEW_PY" scripts/final_review_audit.py --archive downloads/v4-review/raw-final.tar.gz \
  --out outputs/final-review/audit.json
cmp results/final_review/audit.json outputs/final-review/audit.json
"$REVIEW_PY" scripts/final_review_build.py --markdown-only
git diff --exit-code -- report/final/overview.md
```

If the CPU Torch index has no wheel for the machine, use a compatible preinstalled CPU
Torch environment or install the same version's normal wheel with CUDA hidden; do not
launch the simulator to work around a packaging problem. Record actual dependencies.
Do not silently change analysis definitions to force agreement. Investigate a failed
check and fix only the new review tooling if justified; preserve the frozen study.

The already-built PDF/PNG are deliverables. To regenerate them, run
`"$REVIEW_PY" scripts/final_review_build.py`; inspect every rendered PDF page, including
tables, links and figure labels, before committing rebuilt artifacts. Font/library
differences can change bytes; the Markdown/audit must still agree and the visuals must
remain correct. The local reference build used ReportLab 4.4.9 and Matplotlib 3.11.2.

## 2. Prepare and publish the supplement

The proposed tag is **v4.0.2**. First inspect repository tags/releases. If that tag already
contains this verified supplement, verify it and finish rather than creating duplicates.
If it was used for unrelated work, use the next unused V4 patch tag and record why.
Never move a tag or replace a published asset. Resume an existing draft only if its
source commit and asset hashes match this package; otherwise use a new unused tag.

Ensure all intended fixes and regenerated artifacts are committed and pushed to the
same branch; resolve concurrent updates by normal fast-forward/rebase, never force.
Packaging refuses a dirty checkout and nonempty destination. It creates 12 assets:
overview PDF/Markdown/PNG, review and defense notes, release notes, audit JSON, inherited
asset index, source commit, full source archive, package manifest and checksums.
The exact set is enforced by the verifier (the overview accounts for three assets).

```bash
git status --short
git push origin HEAD:study/v4-grasp-uncertainty
REVIEW_COMMIT=$(git rev-parse HEAD)
REVIEW_TAG=v4.0.2
REVIEW_PACKAGE="$REVIEW_WORK/package"
"$REVIEW_PY" scripts/final_review_package.py build --directory "$REVIEW_PACKAGE"
"$REVIEW_PY" scripts/final_review_package.py verify --directory "$REVIEW_PACKAGE"
git tag -a "$REVIEW_TAG" "$REVIEW_COMMIT" -m 'V4 final synthesis and independent CPU review'
git push origin "refs/tags/$REVIEW_TAG"
gh release create "$REVIEW_TAG" --repo ywen0511/CSCI645-Project --verify-tag --draft \
  --title "$REVIEW_TAG — Final synthesis and independent CPU review" \
  --notes-file "$REVIEW_PACKAGE/RELEASE_NOTES.md"
gh release upload "$REVIEW_TAG" "$REVIEW_PACKAGE"/* --repo ywen0511/CSCI645-Project
```

Before publishing, download the draft assets into a separate empty directory using
authenticated `gh release download`, run `final_review_package.py verify`, and compare
every asset byte with the package. Check the draft has exactly the 12 expected assets
and the source tag resolves to `REVIEW_COMMIT`. Keep the new source snapshot distinct
from experiment-v4. The original trained weights belong to experiment-v4, not this tag.

Then publish the draft:

```bash
gh release edit "$REVIEW_TAG" --repo ywen0511/CSCI645-Project --draft=false
```

## 3. Fresh public-download verification and inherited delivery

Download the new release anonymously to a new empty directory; the existing downloader
uses the public API and needs no owner-local material. Do not use cached package bytes.

```bash
REVIEW_PUBLIC="$REVIEW_WORK/public-download"
"$REVIEW_PY" scripts/v3_download.py --tag "$REVIEW_TAG" --output "$REVIEW_PUBLIC"
mv "$REVIEW_PUBLIC/download_log.json" outputs/final-review/public-download-log.json
"$REVIEW_PY" scripts/final_review_package.py verify --directory "$REVIEW_PUBLIC" \
  > outputs/final-review/package-public-verification.json
```

Use a separate fresh public clone at the new tag and fetch experiment-v4. Execute the
CPU audit from that clone against a fresh anonymous raw-final download. Compare its
JSON with the released `audit.json`; regenerate the Markdown and compare it with the
released overview. Open the downloaded PDF and inspect all six pages. Record the exact
tag SHA, command outputs, dependency versions and checksums. Do not claim a new GPU
replay: prior physics/reload/resume verification is already documented in
[docs/v4/VERIFICATION.md](docs/v4/VERIFICATION.md).

**All checkpoints and earlier results are already uploaded.** Do not retrain or upload
empty placeholder checkpoint directories. `INHERITED_ASSETS.json` lists all 30 v4.0.0
study assets and six v4.0.1 tooling assets, with exact public URLs, sizes and SHA-256.
Download all 36 into separate tag-named directories and verify each against that index.
This includes all five formal checkpoint archives, pilot/smoke checkpoints, checkpoint
index, raw records, logs, videos, source snapshots, original report and slides. Keep
those immutable assets in their existing releases, explicitly linked from the patch.
If an asset is inaccessible or has changed, leave verification incomplete and report
the exact failing URL/hash; do not invent a replacement. Existing public-download
verification is useful prior evidence, but does not replace this delivery's check.

## 4. Record completion and stop

Create `results/final_review/public_verification.json` with: release URL and tag/commit;
new asset names/sizes/hashes and all pass flags; 36 inherited asset verification results;
fresh-clone audit equality; Markdown equality; PDF page count/visual check; CPU test
result and versions; explicit `gpu_runs: 0`; timestamps and any remaining limitations.
Use repo-relative paths and public URLs, never host-local paths or credentials.
Add a concise English `docs/final_review/PUBLIC_VERIFICATION.md` with exact reproduction
commands and links. Include the package verifier's raw JSON and sanitized test output.

Only after every gate passes, update `FINAL_REVIEW_STATUS.json` with the actual release,
`supplement_release_published: true`, `fresh_public_download_verified: true`,
`complete: true`, and an empty remaining list. Link the new release and verification
record prominently from README. Append the delivery outcome to `docs/DECISIONS.md`.
Commit and push the verification/status follow-up; do not move the release tag to it.
The release snapshot can truthfully precede its own public verification.

Your final English response must link the source tag, branch verification commit,
supplement release/PDF, full archived report/deck, checkpoint index and checkpoint
archive location, raw results, videos and the public verification record. State that
this delivery added no new GPU experiment, that the V4 study was already complete,
and that this supplement adds corrections and retrospective analysis. Do not stop at
a draft, a local package, a plan, or an upload without verification.
