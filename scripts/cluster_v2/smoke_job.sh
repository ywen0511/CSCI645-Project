#!/usr/bin/env bash
# Smoke: v2 training pipeline with resume (3 + 3 iterations), zero-mean init check, evaluation of step 0 / final.
set -uo pipefail
. $(dirname $0)/common.sh
require_clean $DEV
export REPO=$DEV
PROT=configs/v2/pilot/P2_zero_mean_init.json
OUT=$V2/pilot/train/smoke_combined_P2_s102
EV=$V2/pilot/eval/smoke_combined_P2_s102
mkdir -p $EV
bash $GR scripts/train.py --method combined --seed 102 --protocol $PROT --run-type smoke --transitions 98304 \
  --checkpoint-every 98304 --output $OUT || exit 1
bash $GR scripts/train.py --method combined --seed 102 --protocol $PROT --run-type smoke --transitions 196608 \
  --checkpoint-every 98304 --output $OUT --resume $OUT/checkpoints/latest.pt || exit 2
cd $DEV
$PY scripts/make_ckpt_matrix.py --run-dir $OUT --method combined --seed 102 --suite configs/v2/suites/development.jsonl \
  --protocol $PROT --tags all --name smoke --output $EV/matrix.json || exit 3
python3 - $EV/matrix.json <<'PY'
import json, sys
m = json.load(open(sys.argv[1]))
m["entries"].append({"id": "geometry_1p5cm_zero", "method": "geometry"})
json.dump(m, open(sys.argv[1], "w"), indent=1)
PY
bash $GR scripts/eval_matrix.py --matrix $EV/matrix.json --output $EV/development || exit 4
echo SMOKE_DONE
