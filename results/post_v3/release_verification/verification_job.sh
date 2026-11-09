#!/usr/bin/env bash
# Stage A step 8: public verification of release v3.0.1 from a new empty directory (no original run outputs).
KZ=<work-root>
export TMPDIR=$KZ/runs/csci645-project/post_v3/fresh301
mkdir -p "$TMPDIR"
export PATH=$KZ/envs/cpython-3.13.9/bin:$PATH
export CLOSEOUT_VK_ICD_DIR=$KZ/projs/code/csci645_ops/nvidia_580.159.03
unset GITHUB_TOKEN GH_TOKEN
export GIT_CONFIG_GLOBAL=/dev/null GIT_TERMINAL_PROMPT=0 PIP_DISABLE_PIP_VERSION_CHECK=1
export PS4='+ [$(date -u +%H:%M:%S)] '
trap 'echo "FRESH301_FAILED line $LINENO rc $?"' ERR
set -eux
V3_WORK=$(mktemp -d "$TMPDIR/v301.XXXXXX")
T="$V3_WORK/tooling"; D="$V3_WORK/delivery"; E="$V3_WORK/experiment"
B1="$V3_WORK/release-v3.0.1"; B="$V3_WORK/release"; X="$V3_WORK/extracted"; G="$V3_WORK/regenerated"; R="$V3_WORK/replay"
REPO_URL=https://github.com/ywen0511/CSCI645-Project.git
git clone --branch maintenance-v3.0.1 "$REPO_URL" "$T"
git clone --branch v3.0.0 "$REPO_URL" "$D"
git clone --branch experiment-v3 "$REPO_URL" "$E"
test "$(git -C "$T" rev-parse HEAD)" = c85fded58f776c117368dc02be24405912593e38
test "$(git -C "$T" rev-parse v3.0.1^{commit})" = c85fded58f776c117368dc02be24405912593e38
test "$(git -C "$E" rev-parse HEAD)" = 3811f5da5ef55638f95f7306e449609877f546df
test "$(git -C "$D" rev-parse HEAD)" = ebfa328b17103c32ae19c13f0a6408ebc55a6459
python3.13 -m venv "$V3_WORK/analysis-env"
PY="$V3_WORK/analysis-env/bin/python"
"$PY" -m pip install -q -r "$D/configs/closeout/requirements-analysis.txt"
"$PY" -I "$T/scripts/v3_download.py" --tag v3.0.1 --output "$B1"
(cd "$B1" && sha256sum -c SHA256SUMS)
"$PY" -I "$T/scripts/post_v3_verify_release.py" --bundle "$B1" --original-out "$B" \
    --expect-tooling-sha c85fded58f776c117368dc02be24405912593e38 --output "$V3_WORK/maintenance_release_verify.json"
(cd "$B" && sha256sum -c SHA256SUMS)
"$PY" -I "$D/scripts/v3_verify.py" --bundle "$B" --extract "$X" --output "$V3_WORK/bundle_verify.json"
"$PY" "$D/scripts/v3_regen.py" --runs "$X" --work "$G"
"$PY" "$T/scripts/v3_rebuild_suites.py" --experiment-repo "$E" --check
for f in "$G"/figures/*.png; do cmp "$f" "$D/results/v3/figures/$(basename $f)"; done
# revised quickstart, section 3: small complete replay from the v3.0.1-extracted checkpoints
ISAAC=$KZ/envs/csci645proj/bin/python
mkdir -p "$R/formal"
ln -s "$X/formal/train" "$R/formal/train"
ln -s "$X/final" "$R/final"
"$PY" "$T/scripts/v3_jobs.py" run --manifest "$T/results/v3/jobs/verification.json" --repo "$E" --runs-root "$R" \
    --isaac-python "$ISAAC" --only replay65_geometry_common,reload_combined_robust_ff --task-timeout-s 3600
"$PY" - "$R" "$X" "$T" <<'PYX'
import json, sys
from pathlib import Path
R, X, T = map(Path, sys.argv[1:])
idx = {(e["family"], e["role"], e["seed"]): e["records"] for e in json.loads((T / "configs/v3/final_matrix_index.json").read_text())["entries"]}
def jl(p): return {json.loads(l)["case_id"]: json.loads(l) for l in p.read_text().splitlines() if l.strip()}
new = jl(R / "replay65/geometry_common/geometry_common.jsonl"); old = jl(X / idx[("geometry_common", "baseline", None)])
sub = [json.loads(l)["case_id"] for l in (T / "configs/v3/suites/final_subset65.jsonl").read_text().splitlines() if l.strip()]
assert sorted(new) == sorted(sub) and all(new[c]["terminal_reason"] == old[c]["terminal_reason"] for c in new)
rl = jl(R / "reload/combined_robust_ff/combined_robust_ff_s11__selected.jsonl"); ro = jl(X / idx[("combined_robust_ff", "selected", 11)])
assert len(rl) == 13 and all(rl[c]["terminal_reason"] == ro[c]["terminal_reason"] for c in rl)
assert all(r["checkpoint_sha256"] == ro[c]["checkpoint_sha256"] for c, r in rl.items())
print(json.dumps({"replay65_geometry_common": len(new), "reload_combined_robust_ff": len(rl), "all_equal": True}))
PYX
echo "V3_WORK=$V3_WORK"
echo FRESH301_DONE
