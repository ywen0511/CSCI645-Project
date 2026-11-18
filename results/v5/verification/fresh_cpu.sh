#!/usr/bin/env bash
# V5 public verification, CPU part: docs/v5/REPRODUCE.md sections 1-2 verbatim, plus the CPU test suite in a fresh
# clone of the tag. python3.13 = the local CPython 3.13.9 interpreter.
set -eu
export PATH=$HOME/miniconda3/bin:$PATH
echo "[fresh] utc=$(date -u +%FT%TZ) python3.13=$(python3.13 --version)"
V5_WORK=$(mktemp -d "${TMPDIR:-/tmp}/csci645-v5-reproduce.XXXXXX")
echo "[fresh] work=<V5_WORK>"
T="$V5_WORK/delivery"; EA="$V5_WORK/exp-a"; EB="$V5_WORK/exp-b"
B="$V5_WORK/release"; X="$V5_WORK/extracted"; G="$V5_WORK/regenerated"
REPO_URL=https://github.com/ywen0511/CSCI645-Project.git
export GIT_TERMINAL_PROMPT=0
git -c credential.helper= clone -q --branch v5.0.0 "$REPO_URL" "$T"
git -C "$T" fetch -q --tags
git -c credential.helper= clone -q --branch experiment-v5a "$REPO_URL" "$EA"
git -c credential.helper= clone -q --branch experiment-v5b "$REPO_URL" "$EB"
test "$(git -C "$EA" rev-parse HEAD)" = 13cda3af2699f0ebfdd50affb4d27fb6dde877e8 && echo "[fresh] EA ok"
test "$(git -C "$EB" rev-parse HEAD)" = db62bd1dbb3bb077ad4b67f3b3cd934e677db522 && echo "[fresh] EB ok"
echo "[fresh] T=$(git -C "$T" rev-parse HEAD)"
python3.13 -m venv "$V5_WORK/analysis-env"
PY="$V5_WORK/analysis-env/bin/python"
"$PY" -m pip install -q -r "$T/configs/closeout/requirements-analysis.txt"
env -u GH_TOKEN -u GITHUB_TOKEN "$PY" -I "$T/scripts/v3_download.py" --tag v5.0.0 --output "$B" | tail -2
(cd "$B" && sha256sum -c SHA256SUMS | awk '{print $NF}' | sort | uniq -c)
"$PY" -I "$T/scripts/v5_verify.py" --bundle "$B" --extract "$X" --output "$V5_WORK/bundle_verify.json" > "$V5_WORK/bundle_verify.log" 2>&1; echo "[fresh] v5_verify rc=$?"
"$PY" -I -c "import json,sys; d=json.load(open(sys.argv[1])); print('[fresh] bundle_verify ok', d['ok'], 'failures', d['failures'])" "$V5_WORK/bundle_verify.json"
mkdir "$V5_WORK/v4"
curl -fsSL -o "$V5_WORK/v4/raw-final.tar.gz" https://github.com/ywen0511/CSCI645-Project/releases/download/v4.0.0/raw-final.tar.gz
"$PY" "$T/scripts/v5_regen.py" --runs "$X" --work "$G" --v4-raw-final "$V5_WORK/v4/raw-final.tar.gz"; echo "[fresh] regen rc=$?"
# CPU tests in a fresh clone of the tag (test environment: Python 3.13 + numpy + pytest + torch CPU)
python3.13 -m venv "$V5_WORK/test-env"
"$V5_WORK/test-env/bin/pip" install -q numpy pytest torch --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple
(cd "$T" && "$V5_WORK/test-env/bin/python" -m pytest -q 2>&1 | tail -2)
echo "[fresh] utc=$(date -u +%FT%TZ) done"
echo "$V5_WORK" > "$1"
