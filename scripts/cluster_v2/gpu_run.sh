#!/usr/bin/env bash
# Run a project command inside the csci645proj env on an LSF GPU allocation.
# Usage (from bsub): gpu_run.sh <python-args...>   e.g. gpu_run.sh scripts/inspect_scene.py --headless
set -uo pipefail
KZ=${CSCI645_WORK:?set CSCI645_WORK to the work root (envs/, projs/code/, runs/)}
OPS=${CSCI645_OPS:-$KZ/projs/code/csci645_ops}
REPO=${REPO:-$KZ/projs/code/csci645-project}
ENV=$KZ/envs/csci645proj
NV=$OPS/nvidia_580.159.03
NODE_TMP=${TMPDIR:-/tmp}/c645_$USER
mkdir -p $NODE_TMP/home $NODE_TMP/cuda $NODE_TMP/mpl $NODE_TMP/xdg
export HOME=$NODE_TMP/home            # Kit/Omniverse caches + logs go node-local, not to the 10 GB NFS home
export XDG_CACHE_HOME=$NODE_TMP/xdg
export CUDA_CACHE_PATH=$NODE_TMP/cuda
export MPLCONFIGDIR=$NODE_TMP/mpl
export OMNI_KIT_ACCEPT_EULA=YES ACCEPT_EULA=Y PRIVACY_CONSENT=Y
export VK_ICD_FILENAMES=$NV/nvidia_icd.json
export LD_LIBRARY_PATH=$NV/lib:${LD_LIBRARY_PATH:-}
export PYTHONPATH=$REPO/src:${PYTHONPATH:-}
export PYTHONUNBUFFERED=1 TORCHINDUCTOR_COMPILE_THREADS=1 OMP_NUM_THREADS=${OMP_NUM_THREADS:-8}
export PATH=$ENV/bin:$PATH
cd $REPO
echo "[gpu_run] host=$(hostname) date=$(date -u +%FT%TZ) CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-unset} LSB_JOBID=${LSB_JOBID:-}"
nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv,noheader
git -C $REPO rev-parse HEAD 2>/dev/null | sed 's/^/[gpu_run] repo HEAD /'
exec $ENV/bin/python "$@"
