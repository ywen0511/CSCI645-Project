#!/usr/bin/env bash
# Release verification on GPU: fresh clone at experiment-v2, one deterministic episode, replay of downloaded
# checkpoints (predeclared boundary sample) in new processes.
set -uo pipefail
. $(dirname $0)/common.sh
VD=$V2/verify_download
rm -rf $VD/clone && git clone -q https://github.com/ywen0511/CSCI645-Project.git $VD/clone && git -C $VD/clone checkout -q experiment-v2 || exit 2
require_clean $VD/clone
export REPO=$VD/clone
bash $GR scripts/run_scripted.py --method geometry --num-envs 1 --episodes 1 --set 'align_max=0.015' --output $VD/out/geometry_one || exit 3
bash $GR scripts/eval_matrix.py --matrix $VD/replay_matrix.json --output $VD/replay --checkpoint-root $VD/x || exit 4
echo VERIFY_DONE
