#!/usr/bin/env bash
# Final v2 run: train (frozen protocol, clean experiment-v2 clone; resumes from latest.pt) + validation of
# the five v2 candidates. Usage: final_train_job.sh METHOD SEED
set -uo pipefail
. $(dirname $0)/common.sh
EXP2=$KZ/projs/code/csci645-project-v2exp
git -C $EXP2 describe --tags --exact-match | grep -qx experiment-v2 || { echo "v2 clone not at experiment-v2"; exit 9; }
require_clean $EXP2
export REPO=$EXP2
M=$1; S=$2; RID=${M}_seed${S}
P=configs/v2/frozen/protocol.json
OUT=$V2/final/train/$RID
VAL=$V2/final/validation/$RID
mkdir -p $VAL
if [ -f $OUT/DONE.json ]; then echo "training already complete";
elif [ -f $OUT/checkpoints/latest.pt ]; then
  bash $GR scripts/train.py --method $M --seed $S --protocol $P --run-type final --output $OUT --resume $OUT/checkpoints/latest.pt || exit 1
else
  bash $GR scripts/train.py --method $M --seed $S --protocol $P --run-type final --output $OUT || exit 1
fi
cd $EXP2
$PY scripts/make_ckpt_matrix.py --run-dir $OUT --method $M --seed $S --suite configs/v2/suites/validation.jsonl \
  --protocol $P --tags v2_candidates --name val_$RID --num-envs 400 --output $VAL/matrix.json || exit 2
bash $GR scripts/eval_matrix.py --matrix $VAL/matrix.json --output $VAL || exit 3
echo FINAL_TRAIN_DONE $RID
