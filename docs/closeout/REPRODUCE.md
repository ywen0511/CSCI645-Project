# Reproducing the v2 study and the closeout from public sources

This guide supersedes the command list in [`docs/v2/REPRODUCE.md`](../v2/REPRODUCE.md), which mixed scripts that
exist only after `experiment-v2`. Every step below runs through one driver, `scripts/closeout.py`, with explicit
paths. No step needs anything except this public repository, its GitHub releases and the official
simulator distribution. [VERIFICATION.md](VERIFICATION.md) lists which commands were run, where and with what
result.

## Two checkouts with fixed roles

| Role | Revision | What runs from it |
|---|---|---|
| **Experiment checkout** | tag `experiment-v2` = `1d9d0e23eec346c1b1cb3c0c245a1e772df7bedf` | every simulator command: `eval_matrix.py`, `run_scripted.py`, `train.py`, `record_video.py` (created by the `checkout` stage under `<work>/src/experiment-v2`) |
| **Delivery-tools checkout** | tag `v2.1.0` (release) — Stage 4 itself ran with tag `closeout-eval-v1` = `6bf80bb38ffc38821ae8a6b4bbcdc99fa89574af` | the driver, download/integrity, CPU regeneration, analysis, rendering, packaging, verification, and the closeout configs/matrices passed to the experiment checkout |

The simulator code (`src/`, the four simulator scripts), the frozen protocol and the final suite are
byte-identical in both checkouts ([`results/closeout/supplementary_source_identity.json`](../../results/closeout/supplementary_source_identity.json));
the driver re-checks this before every simulator stage and refuses a dirty or wrong experiment checkout.

## Environments

- **CPU (analysis, regeneration, packaging, verification):** Python 3.13 with
  [`configs/closeout/requirements-analysis.txt`](../../configs/closeout/requirements-analysis.txt) (NumPy 2.4.4,
  Matplotlib 3.11.2, Markdown, python-pptx, pypdf, imageio-ffmpeg). Other NumPy builds can change the last
  printed digit of `np.polyfit` slopes in two v2 files; the comparison classifies such changes as float-only.
- **Rendering:** Google Chrome/Chromium (report PDF) and LibreOffice (deck PDF); versions used are in
  [`results/closeout/render_environment.json`](../../results/closeout/render_environment.json).
- **GPU (simulator):** Isaac Lab v3.0.0, Isaac Sim 6.2.0.0, PhysX, RSL-RL 5.5.1, PyTorch 2.11 (CUDA 13), Python 3.12,
  installed per [`docs/SETUP_REMOTE.md`](../SETUP_REMOTE.md) and checked against the lock
  [`configs/v2/frozen/pip-freeze.txt`](../../configs/v2/frozen/pip-freeze.txt). Pass its Python with
  `--isaac-python` (or `CLOSEOUT_ISAAC_PYTHON`). A node without a system Vulkan driver needs a user-space
  NVIDIA ICD folder in `CLOSEOUT_VK_ICD_DIR` (not distributed here). The simulator itself is not
  redistributed.

## Quickstart (CPU only, copy-paste)

```bash
git clone https://github.com/ywen0511/CSCI645-Project.git CSCI645-Project
cd CSCI645-Project
git checkout v2.1.0
python3.13 -m venv .venv-analysis
.venv-analysis/bin/pip install -r configs/closeout/requirements-analysis.txt
PY=$PWD/.venv-analysis/bin/python
W=$PWD/closeout_work
$PY scripts/closeout.py --work "$W" download --tag v2.1.0      # anonymous; sha256 + member re-hash + extract
$PY scripts/closeout.py --work "$W" checkout                    # clean experiment-v2 checkout under $W/src
$PY scripts/closeout.py --work "$W" check                       # scripts, CLI flags, links, asset names, sim-code identity
$PY scripts/closeout.py --work "$W" regen                       # v2 tables/figures from downloaded raw records
$PY scripts/closeout.py --work "$W" analyze --from-release      # Stage 4 tables/figures from downloaded raw records
$PY scripts/closeout.py --work "$W" verify --tag v2.1.0         # re-verify the downloaded release
```

