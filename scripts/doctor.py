"""Preflight: hardware, versions, physics backend, asset access and a short simulator smoke test.

Usage:
    python scripts/doctor.py --output outputs/preflight.json

The JSON contains no credentials. GitHub capabilities are checked separately from the machine that holds
credentials (see docs/SETUP_REMOTE.md).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from isaaclab.app import add_launcher_args, launch_simulation  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", default="outputs/preflight.json")
parser.add_argument("--num-envs", type=int, default=4)
parser.add_argument("--steps", type=int, default=60)
add_launcher_args(parser)
args = parser.parse_args()


def sh(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout.strip()
    except Exception as exc:  # noqa: BLE001
        return f"unavailable: {exc}"


def main():
    from csci645_handover import runtime as rt

    report = {"utc": rt.utc_now(), "argv": sys.argv[1:]}
    report["os"] = {"platform": platform.platform(), "machine": platform.machine(),
                    "os_release": Path("/etc/os-release").read_text().splitlines()[:4] if Path("/etc/os-release").exists() else None,
                    "glibc": platform.libc_ver()}
    report["nvidia_smi"] = sh(["nvidia-smi", "--query-gpu=index,name,memory.total,driver_version", "--format=csv,noheader"])
    report["driver_version_proc"] = Path("/proc/driver/nvidia/version").read_text().splitlines()[0] if Path("/proc/driver/nvidia/version").exists() else None
    report["cpu_count"] = os.cpu_count()
    report["mem_total_gb"] = round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30, 1)
    report["disk_free_gb_cwd"] = round(shutil.disk_usage(".").free / 2**30, 1)
    report["vulkan_icd"] = os.environ.get("VK_ICD_FILENAMES") and Path(os.environ["VK_ICD_FILENAMES"]).name
    report["versions"] = rt.hardware_info()
    report["git"] = rt.git_state()
    cfg = rt.build_env_cfg("nominal", args.num_envs, args.device if getattr(args, "device", None) else "cuda:0", 0)
    report["physics"] = {"backend": type(cfg.sim.physics).__module__ + "." + type(cfg.sim.physics).__name__,
                         "physics_dt": cfg.sim.dt, "decimation": cfg.decimation}
    t0 = time.time()
    smoke = {"ok": False}
    try:
        with launch_simulation(cfg, args):
            from isaaclab.utils.assets import ISAACLAB_NUCLEUS_DIR

            from csci645_handover.tasks.handover_env import HandoverEnv
            from csci645_handover.tasks.handover_env_cfg import FRANKA_HANDOVER_CFG

            report["assets"] = {"isaaclab_nucleus_dir": ISAACLAB_NUCLEUS_DIR,
                                "franka_usd": FRANKA_HANDOVER_CFG.spawn.usd_path}
            import torch

            env = HandoverEnv(cfg)
            env.reset()
            t1 = time.time()
            for _ in range(args.steps):
                env.step(torch.zeros(env.num_envs, 3, device=env.device))
            smoke = {"ok": True, "startup_s": round(t1 - t0, 1), "steps": args.steps, "num_envs": env.num_envs,
                     "steps_per_s": round(args.steps / (time.time() - t1), 2),
                     "finite": bool(env.m["finite"].all()), "modes": env.mode.tolist(),
                     "giver_forces": [env.m["giver_force_l"].tolist(), env.m["giver_force_r"].tolist()],
                     "physics_manager": type(env.sim.physics_manager).__name__}
            write_report(report, smoke)  # inside the launch context: closing Kit ends the process
            env.close()
    except Exception as exc:  # noqa: BLE001
        import traceback

        smoke = {"ok": False, "error": repr(exc), "traceback": traceback.format_exc()[-4000:]}
        write_report(report, smoke)


def write_report(report: dict, smoke: dict) -> None:
    report["smoke"] = smoke
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps(report, indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
