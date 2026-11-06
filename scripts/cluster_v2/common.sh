# Sourced by v2 job scripts.
KZ=${CSCI645_WORK:?set CSCI645_WORK to the work root (envs/, projs/code/, runs/)}
V2=$KZ/runs/csci645-project/v2
DEV=$KZ/projs/code/csci645-project
EXP1=$KZ/projs/code/csci645-project-exp
GR=$(cd $(dirname ${BASH_SOURCE[0]}) && pwd)/gpu_run.sh
PY=$KZ/envs/csci645proj/bin/python
V1CK=$V2/v1_download/extracted
mkdir -p $V2/logs
require_clean() {  # require_clean REPO -> refuse dirty source
  test -z "$(git -C $1 status --porcelain --untracked-files=no)" || { echo "source $1 is dirty"; exit 9; }
  echo "[src] $1 @ $(git -C $1 rev-parse HEAD)"
}
