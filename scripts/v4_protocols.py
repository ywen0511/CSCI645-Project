#!/usr/bin/env python3
"""Write V4 training protocols from the development baseline selection (CPU, deterministic).

    python3 scripts/v4_protocols.py draft      # configs/v4/training/<profile>.json (status: draft) + configs/v4/pilot/
    python3 scripts/v4_protocols.py freeze     # (scripts/v4_freeze.py) copies drafts to configs/v4/frozen/training/

Every profile uses the common geometric parent's estimator (EMA alpha, giver reference, calibration window) and
alignment bound, the same PPO settings, network widths, rollout size, curriculum of joint start displacements
and transition budget as V3. Only the observation input (one frame / four chronological frames / current frame
repeated four times), the parent (combined = geometry parent; residual = nominal trajectory) and the training
uncertainty (clean vs the development-frozen robust distribution) differ.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from csci645_handover import v4_protocol as v4  # noqa: E402

SENSOR_ROBUST = {"bias_bound_m": 0.005, "noise_std_m": 0.002, "delay_steps": 2, "max_delay_steps": 8, "clean_probability": 0.25}
SENSOR_CLEAN = {"bias_bound_m": 0.0, "noise_std_m": 0.0, "delay_steps": 0, "max_delay_steps": 8, "clean_probability": 1.0}
GRASP_ROBUST = {**v4.TRAIN_SUPPORT, "clean_probability": 0.25}
HISTORY = 4
PROFILES = {
    "combined_clean_ff": {"method": "combined", "history": 1, "mode": "stack", "robust": False},
    "combined_robust_ff": {"method": "combined", "history": 1, "mode": "stack", "robust": True},
    "combined_robust_history": {"method": "combined", "history": HISTORY, "mode": "stack", "robust": True},
    "combined_robust_repeat": {"method": "combined", "history": HISTORY, "mode": "repeat_current", "robust": True},
    "residual_robust_history": {"method": "residual", "history": HISTORY, "mode": "stack", "robust": True},
}
V3_TRAINING = json.loads((ROOT / "configs/v3/frozen/training/combined_robust_history.json").read_text())["training"]


def parent():
    sel = json.loads((ROOT / "configs/v4/development/baseline_selection.json").read_text())
    return sel["roles"]["common_parent"]


def env_overrides(prof: dict, p: dict) -> dict:
    ov = {"grasp_uncertainty": True,
          "observation_sensor": {**(SENSOR_ROBUST if prof["robust"] else SENSOR_CLEAN), "ema_alpha": p["ema_alpha"]},
          "observation_giver_reference": p["reference"] != "none",
          "observation_history": prof["history"], "observation_history_mode": prof["mode"],
          "grasp_offset_train": GRASP_ROBUST if prof["robust"] else None}
    if p.get("align_max_m") is not None:
        ov["align_max"] = p["align_max_m"]
    if p["reference"].startswith("cal"):
        ov["giver_calibration_window_s"] = {"cal010": 0.1, "cal025": 0.25, "cal050": 0.5}[p["reference"]]
    return ov


def training(seeds) -> dict:
    t = {k: V3_TRAINING[k] for k in ("actor_init", "checkpoint_interval_transitions", "curriculum", "final_transitions_per_run",
                                     "num_envs", "realized_transitions_per_run", "rollout_batch_transitions",
                                     "rollout_steps_per_env", "transition_definition", "scored_transitions")}
    t["seeds"] = list(seeds)
    return t


def draft():
    p = parent()
    for kind, seeds, out in (("final", v4.TRAINING_SEEDS, ROOT / "configs/v4/training"), ("pilot", (901, 902), ROOT / "configs/v4/pilot")):
        out.mkdir(parents=True, exist_ok=True)
        for name, prof in PROFILES.items():
            proto = {"protocol_id": f"v4-{kind}-{name}", "status": "draft (frozen copies under configs/v4/frozen/training)"
                     if kind == "final" else "pilot (development only; weights never carried into formal runs)",
                     "env_overrides": env_overrides(prof, p), "ppo_overrides": {},
                     "common_parent": {k: p[k] for k in ("candidate_id", "ema_alpha", "reference", "align_max_m")},
                     "profile": {**prof, "parent": "common geometric parent" if prof["method"] == "combined" else "nominal trajectory"},
                     "training": {**training(seeds), "methods": [prof["method"]]}}
            (out / f"{name}.json").write_text(json.dumps(proto, indent=1, sort_keys=True) + "\n")
    print("parent", p["candidate_id"])


if __name__ == "__main__":
    {"draft": draft}[sys.argv[1]]()
