#!/usr/bin/env bash
# Run one Python command of the experiment checkout inside an Isaac Lab v3.0.0 environment.
#   isaac_run.sh ISAAC_PYTHON <python args...>      (cwd and $REPO: the experiment checkout)
# Optional environment:
#   CLOSEOUT_VK_ICD_DIR  folder with a user-space NVIDIA Vulkan ICD (nvidia_icd.json + lib/) for nodes without a
#                        system Vulkan driver; it is NOT distributed with this project (NVIDIA license)
#   CLOSEOUT_NODE_TMP    node-local scratch for Kit/CUDA/matplotlib caches (default ${TMPDIR:-/tmp}/csci645_$USER)
set -uo pipefail
PY=${1:?usage: isaac_run.sh ISAAC_PYTHON <args...>}; shift
REPO=${REPO:-$PWD}
T=${CLOSEOUT_NODE_TMP:-${TMPDIR:-/tmp}/csci645_${USER:-user}}
mkdir -p "$T/home" "$T/cuda" "$T/mpl" "$T/xdg"
export HOME=$T/home XDG_CACHE_HOME=$T/xdg CUDA_CACHE_PATH=$T/cuda MPLCONFIGDIR=$T/mpl
export OMNI_KIT_ACCEPT_EULA=YES ACCEPT_EULA=Y PRIVACY_CONSENT=Y
if [ -n "${CLOSEOUT_VK_ICD_DIR:-}" ]; then
  export VK_ICD_FILENAMES=$CLOSEOUT_VK_ICD_DIR/nvidia_icd.json
  export LD_LIBRARY_PATH=$CLOSEOUT_VK_ICD_DIR/lib:${LD_LIBRARY_PATH:-}
fi
export PYTHONPATH=$REPO/src:${PYTHONPATH:-}
export PYTHONUNBUFFERED=1 TORCHINDUCTOR_COMPILE_THREADS=1 OMP_NUM_THREADS=${OMP_NUM_THREADS:-8}
export PATH=$(dirname "$PY"):$PATH
cd "$REPO"
echo "[isaac_run] utc=$(date -u +%FT%TZ) CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-unset} repo=$(git -C "$REPO" rev-parse HEAD 2>/dev/null)"
nvidia-smi --query-gpu=index,name,driver_version,memory.used,memory.total --format=csv,noheader 2>/dev/null
exec "$PY" "$@"