Outputs: `$W/regen/comparison.json` (each archived v2 file: identical / float-only / figure / substantive),
`$W/analysis/repeatability/` (compared with the committed `results/closeout/repeatability/` in
`$W/records/analyze.json`), `$W/verify/v2.1.0.json`, and one record per stage in `$W/records/`.

## Simulator stages (GPU)

```bash
ISAAC=/path/to/isaaclab-env/bin/python          # Isaac Lab v3.0.0 environment (see Environments)
W=$PWD/closeout_work                             # same work folder as the quickstart (download + checkout done)
$PY scripts/closeout.py --work "$W" negative --isaac-python "$ISAAC"        # clean episodes + 3 negative controls
$PY scripts/closeout.py --work "$W" replay --isaac-python "$ISAAC"          # predeclared 60-case replay, 22 entries
$PY scripts/closeout.py --work "$W" resume-smoke --isaac-python "$ISAAC"    # resume latest.pt for 2 PPO iterations
$PY scripts/closeout.py --work "$W" video-replay --isaac-python "$ISAAC"    # re-render the 10 videos
$PY scripts/closeout.py --work "$W" repeatability --throughput --isaac-python "$ISAAC"   # ~3 min check
for I in 0 1 2 3; do                                                         # Stage 4 (48 tasks, ~7 GPU-h)
  $PY scripts/closeout.py --work "$W" repeatability --shard $I/4 --isaac-python "$ISAAC"
done
$PY scripts/closeout.py --work "$W" analyze
```

`--shard I/N` runs every N-th task of [`results/closeout/repeatability/run_manifest.json`](../../results/closeout/repeatability/run_manifest.json);
shards are independent and can run in parallel, one GPU each. On an LSF cluster:
`CLOSEOUT_LSF_QUEUE=<queue> scripts/cluster/lsf_submit.sh <name> <HH:MM> 1 <driver command>`; with another
scheduler run the same driver command in its job script.

**Resume and refusal rules.** A simulator task is complete when its `matrix_status.json` shows every scheduled
case recorded. An incomplete task is resumed by `eval_matrix.py`, which skips recorded case IDs only if their
suite, configuration, controller and checkpoint hashes match, and aborts otherwise. Each task gets at most
`--max-attempts` (default 3) attempts, all logged in `$W/ledger/<task>.jsonl`. The repeatability stage refuses
to run if the config or a matrix differs from the hashes frozen in the run manifest. `download` re-uses a
download only if its `SHA256SUMS` hash matches the verified marker. `checkout` refuses a checkout that is
not clean at `experiment-v2`. `package` refuses an existing output folder and a dirty source checkout.

## Original v2 experiment (replay of training/evaluation; not needed to verify the results)

Run from the experiment checkout (`cd "$W/src/experiment-v2"`) with the Isaac Lab Python. These are the
commands of the v2 study (paths relative to that checkout; `$X` = `$W/inputs/v2.1.0/x`, the extracted
release):

```bash
X=$W/inputs/v2.1.0/x
cd "$W/src/experiment-v2"
$ISAAC scripts/train.py --method combined --seed 11 --protocol configs/v2/frozen/protocol.json --run-type final \
    --output "$W/retrain/combined_seed11"                      # 10,027,008 transitions; resume: --resume <dir>/checkpoints/latest.pt
$ISAAC scripts/eval_matrix.py --matrix configs/v2/matrices/final/final_det_1.json --output "$W/reeval/det_1"
```

The learned-run final matrices (`configs/v2/matrices/final/final_<run>.json`, created by the frozen selection
after `experiment-v2`) live in the delivery-tools checkout. Pass them by absolute path together with
`--checkpoint-root "$X"`:
`$ISAAC scripts/eval_matrix.py --matrix <tools>/configs/v2/matrices/final/final_combined_seed11.json --output "$W/reeval/combined_seed11" --checkpoint-root "$X"`.

## Rendering and packaging (maintainers)

```bash
$PY scripts/closeout.py --work "$W" render --chrome google-chrome --soffice libreoffice
$PY scripts/closeout.py --work "$W" package --release-tag v2.1.0       # needs $W/inputs/v2.0.0 (download --tag v2.0.0)
```
