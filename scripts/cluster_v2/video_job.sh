#!/usr/bin/env bash
# Record the v2 videos (frozen rule plan) with the clean experiment-v2 clone. Usage: video_job.sh PLAN_JSON
set -uo pipefail
. $(dirname $0)/common.sh
EXP2=$KZ/projs/code/csci645-project-v2exp
git -C $EXP2 describe --tags --exact-match | grep -qx experiment-v2 || { echo "v2 clone not at experiment-v2"; exit 9; }
require_clean $EXP2
export REPO=$EXP2
mkdir -p $V2/videos
bash $GR scripts/record_video.py --plan $1 --suite configs/v2/suites/final.jsonl --protocol configs/v2/frozen/protocol.json
echo "VIDEO_JOB rc=$?"
