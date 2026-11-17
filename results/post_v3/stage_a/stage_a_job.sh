#!/usr/bin/env bash
# Stage A: execute docs/v3/REPRODUCE.md sections 1-4 verbatim (tooling 4d7beb3), then repeat the runner.
KZ=<work-root>
export TMPDIR=$KZ/runs/csci645-project/post_v3/stageA
mkdir -p "$TMPDIR"
export PATH=$KZ/envs/cpython-3.13.9/bin:$PATH
export CLOSEOUT_VK_ICD_DIR=$KZ/projs/code/csci645_ops/nvidia_580.159.03
unset GITHUB_TOKEN GH_TOKEN
export GIT_CONFIG_GLOBAL=/dev/null GIT_TERMINAL_PROMPT=0 PIP_DISABLE_PIP_VERSION_CHECK=1
export PS4='+ [$(date -u +%H:%M:%S)] '
trap 'echo "STAGEA_FAILED line $LINENO rc $?"' ERR
set -x

echo '=== REPRODUCE section: 1. Create three distinct checkouts (CPU) ==='
set -eu
V3_WORK=$(mktemp -d "${TMPDIR:-/tmp}/csci645-reproduce.XXXXXX")
T="$V3_WORK/tooling"
D="$V3_WORK/delivery"
E="$V3_WORK/experiment"
B="$V3_WORK/release"
X="$V3_WORK/extracted"
R="$V3_WORK/replay"
G="$V3_WORK/regenerated"
REPO_URL=https://github.com/ywen0511/CSCI645-Project.git
git clone --branch study/v3-observation-robustness "$REPO_URL" "$T"
git -C "$T" rev-parse HEAD > "$V3_WORK/tooling_commit.txt"
git clone --branch v3.0.0 "$REPO_URL" "$D"
git clone --branch experiment-v3 "$REPO_URL" "$E"
test "$(git -C "$E" rev-parse HEAD)" = 3811f5da5ef55638f95f7306e449609877f546df
test "$(git -C "$D" rev-parse HEAD)" = ebfa328b17103c32ae19c13f0a6408ebc55a6459

echo '=== REPRODUCE section: 2. Download, verify and regenerate (CPU) ==='
python3.13 -m venv "$V3_WORK/analysis-env"
PY="$V3_WORK/analysis-env/bin/python"
"$PY" -m pip install -r "$D/configs/closeout/requirements-analysis.txt"
"$PY" -I "$T/scripts/v3_download.py" --tag v3.0.0 --output "$B"
"$PY" -I "$D/scripts/v3_verify.py" --bundle "$B" --extract "$X" --output "$V3_WORK/bundle_verify.json"
"$PY" "$D/scripts/v3_regen.py" --runs "$X" --work "$G"
"$PY" "$T/scripts/v3_rebuild_suites.py" --experiment-repo "$E" --check
"$PY" "$T/scripts/v3_rebuild_suites.py" --experiment-repo "$E" --output "$V3_WORK/rebuilt-suites"

echo '=== REPRODUCE section: 3. Small complete replay (remote GPU only) ==='
ISAAC=$ISAAC  # set per section 3
test -x "$ISAAC"
mkdir -p "$R/formal"
ln -s "$X/formal/train" "$R/formal/train"
ln -s "$X/final" "$R/final"
"$PY" "$T/scripts/v3_jobs.py" run --manifest "$T/results/v3/jobs/verification.json"   --repo "$E" --runs-root "$R" --isaac-python "$ISAAC"   --only replay65_geometry_common --dry-run
"$PY" "$T/scripts/v3_jobs.py" run --manifest "$T/results/v3/jobs/verification.json"   --repo "$E" --runs-root "$R" --isaac-python "$ISAAC"   --only replay65_geometry_common --task-timeout-s 3600

echo '=== REPRODUCE section: 4. All replay, reload and resume checks (remote GPU) ==='
"$PY" - "$X/formal/train/combined_robust_history_s11/checkpoints/latest.pt" > "$V3_WORK/resume-input.sha256" <<'HASH'
import hashlib, pathlib, sys
print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())
HASH
"$PY" "$T/scripts/v3_jobs.py" run --manifest "$T/results/v3/jobs/verification.json"   --repo "$E" --runs-root "$R" --isaac-python "$ISAAC" --task-timeout-s 3600
"$PY" "$T/scripts/v3_fresh_compare.py" --x "$R" --output "$V3_WORK/fresh_gpu.json"
"$PY" - "$V3_WORK/fresh_gpu.json" "$X/formal/train/combined_robust_history_s11/checkpoints/latest.pt"   "$V3_WORK/resume-input.sha256" <<'CHECK'
import hashlib, json, pathlib, sys
r = json.loads(pathlib.Path(sys.argv[1]).read_text())
assert len(r['replay65']) == 7 and all(x['cases'] == 65 for x in r['replay65'])
assert len(r['reload']) == 4 and all(x['cases'] == 13 for x in r['reload'])
assert r['summary']['mismatches'] == 0 and r['resume']['ok']
for x in r['replay65'] + r['reload']:
    assert not x['missing_in_final'] and x['invalid_resets'] == 0
    assert x['terminal_equal'] == x['success_equal'] == x['cases']
    assert x['observation_error_equal'] and x['checkpoint_sha256_equal']
assert hashlib.sha256(pathlib.Path(sys.argv[2]).read_bytes()).hexdigest() == pathlib.Path(sys.argv[3]).read_text().strip()
CHECK

echo '=== REPRODUCE section 4 note: repeat the runner once ==='
cp -r "$R/ledger" "$V3_WORK/ledger_after_first"
rc=0; "$PY" "$T/scripts/v3_jobs.py" run --manifest "$T/results/v3/jobs/verification.json"   --repo "$E" --runs-root "$R" --isaac-python "$ISAAC" --task-timeout-s 3600 > "$V3_WORK/repeat_run.log" 2>&1 || rc=$?
echo "repeat_rc=$rc"
"$PY" -c 'import sys,json;print(json.dumps({"python":sys.version}))'
"$ISAAC" -c 'import sys;print(sys.version)'
echo "V3_WORK=$V3_WORK"
echo STAGEA_DONE
