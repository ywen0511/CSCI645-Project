# Reproducing V5 (Study A: matched calibration ablation; Study B: dynamic in-grasp slip)

Only public sources are needed: this repository, the `v5.0.0` release assets, the `v4.0.0` final-record archive
(for the V4 regression comparison) and the official simulator distribution. Every block was executed for the
public verification recorded in [VERIFICATION.md](VERIFICATION.md); expected outputs follow each block.

## 0. Software

| Role | Version |
|---|---|
| Simulator | Isaac Lab v3.0.0 (package `isaaclab` 28.0.0) on Isaac Sim 6.2.0.0, PhysX, Python 3.12, torch 2.11.0+cu130, RSL-RL 5.5.1 ([setup](../SETUP_REMOTE.md)) |
| CPU analysis | Python 3.13.9 + [requirements-analysis.txt](../../configs/closeout/requirements-analysis.txt) |
| GPU used | NVIDIA A100-SXM4-80GB, driver bundle 580.159.03 (headless rendering needs a Vulkan ICD) |

A different simulator version is not an exact reproduction. CPU steps never launch the simulator.

## 1. Checkouts (CPU)

Run all blocks in one Bash shell. Every path is absolute.

```bash
set -eu
V5_WORK=$(mktemp -d "${TMPDIR:-/tmp}/csci645-v5-reproduce.XXXXXX")
T="$V5_WORK/delivery"      # analysis/delivery tooling at the release tag
EA="$V5_WORK/exp-a"        # Study A execution source (simulator code = experiment-v4)
EB="$V5_WORK/exp-b"        # Study B execution source (slip mechanism)
B="$V5_WORK/release"; X="$V5_WORK/extracted"; G="$V5_WORK/regenerated"
REPO_URL=https://github.com/ywen0511/CSCI645-Project.git
git clone --branch v5.0.0 "$REPO_URL" "$T"
git -C "$T" fetch --tags
git clone --branch experiment-v5a "$REPO_URL" "$EA"
git clone --branch experiment-v5b "$REPO_URL" "$EB"
test "$(git -C "$EA" rev-parse HEAD)" = 13cda3af2699f0ebfdd50affb4d27fb6dde877e8
test "$(git -C "$EB" rev-parse HEAD)" = db62bd1dbb3bb077ad4b67f3b3cd934e677db522
```

## 2. Download, verify and regenerate (CPU)

```bash
python3.13 -m venv "$V5_WORK/analysis-env"
PY="$V5_WORK/analysis-env/bin/python"
"$PY" -m pip install -r "$T/configs/closeout/requirements-analysis.txt"
"$PY" -I "$T/scripts/v3_download.py" --tag v5.0.0 --output "$B"
(cd "$B" && sha256sum -c SHA256SUMS)
"$PY" -I "$T/scripts/v5_verify.py" --bundle "$B" --extract "$X" --output "$V5_WORK/bundle_verify.json"
mkdir "$V5_WORK/v4"
curl -fL -o "$V5_WORK/v4/raw-final.tar.gz" \
  https://github.com/ywen0511/CSCI645-Project/releases/download/v4.0.0/raw-final.tar.gz
"$PY" "$T/scripts/v5_regen.py" --runs "$X" --work "$G" --v4-raw-final "$V5_WORK/v4/raw-final.tar.gz"
```

Expected:
- Every `SHA256SUMS` line reports `OK`.
- `bundle_verify.json` reports `"ok": true`:
  - all archive members are re-hashed;
  - every checkpoint index entry resolves;
  - all 15 formal runs have step 0, ten periodic, final, latest and selected checkpoints;
  - Study A has 10 × 2,400 records, Study B final 36 × 1,400 and validation 165 × 160;
  - the videos decode and the leak scan has no hits.
- `regen.json` reports every regenerated Study A and Study B table as identical, or numerically equal within
  1e-9 (listed as `float_only`), with zero `different`. Every figure is byte-identical.

### 2a. v5.0.1 CPU additions

v5.0.1 adds two CPU-only scripts that read the v5.0.0 raw records; the data stay in the v5.0.0 release. With the
tooling checked out at `v5.0.1`, `v5_regen.py` above also runs both (steps `ema_identity` and `slip_sensitivity`).
To run them alone, after the block above:

```bash
git clone --branch v5.0.1 "$REPO_URL" "$V5_WORK/delivery-501"
T1="$V5_WORK/delivery-501"
"$PY" "$T1/scripts/v5_ema_identity.py" --archive "$B/raw-study-a.tar.gz" --out "$V5_WORK/v501/ema_identity"
"$PY" "$T1/scripts/v5_slip_sensitivity.py" --runs "$X" --out "$V5_WORK/v501/sensitivity"
cmp "$V5_WORK/v501/ema_identity/summary.json" "$T1/results/v5/calibration/ema_identity/summary.json"
cmp "$V5_WORK/v501/sensitivity/summary.json" "$T1/results/v5/slip/sensitivity/summary.json"
```

