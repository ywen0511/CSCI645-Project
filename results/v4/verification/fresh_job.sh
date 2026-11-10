#!/usr/bin/env bash
# Public-download verification of v4.0.0: docs/v4/REPRODUCE.md sections 1-3 verbatim (tag v4.0.1), new empty directory.
KZ=<work-root>
export TMPDIR=$KZ/runs/csci645-project/v4_fresh2
mkdir -p "$TMPDIR"
export PATH=$KZ/envs/cpython-3.13.9/bin:$PATH
export CLOSEOUT_VK_ICD_DIR=$KZ/projs/code/csci645_ops/nvidia_580.159.03
unset GITHUB_TOKEN GH_TOKEN
export GIT_CONFIG_GLOBAL=/dev/null GIT_TERMINAL_PROMPT=0 PIP_DISABLE_PIP_VERSION_CHECK=1
export PS4='+ [$(date -u +%H:%M:%S)] '
trap 'echo "V4FRESH_FAILED line $LINENO rc $?"' ERR
set -x

echo '=== REPRODUCE section: 1. Checkouts (CPU) ==='
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

echo '=== REPRODUCE section: 2. Download, verify and regenerate (CPU) ==='
python3.13 -m venv "$V4_WORK/analysis-env"
PY="$V4_WORK/analysis-env/bin/python"
"$PY" -m pip install -r "$T/configs/closeout/requirements-analysis.txt"
"$PY" -I "$T/scripts/v3_download.py" --tag v4.0.0 --output "$B"
(cd "$B" && sha256sum -c SHA256SUMS)
"$PY" -I "$T/scripts/v4_verify.py" --bundle "$B" --extract "$X" --output "$V4_WORK/bundle_verify.json"
"$PY" "$T/scripts/v4_regen.py" --runs "$X" --work "$G"

echo '=== REPRODUCE section: 3. Small complete replay, reload of every architecture, resume (remote GPU) ==='
ISAAC=$ISAAC  # set per section 3
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

echo '=== REPRODUCE section: 3. Small complete replay, reload of every architecture, resume (remote GPU) ==='
sha256sum "$X/formal/train/combined_robust_history_s111/checkpoints/latest.pt"
grep -A1 '"member": "formal/train/combined_robust_history_s111/checkpoints/latest.pt"' "$B/checkpoints.json"

echo '=== v4.0.1 patch assets ==='
"$PY" -I "$T/scripts/v3_download.py" --tag v4.0.1 --output "$V4_WORK/release-v4.0.1"
(cd "$V4_WORK/release-v4.0.1" && sha256sum -c SHA256SUMS)

echo '=== repeat the runner: completed tasks must skip ==='
cp -r "$R/ledger" "$V4_WORK/ledger_after_first"
rc=0; "$PY" "$T/scripts/v3_jobs.py" run --manifest "$T/results/v4/jobs/verification.json" --repo "$E" --runs-root "$R" --isaac-python "$ISAAC" --task-timeout-s 3600 > "$V4_WORK/repeat_run.log" 2>&1 || rc=$?
echo "repeat_rc=$rc"; grep -c "skip " "$V4_WORK/repeat_run.log"
"$PY" -c 'import sys;print(sys.version)'
echo "V4_WORK=$V4_WORK"
echo V4FRESH_DONE
