#!/usr/bin/env bash
# Submit one self-terminating closeout job to an LSF scheduler (the only scheduler used in this study).
#   lsf_submit.sh NAME WALL(HH:MM) GPUS(0|1) <command...>
# Required: CLOSEOUT_LSF_QUEUE. Optional: CLOSEOUT_LSF_HOST (-m), CLOSEOUT_LSF_PROFILE (sourced first),
# CLOSEOUT_LSF_LOGS (default ./closeout_work/lsf_logs), CLOSEOUT_LSF_CORES (default 8).
# Other schedulers: run the same command (e.g. `python3 scripts/closeout.py ... repeatability --shard I/N`)
# under your scheduler's equivalent; the driver itself has no scheduler dependency.
[ -n "${CLOSEOUT_LSF_PROFILE:-}" ] && . "$CLOSEOUT_LSF_PROFILE"
set -euo pipefail
NAME=$1; WALL=$2; GPUS=$3; shift 3
LOGS=${CLOSEOUT_LSF_LOGS:-$PWD/closeout_work/lsf_logs}
mkdir -p "$LOGS"
GPU_ARGS=()
[ "$GPUS" != "0" ] && GPU_ARGS=(-gpu "num=$GPUS:mode=shared:j_exclusive=yes")
bsub -q "${CLOSEOUT_LSF_QUEUE:?set CLOSEOUT_LSF_QUEUE}" ${CLOSEOUT_LSF_HOST:+-m "$CLOSEOUT_LSF_HOST"} "${GPU_ARGS[@]}" \
  -n "${CLOSEOUT_LSF_CORES:-8}" -W "$WALL" -J "c645co_$NAME" -o "$LOGS/$NAME.%J.log" "$@"
