#!/usr/bin/env bash
# V5 public verification, cluster part 1 (login node, CPU): REPRODUCE.md sections 1-2 up to extraction.
set -eu
KZ=<WORK>
export PATH=$KZ/envs/cpython-3.13.9/bin:$PATH TMPDIR=$KZ/tmp
mkdir -p $TMPDIR
echo "[prep] utc=$(date -u +%FT%TZ)"
V5_WORK=$(mktemp -d "${TMPDIR:-/tmp}/csci645-v5-reproduce.XXXXXX"); echo "$V5_WORK" > $KZ/runs/csci645-project/v5_fresh_work.txt
T="$V5_WORK/delivery"; EA="$V5_WORK/exp-a"; EB="$V5_WORK/exp-b"; B="$V5_WORK/release"; X="$V5_WORK/extracted"
REPO_URL=https://github.com/ywen0511/CSCI645-Project.git
export GIT_TERMINAL_PROMPT=0
git -c credential.helper= clone -q --branch v5.0.0 "$REPO_URL" "$T"; git -C "$T" fetch -q --tags
git -c credential.helper= clone -q --branch experiment-v5a "$REPO_URL" "$EA"
git -c credential.helper= clone -q --branch experiment-v5b "$REPO_URL" "$EB"
test "$(git -C "$EA" rev-parse HEAD)" = 13cda3af2699f0ebfdd50affb4d27fb6dde877e8
test "$(git -C "$EB" rev-parse HEAD)" = db62bd1dbb3bb077ad4b67f3b3cd934e677db522
echo "[prep] T=$(git -C $T rev-parse HEAD) clones ok"
python3.13 -m venv "$V5_WORK/analysis-env"; PY="$V5_WORK/analysis-env/bin/python"
"$PY" -m pip install -q -r "$T/configs/closeout/requirements-analysis.txt"
env -u GH_TOKEN -u GITHUB_TOKEN "$PY" -I "$T/scripts/v3_download.py" --tag v5.0.0 --output "$B" | tail -1
(cd "$B" && sha256sum -c SHA256SUMS | awk "{print \$NF}" | sort | uniq -c)
"$PY" -I "$T/scripts/v5_verify.py" --bundle "$B" --extract "$X" --output "$V5_WORK/bundle_verify.json" > "$V5_WORK/bundle_verify.log" 2>&1; echo "[prep] verify rc=$?"
echo "[prep] utc=$(date -u +%FT%TZ) done"
