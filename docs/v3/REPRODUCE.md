# Reproducing the v3 study from public sources

Everything below uses only this public repository, the GitHub release `v3.0.0` and the official simulator
distribution. Paths are relative to a checkout. [VERIFICATION.md](VERIFICATION.md) records which of these
commands were run on a fresh download, with exit codes and results.

## Versions and roles

| Role | Revision | Used for |
|---|---|---|
| Experiment source | tag `experiment-v3` = `3811f5da5ef55638f95f7306e449609877f546df` | every simulator command (training, validation, final evaluation, extras, videos) |
| Delivery source | tag `v3.0.0` (release) | analysis, regeneration, figures, report/slides, packaging, verification, and the post-freeze matrices/suites passed to the experiment checkout (`configs/v3/final_matrices/`, `configs/v3/suites/final_subset65.jsonl`, `final_trace6.jsonl`, `configs/v3/video/`) |

Post-freeze files are created by frozen rules from the selection (`scripts/v3_manifests.py`); they never change
simulator code. Both source trees are in the release (`source-experiment-v3.tar.gz`, `source-v3.0.0.tar.gz`).

## Environments

- **CPU (analysis, regeneration, rendering, verification):** Python 3.13 with
  [`configs/closeout/requirements-analysis.txt`](../../configs/closeout/requirements-analysis.txt) (NumPy 2.4.4,
  Matplotlib 3.11.2, Markdown, python-pptx, pypdf, imageio-ffmpeg). Rendering also needs Chrome/Chromium (report
  PDF) and LibreOffice (slides PDF).
- **GPU (simulator):** Isaac Lab v3.0.0, Isaac Sim 6.2.0.0 (PhysX), RSL-RL 5.5.1, PyTorch 2.11 (CUDA 13), Python
  3.12, installed per [`docs/SETUP_REMOTE.md`](../SETUP_REMOTE.md). The environment used for v3 is identical
  to the lock [`configs/v2/frozen/pip-freeze.txt`](../../configs/v2/frozen/pip-freeze.txt) (checked on
  2026-11-08). The study ran on A100-SXM4-40GB, driver 580.159.03. A node without a system Vulkan driver needs a
  user-space NVIDIA ICD folder in `CLOSEOUT_VK_ICD_DIR`; it is not distributed here. Simulator commands are run
  through `scripts/cluster/isaac_run.sh <isaac python> <script> ...` (sets caches, Vulkan and `PYTHONPATH`).

## 1. Download, check and extract (CPU)

```bash
git clone https://github.com/ywen0511/CSCI645-Project.git v3-delivery
cd v3-delivery && git checkout v3.0.0
python3.13 -m venv .venv && .venv/bin/pip install -r configs/closeout/requirements-analysis.txt
PY=$PWD/.venv/bin/python
mkdir -p ../v3-release && gh release download v3.0.0 --repo ywen0511/CSCI645-Project --dir ../v3-release
#   (or download every asset from https://github.com/ywen0511/CSCI645-Project/releases/tag/v3.0.0)
(cd ../v3-release && sha256sum -c SHA256SUMS)
$PY -I scripts/v3_verify.py --bundle ../v3-release --extract ../v3-x --output ../v3-verify.json
```

`v3_verify.py` checks `SHA256SUMS` and `release_manifest.json`, re-hashes every archive member against
`archive_inventories.json`, extracts safely into `../v3-x`, and checks that every checkpoint in
`checkpoints.json` resolves (all 23 formal runs with step 0, ten periodic saves, final, latest and the selected
tag), that the 50 executed final record files have 2,600 records each and the 138 validation files 240 each,
that the videos decode, the PDFs and PPTX open, and that no private path appears. Extracted layout:
`train/` is under `formal/train/`; `final/`, `validation/`, `zero_policy/`, `interventions/`, `repeatability/`,
`traces6/`, `development/`, `acceptance/`, `pilot/`, `smoke/`, `videos/`, `results/v3/`, `configs/v3/`, `report/v3/`.

## 2. Quickstart: regenerate all tables and figures from the raw records (CPU, ~1 min)

```bash
$PY scripts/v3_regen.py --runs ../v3-x --work ../v3-regen
```

Runs checkpoint selection, the main analysis (`v3_analyze.py`, 10,000 bootstrap replicates), mechanisms,
repeatability, interventions, zero-policy and trace summaries plus figures, and compares every generated
JSON/CSV with the committed `results/v3/` (identical / float-only / different) in `../v3-regen/regen.json`.
Individual steps:

```bash
$PY scripts/v3_select_checkpoints.py --validation ../v3-x/validation --output ../v3-regen/selection
$PY scripts/v3_analyze.py --index configs/v3/final_matrix_index.json --root ../v3-x --output ../v3-regen/summary
$PY scripts/v3_mechanisms.py --index configs/v3/final_matrix_index.json --root ../v3-x --output ../v3-regen/mechanisms
$PY scripts/v3_repeatability.py --runs ../v3-x --index configs/v3/final_matrix_index.json --output ../v3-regen/repeatability
$PY scripts/v3_interventions.py --runs ../v3-x --index configs/v3/final_matrix_index.json --output ../v3-regen/interventions
$PY scripts/v3_figures.py --summary ../v3-regen/summary --selection ../v3-regen/selection --output ../v3-regen/figures
```

