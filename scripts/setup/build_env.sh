#!/usr/bin/env bash
# Build the isolated Python 3.12 conda environment for this project:
#   Isaac Lab v3.0.0 (source checkout) + Isaac Sim 6.2.0.0 (pip) + RSL-RL 5.5.1.
#
# Usage:
#   scripts/setup/build_env.sh ENV_PREFIX ISAACLAB_DIR [CONDA_EXE]
#
#   ENV_PREFIX    directory for the new conda env (must not exist yet)
#   ISAACLAB_DIR  Isaac Lab checkout at tag v3.0.0
#                 (git clone --branch v3.0.0 --depth 1 https://github.com/isaac-sim/IsaacLab.git)
#   CONDA_EXE     conda/mamba executable (default: conda on PATH)
#
# Follows the "isaaclab.sh installer (legacy) / conda environment" route of
# docs/source/isaaclab/installation.rst at v3.0.0 with the `isaacsim` and
# `rl[rsl-rl]` selectors. Set PIP_CACHE_DIR to a large disk; Isaac Sim wheels are big.
set -euo pipefail
ENV_PREFIX=${1:?ENV_PREFIX}
ISAACLAB_DIR=${2:?ISAACLAB_DIR}
CONDA_EXE=${3:-conda}

test "$(git -C "$ISAACLAB_DIR" describe --tags --exact-match 2>/dev/null)" = "v3.0.0" \
  || { echo "ISAACLAB_DIR is not at tag v3.0.0" >&2; exit 2; }

if [ ! -x "$ENV_PREFIX/bin/python" ]; then
  "$CONDA_EXE" create -y -p "$ENV_PREFIX" python=3.12 pip
fi
export CONDA_PREFIX="$ENV_PREFIX"
export PATH="$ENV_PREFIX/bin:$PATH"
unset VIRTUAL_ENV
python -m pip install --upgrade pip
python -m pip install uv
# The installer runs `sudo apt-get install cmake build-essential` unless cmake is on PATH.
# A user-space cmake avoids needing root (build-essential/gcc must already exist).
python -m pip install cmake
hash -r

cd "$ISAACLAB_DIR"
export OMNI_KIT_ACCEPT_EULA=YES
./isaaclab.sh -i 'rl[rsl-rl],isaacsim'
# Video encoding for record_video.py.
python -m pip install "moviepy>=1.0.3,<2.0.0.dev0" imageio imageio-ffmpeg
python -m pip freeze > "$ENV_PREFIX/pip-freeze.txt"
python - <<'PY'
import importlib.metadata as md
for p in ["isaacsim", "isaaclab", "isaaclab-physx", "isaaclab-rl", "isaaclab-tasks",
          "rsl-rl-lib", "torch", "warp-lang", "numpy", "gymnasium"]:
    try:
        print(f"{p}=={md.version(p)}")
    except md.PackageNotFoundError:
        print(f"{p}: NOT INSTALLED")
PY
echo BUILD_ENV_DONE
