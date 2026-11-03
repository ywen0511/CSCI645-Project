# Remote setup (verified)

These are the exact steps used for every experiment in this repository. Paths are placeholders; set them
for your machine. No credentials are needed except GitHub access for publishing.

## Verified platform

| Item | Value |
|---|---|
| OS | Ubuntu 24.04.5 LTS, x86_64, glibc 2.39 |
| GPU | NVIDIA A100-SXM4-40GB (one GPU per run) |
| Driver | 580.159.03 (open kernel module) |
| Python | 3.12 (conda environment) |
| Isaac Sim | 6.2.0.0 (pip wheels `isaacsim[all,extscache]==6.2.0.0`) |
| Isaac Lab | v3.0.0 source checkout (commit e3f7d9ff1f5d7f8280de3ece9000b7117f66bcf4; package `isaaclab` 28.0.0) |
| Physics backend | Isaac Sim PhysX (`isaaclab_physx.physics.PhysxCfg`) for all methods |
| RL library | RSL-RL `rsl-rl-lib==5.5.1` (PPO) |
| PyTorch | 2.11.0+cu130, Warp 1.17.0, NumPy 2.5 |

A pip freeze of the environment is in `configs/frozen/env/pip-freeze.txt`.

## 1. Isaac Lab + Isaac Sim environment

```bash
export WORK=/path/to/large/disk
git clone --branch v3.0.0 --depth 1 https://github.com/isaac-sim/IsaacLab.git $WORK/IsaacLab-v3.0.0
git clone https://github.com/ywen0511/CSCI645-Project.git $WORK/CSCI645-Project
export PIP_CACHE_DIR=$WORK/pip_cache      # Isaac Sim wheels are large (~25 GB installed)
bash $WORK/CSCI645-Project/scripts/setup/build_env.sh $WORK/envs/csci645proj $WORK/IsaacLab-v3.0.0 conda
```

`build_env.sh` creates a Python 3.12 conda environment, installs a user-space `cmake` (the Isaac Lab
installer otherwise calls `sudo apt-get install cmake`), runs the documented legacy installer
`./isaaclab.sh -i 'rl[rsl-rl],isaacsim'` and adds `moviepy`/`imageio-ffmpeg` for video encoding.

## 2. Runtime environment variables

```bash
export OMNI_KIT_ACCEPT_EULA=YES ACCEPT_EULA=Y PRIVACY_CONSENT=Y   # Isaac Sim EULA (read it first)
export PYTHONPATH=$WORK/CSCI645-Project/src:$PYTHONPATH            # or: pip install -e . --no-deps
# Optional: keep Kit caches off a small or network home directory
export HOME=/local/scratch/home XDG_CACHE_HOME=/local/scratch/xdg CUDA_CACHE_PATH=/local/scratch/cuda
```

Isaac Lab 3.0 runs headless by default (no `--headless` flag). Isaac Sim needs a Vulkan driver even
headless. On GPU nodes that ship only NVIDIA compute libraries (no `libGLX_nvidia`/`nvidia_icd.json`),
extract the user-space graphics libraries from the *matching* driver installer without installing it:

```bash
V=$(sed -n 's/.*Kernel Module for x86_64 *\([0-9.]*\).*/\1/p' /proc/driver/nvidia/version)
wget https://us.download.nvidia.com/tesla/$V/NVIDIA-Linux-x86_64-$V.run
sh NVIDIA-Linux-x86_64-$V.run -x --target nv && mkdir -p nvlib
cp nv/libGLX_nvidia.so.$V nv/libnvidia-glcore.so.$V nv/libnvidia-glvkspirv.so.$V nv/libnvidia-gpucomp.so.$V \
   nv/libnvidia-tls.so.$V nv/libEGL_nvidia.so.$V nv/libnvidia-eglcore.so.$V nv/libnvidia-glsi.so.$V \
   nv/libnvidia-rtcore.so.$V nv/libnvoptix.so.$V nvlib/
(cd nvlib && for f in *.so.$V; do ln -sf $f ${f%.$V}.0; ln -sf $f ${f%.$V}.1; ln -sf $f ${f%.$V}; done)
python3 -c "import json;j=json.load(open('nv/nvidia_icd.json'));j['ICD']['library_path']='$PWD/nvlib/libGLX_nvidia.so.0';json.dump(j,open('nvidia_icd.json','w'))"
export VK_ICD_FILENAMES=$PWD/nvidia_icd.json LD_LIBRARY_PATH=$PWD/nvlib:$LD_LIBRARY_PATH
```

## 3. Assets

The Franka Panda asset (`Robots/FrankaEmika/franka_panda.usda`, PhysX payload, primitive colliders) is
resolved by Isaac Lab from the official NVIDIA asset server (`ISAACLAB_NUCLEUS_DIR`) at first use; no
account is needed. The object and table are generated cuboids. No external dataset is used.

## 4. Checks

```bash
python3 scripts/check_handoff.py
python3 -B -m unittest discover -s tests -v          # pure logic (+ registration if Isaac Lab is present)
python scripts/doctor.py --output outputs/preflight.json
python scripts/inspect_scene.py --output outputs/inspect_scene.json
```

The exact experiment commands are in `docs/REPRODUCE.md`.
