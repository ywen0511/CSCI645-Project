#!/usr/bin/env bash
# V5 public verification, cluster part 2 (GPU job): REPRODUCE.md section 3 verbatim.
KZ=<WORK>
V5_WORK=$(cat $KZ/runs/csci645-project/v5_fresh_work.txt)
T="$V5_WORK/delivery"; EA="$V5_WORK/exp-a"; EB="$V5_WORK/exp-b"; B="$V5_WORK/release"; X="$V5_WORK/extracted"
PY="$V5_WORK/analysis-env/bin/python"
export CLOSEOUT_VK_ICD_DIR=$KZ/projs/code/csci645_ops/nvidia_580.159.03
ISAAC=$KZ/envs/csci645proj/bin/python
test -x "$ISAAC"
R="$X"
echo "[gpu] utc=$(date -u +%FT%TZ)"
"$PY" "$T/scripts/v3_jobs.py" run --manifest "$T/results/v5/jobs/verification_a.json" --repo "$EA" --runs-root "$R" --isaac-python "$ISAAC" --task-timeout-s 3600; echo "[gpu] a rc=$?"
"$PY" "$T/scripts/v3_jobs.py" run --manifest "$T/results/v5/jobs/verification.json" --repo "$EB" --runs-root "$R" --isaac-python "$ISAAC" --dry-run --only replay60_geometry_best,replay60_slip_robust_history_s111,reload_slip_robust_ff,reload_slip_robust_history,reload_slip_robust_repeat,resume_check_train; echo "[gpu] dry rc=$?"
"$PY" "$T/scripts/v3_jobs.py" run --manifest "$T/results/v5/jobs/verification.json" --repo "$EB" --runs-root "$R" --isaac-python "$ISAAC" --task-timeout-s 3600; echo "[gpu] b rc=$?"
"$PY" -I "$T/scripts/v5_verification.py" compare --x "$R" --output "$V5_WORK/fresh_gpu.json"; echo "[gpu] compare rc=$?"
sha256sum "$X/formal/train/slip_robust_history_s111/checkpoints/latest.pt"
grep -A3 "\"member\": \"formal/train/slip_robust_history_s111/checkpoints/latest.pt\"" "$B/checkpoints.json"
echo "[gpu] utc=$(date -u +%FT%TZ) done"