Report numbers: `scripts/v3_report_values.py` (→ `results/v3/report_values.json`), `scripts/v3_render_report.py`
(template → `report/v3/report.md` + `results/v3/number_audit.json`), `scripts/v3_build_report.py` (PDF),
`scripts/v3_build_slides.py` (slides, notes and slide number audit).

## 3. Simulator steps (GPU)

Run from a clean experiment checkout; post-freeze matrices are read from the delivery checkout. Set

```bash
git clone https://github.com/ywen0511/CSCI645-Project.git v3-exp && git -C v3-exp checkout experiment-v3
ISAAC=/path/to/isaaclab-env/bin/python
D=$PWD/v3-delivery            # delivery checkout at v3.0.0
X=$PWD/v3-x                   # extracted release (checkpoints under $X/formal/train)
cd v3-exp
```

**Tiny replay (one case, ~2 min):** geometry_common on the first case of the predeclared 65-case subset —

```bash
bash scripts/cluster/isaac_run.sh $ISAAC scripts/eval_matrix.py \
  --matrix $D/configs/v3/final_matrices/extras/repeat_geometry_common.json --num-envs 1 \
  --output ../replay_tiny --seed 6455601
```

(`eval_matrix.py` runs all 65 cases of that matrix; stop after the first record if you only want one.) Matrix
files reference `$DELIVERY/...`; the job runner `scripts/v3_jobs.py` substitutes `$DELIVERY`, `$RUNS` and `$PY`.
Running a whole stage through the runner is the simplest way:

```bash
cd $D
$ISAAC scripts/v3_jobs.py run --manifest results/v3/jobs/verification.json --isaac-python $ISAAC \
    --runs-root $X --repo ../v3-exp --task-timeout-s 3600      # 65-case replay (7 entries), reloads, resume check
```

Each manifest (`results/v3/jobs/*.json`) lists every task of one stage with exact argv, inputs and outputs:
`train.json` (23 formal runs, ~20 min each on one A100), `validation.json` (138), `final.json` (50 executed
entries; three baseline roles are aliases, `configs/v3/final_matrices/baseline_aliases.json`), `extras.json`
(zero-policy, interventions, repeatability), `traces6.json`, `videos.json` (recording + index/montage) and
`verification.json`. `--shard I/N` runs every N-th task; shards are independent (one GPU each). Use
`--runs-root <new dir>` to re-train or re-evaluate from scratch; use `--runs-root $X` to evaluate the released
checkpoints.

**Complete final evaluation** (re-evaluate the released checkpoints):

```bash
$ISAAC scripts/v3_jobs.py run --manifest results/v3/jobs/final.json --isaac-python $ISAAC --runs-root ../v3-reeval \
    --repo ../v3-exp --task-timeout-s 3600
```

with `../v3-reeval/train` → a link to `$X/formal/train` (the final matrices take checkpoints relative to
`$RUNS/train`). Records are bitwise comparable to `$X/final/` only up to GPU floating-point nondeterminism;
the 65-case replay quantifies this.

**Resume:** every formal run keeps `checkpoints/latest.pt` (optimizer, normalizer, RNG and counters):

```bash
sha256sum $X/formal/train/combined_robust_history_s11/checkpoints/latest.pt     # unchanged afterwards
bash scripts/cluster/isaac_run.sh $ISAAC scripts/train.py --method combined --seed 11 \
  --protocol configs/v3/frozen/training/combined_robust_history.json --run-type smoke \
  --resume $X/formal/train/combined_robust_history_s11/checkpoints/latest.pt --transitions 10092544 \
  --output /tmp/resume_s11
bash scripts/cluster/isaac_run.sh $ISAAC scripts/closeout_inspect_ckpt.py \
  --before $X/formal/train/combined_robust_history_s11/checkpoints/latest.pt \
  --after /tmp/resume_s11/checkpoints/final.pt --expect-iterations 308 --expect-transitions 10092544 \
  --output /tmp/resume_s11/inspect.json
```

(two more PPO iterations, 306 → 308, into a disposable directory; the inspection compares counters, optimizer
and normalizer state; these are the `resume_check_*` tasks of `verification.json`).

**Video replay:** `results/v3/jobs/videos.json` (three recording processes, one per estimator configuration,
then `scripts/v3_video_index.py` for decode checks and the montage). Plans: `configs/v3/video/plan_*.json`.

**Re-training from scratch:** `results/v3/jobs/train.json` then `validation.json`, then
`scripts/v3_select_checkpoints.py` and `scripts/v3_manifests.py final extras traces6 verification` to rebuild
post-freeze matrices from the new selection.

## Resume and refusal rules

`eval_matrix.py` resumes an incomplete entry by skipping recorded case IDs only if their suite, configuration,
controller, checkpoint hashes and observation-error spec match, and aborts otherwise (acceptance check 10). The
job runner skips a task only if its outputs exist and its last successful attempt had identical inputs, argv
and source commit; every attempt is logged in `<runs>/ledger/<task>.jsonl` (merged in
`results/v3/task_ledger.jsonl`). A task is killed 90 s after the simulator prints its shutdown marker if all
outputs exist (Isaac Sim may otherwise hang at exit); this is logged as a watchdog event.
