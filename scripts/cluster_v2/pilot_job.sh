#!/usr/bin/env bash
# Pilot training + development evaluation of every checkpoint.
# Usage: pilot_job.sh PROTOCOL(repo-rel) METHOD SEED TRANSITIONS RUN_ID [CKPT_EVERY]
set -uo pipefail
. $(dirname $0)/common.sh
require_clean $DEV
export REPO=$DEV
PROT=$1; M=$2; S=$3; BUD=$4; RID=$5; EVERY=${6:-1000000}
OUT=$V2/pilot/train/$RID
EV=$V2/pilot/eval/$RID
mkdir -p $OUT $EV
if [ -f $OUT/DONE.json ]; then echo "training already complete";
elif [ -f $OUT/checkpoints/latest.pt ]; then
  bash $GR scripts/train.py --method $M --seed $S --protocol $PROT --run-type pilot --transitions $BUD \
    --checkpoint-every $EVERY --output $OUT --resume $OUT/checkpoints/latest.pt || exit 1
else
  bash $GR scripts/train.py --method $M --seed $S --protocol $PROT --run-type pilot --transitions $BUD \
    --checkpoint-every $EVERY --output $OUT || exit 1
fi
cd $DEV
for SU in development development_valproxy development_feasibility; do
  $PY scripts/make_ckpt_matrix.py --run-dir $OUT --method $M --seed $S --suite configs/v2/suites/$SU.jsonl \
    --protocol $PROT --tags all --name pilot_${RID}_$SU --output $EV/matrix_$SU.json || exit 2
  bash $GR scripts/eval_matrix.py --matrix $EV/matrix_$SU.json --output $EV/$SU || exit 3
done
echo PILOT_DONE $RID
