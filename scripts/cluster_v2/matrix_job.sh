#!/usr/bin/env bash
# Run one evaluation matrix with the v2 source. Usage: matrix_job.sh MATRIX_JSON(repo-relative) OUTDIR [extra eval_matrix args]
set -uo pipefail
. $(dirname $0)/common.sh
require_clean $DEV
export REPO=$DEV
MX=$1; OUT=$2; shift 2
bash $GR scripts/eval_matrix.py --matrix $MX --output $OUT --checkpoint-root $V1CK "$@"
echo "MATRIX_JOB rc=$?"
