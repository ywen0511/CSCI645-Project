#!/usr/bin/env bash
# Submit a self-terminating 1-GPU job on the configured LSF host. Usage: submit.sh NAME WALL(HH:MM) SCRIPT [args...]
[ -n "${LSF_PROFILE:-}" ] && . $LSF_PROFILE
set -euo pipefail
NAME=$1; WALL=$2; shift 2
LOGS=${CSCI645_WORK:?}/runs/csci645-project/v2/logs
mkdir -p $LOGS
bsub -q ${LSF_QUEUE:?} ${LSF_HOST:+-m $LSF_HOST} -gpu "num=1:mode=shared:j_exclusive=yes" -n 8 -W "$WALL" \
  -J "c645v2_${NAME}" -o "$LOGS/${NAME}.%J.log" bash "$@"
