#!/usr/bin/env bash
# Final v2 evaluation of one matrix with the clean experiment-v2 clone. Usage: final_eval_job.sh MATRIX(repo-rel or abs) NAME
set -uo pipefail
. $(dirname $0)/common.sh
EXP2=$KZ/projs/code/csci645-project-v2exp
git -C $EXP2 describe --tags --exact-match | grep -qx experiment-v2 || { echo "v2 clone not at experiment-v2"; exit 9; }
require_clean $EXP2
export REPO=$EXP2
bash $GR scripts/eval_matrix.py --matrix $1 --output $V2/final/eval/$2
echo "FINAL_EVAL rc=$?"
