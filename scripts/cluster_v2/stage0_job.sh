#!/usr/bin/env bash
# Stage 0: simulator smoke test + negative controls with the v2 source (defaults = v1 behaviour).
set -uo pipefail
. $(dirname $0)/common.sh
require_clean $DEV
export REPO=$DEV
O=$V2/stage0
run() { echo "== $1"; bash $GR scripts/run_scripted.py "${@:2}" --output $O/$1 > $O/$1.log 2>&1; echo "rc=$?"; grep -A12 '"clean"' $O/$1/summary.json | head -14; }
mkdir -p $O
run nominal_clean --method nominal --num-envs 20 --episodes 20 --trace 1
run geometry_clean --method geometry --num-envs 20 --episodes 20 --trace 1
run neg_no_receiver --method nominal --num-envs 20 --episodes 20 --trace 1 --set 'negative_control="no_receiver"'
run neg_giver_holds --method nominal --num-envs 20 --episodes 20 --trace 1 --set 'negative_control="giver_holds"'
run neg_table_support --method nominal --num-envs 20 --episodes 20 --trace 2 --set 'negative_control="table_support"' --set 'table_size_override=[0.06,0.30,0.20]'
run neg_giver_holds_geometry --method geometry --num-envs 20 --episodes 20 --trace 1 --set 'negative_control="giver_holds"'
echo STAGE0_DONE
