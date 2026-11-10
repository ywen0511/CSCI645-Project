# Reproducing the V4 uncertain-grasp study

Only public sources are needed: this repository, the `v4.0.0` release assets and the official simulator
distribution. Use the delivery tag **`v4.0.1`** for the tooling: `v4.0.0` lacked the GPU verification manifest of
section 3 (see the v4.0.1 release notes); its data assets are unchanged and are the ones downloaded below. Every block
was executed for the public verification recorded in [VERIFICATION.md](VERIFICATION.md); expected outputs follow each block.

## 0. Software

| role | version (as recorded in `configs/v2/frozen/pip-freeze.txt` and the run metadata) |
|---|---|
| simulator | Isaac Lab v3.0.0 (package `isaaclab` 28.0.0) on Isaac Sim 6.2.0.0, PhysX, Python 3.12, torch 2.11.0+cu130, RSL-RL 5.5.1 ([setup](../SETUP_REMOTE.md)) |
| CPU analysis | Python 3.13.9 + [requirements-analysis.txt](../../configs/closeout/requirements-analysis.txt) |
| GPU used | NVIDIA A100-SXM4-40GB, driver 580.159.03 (headless rendering needs a Vulkan ICD) |

A different simulator version is not an exact reproduction. CPU steps never launch the simulator.

## 1. Checkouts (CPU)

Run all blocks in one Bash shell; every path is absolute.

```bash
set -eu
V4_WORK=$(mktemp -d "${TMPDIR:-/tmp}/csci645-v4-reproduce.XXXXXX")
T="$V4_WORK/delivery"      # analysis/delivery tooling at the release tag
E="$V4_WORK/experiment"    # immutable simulator source of every formal run
B="$V4_WORK/release"; X="$V4_WORK/extracted"; G="$V4_WORK/regenerated"; R="$V4_WORK/replay"
REPO_URL=https://github.com/ywen0511/CSCI645-Project.git
git clone --branch v4.0.1 "$REPO_URL" "$T"
git clone --branch experiment-v4 "$REPO_URL" "$E"
test "$(git -C "$E" rev-parse HEAD)" = aac4d98274814b1ab121a715db71187e3e1cc0b9
git -C "$T" rev-parse HEAD > "$V4_WORK/delivery_commit.txt"
```

## 2. Download, verify and regenerate (CPU)

```bash
python3.13 -m venv "$V4_WORK/analysis-env"
PY="$V4_WORK/analysis-env/bin/python"
"$PY" -m pip install -r "$T/configs/closeout/requirements-analysis.txt"
"$PY" -I "$T/scripts/v3_download.py" --tag v4.0.0 --output "$B"
(cd "$B" && sha256sum -c SHA256SUMS)
"$PY" -I "$T/scripts/v4_verify.py" --bundle "$B" --extract "$X" --output "$V4_WORK/bundle_verify.json"
"$PY" "$T/scripts/v4_regen.py" --runs "$X" --work "$G"
```

Expected: every `SHA256SUMS` line `OK`; `bundle_verify.json` `"ok": true` (all archive members re-hashed, every
checkpoint index entry resolved, 25 formal runs with step 0 + ten periodic + final + latest + selected, 54 final files
× 2,400 records, 150 validation files × 240, videos decoded, no leak hits); `regen.json` lists every regenerated
JSON/CSV table as identical or numerically equal (a BLAS-dependent last-digit difference is reported as
`float_only`), with zero `different`.

## 3. Small complete replay, reload of every architecture, resume (remote GPU)

`ISAAC` is the Python executable of the installed simulator environment. Set `CLOSEOUT_VK_ICD_DIR` only if the
cluster wrapper needs a user-space Vulkan ICD.

```bash
ISAAC=/absolute/path/to/isaaclab-env/bin/python
test -x "$ISAAC"
mkdir -p "$R/formal"
ln -s "$X/formal/train" "$R/formal/train"
ln -s "$X/final" "$R/final"
"$PY" "$T/scripts/v3_jobs.py" run --manifest "$T/results/v4/jobs/verification.json" --repo "$E" \
    --runs-root "$R" --isaac-python "$ISAAC" --dry-run \
    --only replay60_geometry_calibrated,replay60_combined_robust_history_s111,reload_combined_clean_ff,reload_combined_robust_ff,reload_combined_robust_history,reload_combined_robust_repeat,reload_residual_robust_history,resume_check_train
"$PY" "$T/scripts/v3_jobs.py" run --manifest "$T/results/v4/jobs/verification.json" --repo "$E" \
    --runs-root "$R" --isaac-python "$ISAAC" --task-timeout-s 3600
"$PY" -I "$T/scripts/v4_fresh_compare.py" --x "$R" --index "$T/configs/v4/final_matrix_index.json" \
    --output "$V4_WORK/fresh_gpu.json"
```

The dry run resolves every input except that of `resume_check_inspect`, whose input is the checkpoint written by
`resume_check_train`; the real run executes the nine tasks in order. This runs **all 60 cases** of the mechanism subset for the calibrated baseline and the seed-111 selected history
policy (batch 20), 12 cases (first case of every condition) for one selected checkpoint of each of the five
architectures, and two PPO iterations resumed from `combined_robust_history_s111/checkpoints/latest.pt` into a new
directory (306 → 308 iterations; 10,027,008 → 10,092,544 transitions). Let every task finish. Expected:
`fresh_gpu.json` `"ok": true` (exact case-ID sets, no duplicates, no invalid resets, identical sensor and grasp
specifications, checkpoint SHA-256 and configuration hashes), and the replay/reload terminal outcomes compared
with the published batch-240 records; any disagreement is listed under `mismatches` (PhysX trajectories can
depend on batch layout; the public record states the measured count). Check that the source checkpoint is
unchanged:

```bash
sha256sum "$X/formal/train/combined_robust_history_s111/checkpoints/latest.pt"
grep -A1 '"member": "formal/train/combined_robust_history_s111/checkpoints/latest.pt"' "$B/checkpoints.json"
```

Repeating the runner command skips every completed task after content and provenance verification.

## 4. Full reevaluation (optional, remote GPU)

```bash
F="$V4_WORK/full-final"; mkdir "$F"; ln -s "$X/formal/train" "$F/train"
"$PY" "$T/scripts/v3_jobs.py" run --manifest "$T/results/v4/jobs/final.json" --repo "$E" \
    --runs-root "$F" --isaac-python "$ISAAC" --task-timeout-s 7200
```

29 fresh processes: four executed baselines and 25 formal runs (selected then final checkpoint), 2,400 cases each
(129,600 executed episodes; `best_constant_geometry` is a declared exact alias of `geometry_calibrated`). Use
`--shard I/N` to spread independent tasks over GPUs. Retraining is described by `results/v4/jobs/train.json`
(25 runs × 10,027,008 transitions, one process per GPU) and is not required for verification.

## Integrity notes

The runner (`scripts/v3_jobs.py`) skips a task only when its latest attempt succeeded and the output contents,
inputs, resolved arguments, execution commit and runner context all match; changed outputs and legacy provenance
are refused. Use `T` for tooling and `E` for execution; never modify `E`.
