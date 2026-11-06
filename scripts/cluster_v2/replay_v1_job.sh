#!/usr/bin/env bash
# Stage 1: separate-process replay of archived v1 checkpoints with the clean experiment-v1 source,
# on the predeclared 23-case sample, at batch sizes 23 and 1, with traces.
set -uo pipefail
. $(dirname $0)/common.sh
git -C $EXP1 describe --tags --exact-match | grep -qx experiment-v1 || { echo "exp clone not at experiment-v1"; exit 9; }
require_clean $EXP1
export REPO=$EXP1
S=$V2/audit/v1_replay_sample.jsonl
TR=$(python3 -c "import json;print(','.join(json.loads(l)['case_id'] for l in open('$S')))")
for B in 23 1; do
  O=$V2/audit/replay_b$B
  mkdir -p $O
  for M in nominal geometry; do
    bash $GR scripts/evaluate.py --method $M --suite $S --run-id $M --output $O --num-envs $B --trace-cases $TR \
      --protocol configs/frozen/protocol.json > $O/$M.log 2>&1; echo "$B $M rc=$?"
  done
  for RID in residual_seed11 residual_seed22 residual_seed33 combined_seed11 combined_seed22 combined_seed33 \
             combined_no_phase_seed11 combined_no_phase_seed22 combined_no_phase_seed33; do
    M=${RID%_seed*}; SD=${RID##*_seed}
    SEL=$(python3 -c "import json;print([r for r in json.load(open('$V2/v1_download/checkpoints.json')) if r['run_id']=='$RID'][0]['selected_checkpoint'])")
    CKS="$V1CK/$RID/checkpoints/$SEL.pt"
    [ "$SEL" != final ] && CKS="$CKS $V1CK/$RID/checkpoints/final.pt"
    bash $GR scripts/evaluate.py --method $M --training-seed $SD --checkpoint $CKS --suite $S --run-id $RID \
      --output $O --num-envs $B --trace-cases $TR --protocol configs/frozen/protocol.json > $O/$RID.log 2>&1
    echo "$B $RID rc=$? ($SEL + final)"
  done
done
echo REPLAY_V1_DONE
