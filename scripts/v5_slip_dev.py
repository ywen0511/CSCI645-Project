#!/usr/bin/env python3
"""V5 Study B development inputs (CPU, deterministic). Development cases only; nothing here is a final result.

    python3 scripts/v5_slip_dev.py probe       # configs/v5/slip/development/probe/*  (feasibility probe, section 3.2)

The probe evaluates the training-free calibrated parent (V4 geometry_calibrated) under candidate slip-mechanism
parameter sets (runtime entries in one process), checks that a no-slip case is unchanged by enabling the
mechanism (same suite, same layout, mechanism off vs on, traced), and runs the three negative controls with slip.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from csci645_handover import v5_protocol as v5  # noqa: E402

DEV = ROOT / "configs/v5/slip/development"
SENSOR = {"bias_bound_m": 0.005, "noise_std_m": 0.002, "delay_steps": 2, "max_delay_steps": 8, "ema_alpha": 0.2,
          "clean_probability": 0.25}
PARENT_BASE = {"observation_sensor": SENSOR, "observation_giver_reference": True, "grasp_uncertainty": True}
PARENT_ENTRY = {"align_max": 0.025, "giver_calibration_window_s": 0.5}  # V4 geometry_calibrated (ema0p2_cal050_a25)
GAINS = {"finger_stiffness": 2000.0, "kp": 6000.0, "kd": 60.0, "ki": 60000.0, "regrip_s": 0.1, "tolerance_m": 0.0015}
MECHANISMS = {  # candidate parameter sets (relaxed squeeze, force cap); chosen by the probe, not by outcomes
    "M1": {**GAINS, "grip_force_n": 6.0, "force_max_n": 30.0},
    "M2": {**GAINS, "grip_force_n": 12.0, "force_max_n": 45.0},
    "M3": {**GAINS, "grip_force_n": 20.0, "force_max_n": 60.0},
}


def jl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    return str(path.relative_to(ROOT))


def put(name: str, mx: dict) -> str:
    p = DEV / "probe" / f"{name}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(mx, indent=1) + "\n")
    return str(p.relative_to(ROOT))


def probe():
    rows = v5.probe_cases()
    s_all = jl(DEV / "probe/probe_suite.jsonl", rows)
    noslip = [r for r in rows if r["condition"] == "noslip"]
    s_noslip = jl(DEV / "probe/noslip_suite.jsonl", noslip)
    neg = [r for r in rows if r["condition"] in ("x+10_on105", "x+15_on105", "x-5_on105")]
    s_neg = jl(DEV / "probe/negative_suite.jsonl", neg)
    traced = [f"{v5.PREFIX}probe-development-{c}-0000" for c in ("noslip", "x+15_on140", "x-7_on070", "x+5_on105")]
    base = {**PARENT_BASE, "slip_mechanism": MECHANISMS["M1"]}
    ents = []
    for m, spec in MECHANISMS.items():
        ents.append({"id": f"calibrated_{m}", "method": "geometry", "overrides": {**PARENT_ENTRY, "slip_mechanism": spec},
                     "trace": True})
    ents.append({"id": "nominal_M2", "method": "nominal", "overrides": {"slip_mechanism": MECHANISMS["M2"]}, "trace": False})
    out = {"mechanisms": MECHANISMS, "matrices": {}}
    out["matrices"]["mechanisms"] = put("mechanisms", {
        "name": "v5_probe_mechanisms", "suite": s_all, "num_envs": len(rows), "protocol": "configs/v2/protocol.json",
        "base_overrides": base, "trace_cases": traced, "entries": ents})
    # no-slip equivalence: identical suite and layout, mechanism off (V4 configuration) vs on
    noslip_ents = [{"id": "geometry_calibrated", "method": "geometry", "overrides": dict(PARENT_ENTRY), "trace": True},
                   {"id": "nominal", "method": "nominal", "overrides": {}, "trace": True}]
    tr = [r["case_id"] for r in noslip]
    out["matrices"]["noslip_off"] = put("noslip_off", {
        "name": "v5_probe_noslip_off", "suite": s_noslip, "num_envs": len(noslip), "protocol": "configs/v2/protocol.json",
        "base_overrides": PARENT_BASE, "trace_cases": tr, "entries": noslip_ents})
    out["matrices"]["noslip_on"] = put("noslip_on", {
        "name": "v5_probe_noslip_on", "suite": s_noslip, "num_envs": len(noslip), "protocol": "configs/v2/protocol.json",
        "base_overrides": base, "trace_cases": tr,
        "entries": [{**e, "overrides": {**e["overrides"], "slip_mechanism": MECHANISMS["M2"]}} for e in noslip_ents]})
    for ctl, extra in (("no_receiver", {}), ("giver_holds", {}), ("table_support", {"table_size_override": [0.06, 0.3, 0.2]})):
        out["matrices"][f"neg_{ctl}"] = put(f"neg_{ctl}", {
            "name": f"v5_probe_neg_{ctl}", "suite": s_neg, "num_envs": len(neg), "protocol": "configs/v2/protocol.json",
            "base_overrides": {**base, "negative_control": ctl, **extra}, "trace_cases": [],
            "entries": [{"id": f"calibrated_{m}", "method": "geometry", "overrides": {**PARENT_ENTRY, "slip_mechanism": spec}}
                        for m, spec in MECHANISMS.items()]})
    (DEV / "probe/probe_setup.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out["matrices"].items()}, indent=1), len(rows), "probe cases")


if __name__ == "__main__":
    {"probe": probe}[sys.argv[1]]()
