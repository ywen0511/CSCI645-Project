# Public verification of the v4.0.2 review supplement

**Result: passed.** Release [v4.0.2](https://github.com/ywen0511/CSCI645-Project/releases/tag/v4.0.2)
(tag `v4.0.2` → commit `50037af8c0ac2d17c4a3989b538332f6c8807ad3`, published 2026-11-11T04:16:28Z)
was downloaded anonymously into a new directory. Its 12 assets passed the package verifier and match
`release_manifest.json`. A fresh public clone of the tag re-ran the CPU audit against a fresh
anonymous `raw-final.tar.gz` download. Its `audit.json` is byte-identical to the released one, and the
regenerated `overview.md` is byte-identical to the released Markdown. All 36 inherited
v4.0.0/v4.0.1 assets were downloaded anonymously and match `INHERITED_ASSETS.json` in size, SHA-256
and URL.

This supplement adds **no new GPU experiment**: `gpu_runs: 0`, `simulator_runs: 0`. The V4 study
was already complete. This release adds corrections and retrospective analysis only. Physics replay,
checkpoint reload and resume were verified earlier, as recorded in [../v4/VERIFICATION.md](../v4/VERIFICATION.md).

Machine-readable record: [results/final_review/public_verification.json](../../results/final_review/public_verification.json).
Raw evidence is in [results/final_review/public_verification/](../../results/final_review/public_verification/):
- package verifier output;
- download logs;
- per-asset inherited check;
- pytest output from both clones.

## Gates

| gate | result |
|---|---|
| CPU tests, fresh branch clone at `50037af` and fresh tag clone | 105 passed, 1 skipped (Isaac Lab not installed) |
| Audit from fresh branch clone, compared with committed `audit.json` | `PASS: 129600 episodes; 189 common-valid boundary cases`, byte-identical |
| `final_review_build.py --markdown-only` on branch clone | `overview.md` unchanged |
| Package build + verify (clean checkout) | passed, 12 assets, 1,298 archive members |
| Draft: authenticated download, byte comparison and verifier; tag check | 12/12 byte-identical, passed; tag → `50037af` |
| Anonymous download of v4.0.2 + `final_review_package.py verify` | passed (12 assets) |
| Fresh tag clone: audit from fresh `raw-final.tar.gz` (`26b27cd5…f627`) | byte-identical to released `audit.json` |
| Fresh tag clone: regenerated `overview.md` | byte-identical to released asset |
| Released `overview.pdf` (`a220fda1…8052`) | 6 pages, all inspected; 18 links, all public `https` |
| 36 inherited assets (30 in v4.0.0, 6 in v4.0.1) | 36/36 size, SHA-256 and URL match |

Environment:
- Python 3.13.9 venv on a remote Linux CPU node with CUDA hidden. The system Python 3.12 lacked
  the `venv` module.
- numpy 2.4.6, torch 2.15.0+cpu (CPU wheel index), pytest 9.2.0, matplotlib 3.11.2, reportlab 4.4.9.

The PDF and PNG were not rebuilt. The released files are the committed reference build, verified
by hash and by visual inspection.

## Reproduction commands

```bash
set -eu
W=$(mktemp -d "${TMPDIR:-/tmp}/csci645-v402.XXXXXX")
git clone --branch v4.0.2 https://github.com/ywen0511/CSCI645-Project.git "$W/repo"
cd "$W/repo"
git fetch origin tag experiment-v4
test "$(git rev-parse HEAD)" = 50037af8c0ac2d17c4a3989b538332f6c8807ad3
python3 -m venv .venv-cpu; PY="$PWD/.venv-cpu/bin/python"
"$PY" -m pip install numpy==2.4.6 pytest==9.2.0 matplotlib==3.11.2 reportlab==4.4.9
"$PY" -m pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu
CUDA_VISIBLE_DEVICES='' "$PY" -m pytest -q                       # 105 passed, 1 skipped
"$PY" -I scripts/v3_download.py --tag v4.0.2 --output "$W/public-download"
"$PY" scripts/final_review_package.py verify --directory "$W/public-download"   # "passed": true
mkdir "$W/raw"
curl -fL -o "$W/raw/raw-final.tar.gz" \
  https://github.com/ywen0511/CSCI645-Project/releases/download/v4.0.0/raw-final.tar.gz
"$PY" scripts/final_review_audit.py --archive "$W/raw/raw-final.tar.gz" --out "$W/audit.json"
cmp "$W/audit.json" "$W/public-download/audit.json"
"$PY" scripts/final_review_build.py --markdown-only
cmp report/final/overview.md "$W/public-download/overview.md"
```

Inherited assets (the check script is on the branch after the tag, so use a branch checkout):

```bash
B="$W/branch"; git clone --branch study/v4-grasp-uncertainty https://github.com/ywen0511/CSCI645-Project.git "$B"
for t in v4.0.0 v4.0.1; do python3 -I "$B/scripts/v3_download.py" --tag "$t" --output "$W/inherited/$t"; done
python3 -I "$B/scripts/final_review_inherited_check.py" --index "$B/results/final_review/INHERITED_ASSETS.json" \
  --downloads "$W/inherited" --output "$W/inherited.json"     # {"passed": true, "assets_checked": 36, "assets_passed": 36}
```

## Where everything is

- Supplement release and PDF: [v4.0.2](https://github.com/ywen0511/CSCI645-Project/releases/tag/v4.0.2),
  [overview.pdf](https://github.com/ywen0511/CSCI645-Project/releases/download/v4.0.2/overview.pdf)
- Full archived report and deck: [report.pdf](https://github.com/ywen0511/CSCI645-Project/releases/download/v4.0.0/report.pdf),
  [slides.pptx](https://github.com/ywen0511/CSCI645-Project/releases/download/v4.0.0/slides.pptx)
  in [v4.0.0](https://github.com/ywen0511/CSCI645-Project/releases/tag/v4.0.0)
- Checkpoint index: [checkpoints.json](https://github.com/ywen0511/CSCI645-Project/releases/download/v4.0.0/checkpoints.json).
  Checkpoint archives (`checkpoints-formal-*.tar.gz`, pilot/smoke) are in v4.0.0. An index entry is
  not necessarily a unique weight file or an independent run.
- Raw results: [raw-final.tar.gz](https://github.com/ywen0511/CSCI645-Project/releases/download/v4.0.0/raw-final.tar.gz) and the other v4.0.0 archives
- Videos: [results/v4/videos/video_index.json](../../results/v4/videos/video_index.json); MP4s are in [videos.tar.gz](https://github.com/ywen0511/CSCI645-Project/releases/download/v4.0.0/videos.tar.gz) (index [videos.json](https://github.com/ywen0511/CSCI645-Project/releases/download/v4.0.0/videos.json))
- Tooling patch: [v4.0.1](https://github.com/ywen0511/CSCI645-Project/releases/tag/v4.0.1)

## Incident

The workstation upload of `source-review.tar.gz` to the unpublished draft failed with a TLS error and
left an incomplete ("starter") asset entry. I deleted that incomplete draft entry and uploaded the same
file from the remote CPU node. Before publication, the draft had exactly 12 assets, byte-identical to
the verified package. No published asset or tag was replaced or moved.

## Interpretation reminders

- The final fixed-versus-calibrated comparison changes the reference, the EMA and the alignment bound
  together. It is a controller-package contrast. Matched development controls are not held-out proof.
- Both primary learning intervals touch zero. Neither superiority nor equivalence is claimed.
- The common-valid analysis is post hoc and conditional. The original denominator stays primary.
- V2 residual-only learning improved over nominal control, so RL did help there.
