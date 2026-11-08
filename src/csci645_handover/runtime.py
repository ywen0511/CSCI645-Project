"""Shared helpers for simulator scripts: env creation, case-queue episode loop, provenance, hashing."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[2]


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha256_json(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def git_state() -> dict:
    def run(*a):
        try:
            return subprocess.run(["git", "-C", str(REPO_ROOT), *a], capture_output=True, text=True, timeout=20).stdout.strip()
        except Exception:  # noqa: BLE001
            return ""

    diff = run("status", "--porcelain", "--untracked-files=no")
    return {"commit": run("rev-parse", "HEAD") or None, "dirty": bool(diff), "dirty_files": diff.splitlines()[:50]}


def env_cfg_dict(cfg) -> dict:
    """Serializable snapshot of the task-level fields of a HandoverEnvCfg (scene/sim omitted)."""
    keep = {}
    for k in dir(cfg):
        if k.startswith("_") or k in ("scene", "sim", "events", "observation_noise_model", "action_noise_model",
                                       "viewer", "ui_window_class_type", "video_recorders", "copy", "replace",
                                       "to_dict", "from_dict", "validate"):
            continue
        v = getattr(cfg, k)
        if callable(v):
            continue
        if isinstance(v, (int, float, str, bool, list, tuple, dict)) or v is None:
            keep[k] = v
    keep["sim_dt"] = cfg.sim.dt
    keep["num_envs"] = cfg.scene.num_envs
    return keep


def config_hash(cfg) -> str:
    """Hash of the physics/control/task configuration, excluding the method and run-local fields."""
    d = env_cfg_dict(cfg)
    for k in ("method", "geometry_enabled", "residual_enabled", "phase_input", "seed", "num_envs", "log_dir",
              "total_transitions", "curriculum"):
        d.pop(k, None)
    # v2 controller options are part of the hash only when they differ from their v1-equivalent default,
    # so v1 configurations (and the checkpoints trained with them) keep their original hash.
    for k, default in V2_CONTROLLER_DEFAULTS.items():
        if d.get(k, default) == default:
            d.pop(k, None)
    return sha256_json(d)


V2_CONTROLLER_DEFAULTS = {"geom_align": True, "geom_anchor": True, "geom_gate": True, "constant_residual_m": None,
                          "observation_sensor": None, "observation_history": 1,
                          "observation_giver_reference": False, "observation_history_mode": "stack",
                          "observation_history_permutation": None}
# Task fields that can be changed on a live environment (read every step or rebuilt by
# HandoverEnv.refresh_task_parameters). Everything else needs a new process.
RUNTIME_FIELDS = {"method", "geometry_enabled", "residual_enabled", "phase_input", "geom_align", "geom_anchor",
                  "geom_gate", "constant_residual_m", "align_max", "align_gain", "sep_tol", "release_max_wait_s"}


def controller_hash(cfg) -> str:
    """Hash of the full controller definition (task config hash + method flags)."""
    return sha256_json({"config_hash": config_hash(cfg), "geometry_enabled": cfg.geometry_enabled,
                        "residual_enabled": cfg.residual_enabled, "phase_input": cfg.phase_input})


def hardware_info() -> dict:
    info = {"python": platform.python_version(), "platform": platform.platform(), "host": platform.node()}
    try:
        import torch

        info["torch"] = torch.__version__
        info["cuda"] = torch.version.cuda
        if torch.cuda.is_available():
            info["gpu"] = torch.cuda.get_device_name(0)
            info["gpu_mem_gb"] = round(torch.cuda.get_device_properties(0).total_memory / 2**30, 1)
    except Exception:  # noqa: BLE001
        pass
    try:
        import importlib.metadata as md

        for p in ("isaacsim", "isaaclab", "isaaclab-physx", "isaaclab-rl", "rsl-rl-lib", "warp-lang"):
            try:
                info[p] = md.version(p)
            except md.PackageNotFoundError:
                info[p] = None
    except Exception:  # noqa: BLE001
        pass
    return info


def build_env_cfg(method: str, num_envs: int, device: str, seed: int, overrides: dict | None = None):
    from .tasks.handover_env_cfg import HandoverEnvCfg, apply_method

    cfg = HandoverEnvCfg()
    apply_method(cfg, method)
    for k, v in (overrides or {}).items():
        if not hasattr(cfg, k):
            raise KeyError(f"Unknown env cfg field: {k}")
        setattr(cfg, k, v)
    cfg.__post_init__()
    cfg.scene.num_envs = num_envs
    cfg.sim.device = device
    cfg.seed = seed
    return cfg


def load_overrides(path: str | None) -> dict:
    if not path:
        return {}
    data = json.loads(Path(path).read_text())
    return data.get("env_overrides", data)


def run_cases(env, cases: list[dict], policy: Callable | None, trace_case_ids: set[str] | None = None,
              max_steps: int | None = None, log_every: float = 30.0) -> tuple[list[dict], dict]:
    """Run each case exactly once (one episode per case) and return the evaluator records.

    ``env`` is the unwrapped HandoverEnv. ``policy(obs) -> actions`` or None for zero actions.
    """
    import torch

    env.set_case_queue(cases)
    env.completed_records = []
    env.traces = {}
    env.trace_env_ids = []
    obs, _ = env.reset()
    if trace_case_ids:
        env.trace_env_ids = [i for i in range(env.num_envs)
                             if int(env.case_index[i]) >= 0 and cases[int(env.case_index[i])]["case_id"] in trace_case_ids]
    traces: dict[str, list] = {}
    zeros = torch.zeros(env.num_envs, env.cfg.action_space, device=env.device)
    steps, t0, last = 0, time.time(), time.time()
    limit = max_steps or (len(cases) // env.num_envs + 2) * (int(env.max_episode_length) + 5)
    while len(env.completed_records) < len(cases) and steps < limit:
        with torch.inference_mode():
            act = zeros if policy is None else policy(obs)
        obs, _, _, _, _ = env.step(act)
        steps += 1
        if time.time() - last > log_every:
            print(f"[run_cases] steps={steps} done={len(env.completed_records)}/{len(cases)} "
                  f"elapsed={time.time()-t0:.0f}s", flush=True)
            last = time.time()
    # Trace rows carry the case id they belong to (an env may start another case after finishing).
    for rows in env.traces.values():
        for row in rows:
            case_id = cases[row["case_index"]]["case_id"] if row.get("case_index", -1) >= 0 else None
            if case_id in (trace_case_ids or set()):
                traces.setdefault(case_id, []).append(row)
    traces.pop(None, None)
    info = {"steps": steps, "wall_s": time.time() - t0, "num_envs": env.num_envs,
            "transitions": steps * env.num_envs, "completed": len(env.completed_records), "scheduled": len(cases),
            "traces": traces}
    return env.completed_records, info


def write_jsonl(path: str | Path, rows: list[dict], append: bool = False) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a" if append else "w") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")


def read_jsonl(path: str | Path) -> list[dict]:
    if not Path(path).exists():
        return []
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def as_dict(obj):
    return asdict(obj) if is_dataclass(obj) else obj


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def env_flag(name: str, default: str = "") -> str:
    return os.environ.get(name, default)