Expected: both `cmp` commands print nothing. `ema_identity` reports 9,600 paired episodes with every non-identifier
record field identical; the sensitivity summary keeps 177/200 `slip_mixed_id` base cases.

## 3. Small replay, reload of every architecture, resume (remote GPU)

`ISAAC` is the Python executable of the installed simulator environment. Set `CLOSEOUT_VK_ICD_DIR` only if the
cluster wrapper needs a user-space Vulkan ICD.

```bash
ISAAC=/absolute/path/to/isaaclab-env/bin/python
test -x "$ISAAC"
R="$X"   # the extracted release is the runs root (formal/train, final/, study_a/)
"$PY" "$T/scripts/v3_jobs.py" run --manifest "$T/results/v5/jobs/verification_a.json" --repo "$EA" \
    --runs-root "$R" --isaac-python "$ISAAC" --task-timeout-s 3600
"$PY" "$T/scripts/v3_jobs.py" run --manifest "$T/results/v5/jobs/verification.json" --repo "$EB" \
    --runs-root "$R" --isaac-python "$ISAAC" --dry-run \
    --only replay60_geometry_best,replay60_slip_robust_history_s111,reload_slip_robust_ff,reload_slip_robust_history,reload_slip_robust_repeat,resume_check_train
"$PY" "$T/scripts/v3_jobs.py" run --manifest "$T/results/v5/jobs/verification.json" --repo "$EB" \
    --runs-root "$R" --isaac-python "$ISAAC" --task-timeout-s 3600
"$PY" -I "$T/scripts/v5_verification.py" compare --x "$R" --output "$V5_WORK/fresh_gpu.json"
```

This runs:
- the Study A anchor `ema0p2_cal050_a25`, which is V4's `geometry_calibrated`, on 60 held-out cases;
- `geometry_best` and the seed-111 selected history policy on the 60-case `slip_mixed_id` mechanism subset
  (batch 20);
- the seed-111 selected checkpoint of every architecture on 7 cases (the first case of each condition);
- two PPO iterations resumed from `slip_robust_history_s111/checkpoints/latest.pt` into a new directory
  (306 → 308 iterations).

The dry run resolves every input except that of `resume_check_inspect`, whose input is written by
`resume_check_train`.

Expected: `fresh_gpu.json` reports `"ok": true`:
- exact case-ID sets, no duplicates;
- identical sensor, grasp and slip specifications;
- identical checkpoint SHA-256 and configuration and controller hashes;
- the resume inspection passes.

Terminal outcomes are compared with the published batch-240 records, and every disagreement is listed under
`mismatches`. PhysX trajectories can depend on batch layout, so the public record states the measured count.

Check that the source checkpoint is unchanged:

```bash
sha256sum "$X/formal/train/slip_robust_history_s111/checkpoints/latest.pt"
grep -A3 '"member": "formal/train/slip_robust_history_s111/checkpoints/latest.pt"' "$B/checkpoints.json"
```

Repeating a runner command skips every completed task after content and provenance verification.

## 4. Full re-evaluation (optional, remote GPU)

Study A, from `$EA`:

```bash
for m in matrix_ema1p0 matrix_ema0p2; do
  "$ISAAC" scripts/eval_matrix.py --matrix "$EA/configs/v5/calibration/$m.json" --output "$V5_WORK/a/primary" --seed 6457501
done
```

Run these from `$EA` through the simulator wrapper, sequentially.

Study B, from `$EB`, with the frozen manifests in `$T/results/v5/jobs/`:
1. `final_baselines.json`
2. `final_learned.json`
3. `repeat_baselines.json` and `repeat_learned.json`
4. `regression.json`
5. `mech_dev.json`, then `mechanisms.json`

Run each with `v3_jobs.py run --repo "$EB" --runs-root <dir with train/ linked to $X/formal/train>`.

Retraining is described by `train.json` (15 runs × 10,027,008 transitions, one process per GPU, about 20
minutes each on an A100) and is not required for verification.

## Integrity notes

The runner (`scripts/v3_jobs.py`) skips a task only when its latest attempt succeeded and the output contents,
inputs, resolved arguments, execution commit and runner context all match. Changed outputs and legacy provenance
are refused. Use `T` for tooling and `EA`/`EB` for execution. Never modify the execution checkouts.
`scripts/v5_slip_study.py check` verifies all 68 frozen Study B inputs.
