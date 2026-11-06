#!/usr/bin/env python3
"""Expand configs/v2/diagnostics.json into evaluation matrices for scripts/eval_matrix.py.

    python3 scripts/make_v2_matrices.py dev      # configs/v2/matrices/dev_{controls,learned,geometry}.json

Checkpoint paths are relative to the extracted v1.0.0 checkpoint archives (``<run_id>/checkpoints/<tag>.pt``);
pass that directory to eval_matrix.py as --checkpoint-root.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "configs/v2/matrices"


def fmt_x(x: float) -> str:
    return f"{'+' if x >= 0 else '-'}{abs(round(x * 1000)):03d}mm"


def ablation_id(combo: str) -> str:
    return f"geom_{combo}"


def dev(d: dict) -> dict[str, dict]:
    common = {"suite": d["suite"]["path"], "num_envs": d["num_envs"], "protocol": "configs/frozen/protocol.json",
              "trace_cases": d["trace_cases"]}
    cs = d["constant_offset_search"]
    controls = [
        {"id": "nominal", "group": "baseline", "method": "nominal", "trace": True},
        {"id": "geometry_zero", "group": "baseline", "method": "geometry", "trace": True},
    ]
    for base_id in ("geometry_1cm", "nominal"):
        base = cs["bases"][base_id]
        for x in cs["grid_x_m"]:
            if x == 0.0:
                continue
            controls.append({"id": f"const_{base_id}_x{fmt_x(x)}", "group": f"const_{base_id}", "method": base["method"],
                             "overrides": {**base["overrides"], "constant_residual_m": [x, cs["y_m"], cs["z_m"]]},
                             "trace": True})
    learned = []
    for key in ("combined_init", "combined_final", "residual_init", "residual_final", "combined_no_phase_final"):
        c = d["controls"][key]
        for s in c["seeds"]:
            rid = f"{c['method']}_seed{s}"
            learned.append({"id": f"{key}_s{s}", "group": key, "method": c["method"], "training_seed": s,
                            "run_id": rid, "checkpoint": f"{rid}/checkpoints/{c['checkpoint']}.pt", "trace": True,
                            "label": c.get("label", "required")})
    ga = d["geometry_ablation"]
    geometry = []
    for combo in ga["combinations"]:
        fl = {"geom_align": "A" in combo, "geom_anchor": "H" in combo, "geom_gate": "G" in combo}
        geometry.append({"id": ablation_id(combo), "group": "ablation", "method": "geometry", "overrides": fl,
                         "trace": True})
    for b in ga["alignment_bounds_m"]:
        geometry.append({"id": f"geom_bound_{b:.3f}".replace(".", "p"), "group": "bound", "method": "geometry",
                         "overrides": {"align_max": b}, "trace": b in (0.010, 0.015)})
    base = cs["bases"]["geometry_1p5cm"]
    for x in cs["grid_x_m"]:
        if x == 0.0:
            continue
        geometry.append({"id": f"const_geometry_1p5cm_x{fmt_x(x)}", "group": "const_geometry_1p5cm",
                         "method": base["method"],
                         "overrides": {**base["overrides"], "constant_residual_m": [x, cs["y_m"], cs["z_m"]]},
                         "trace": True})
    return {
        "dev_controls": {"name": "dev_controls", **common, "entries": controls},
        "dev_learned": {"name": "dev_learned", **common, "entries": learned},
        "dev_geometry": {"name": "dev_geometry", **common, "entries": geometry},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("which", choices=["dev"])
    a = ap.parse_args()
    d = json.loads((ROOT / "configs/v2/diagnostics.json").read_text())
    mats = dev(d)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, m in mats.items():
        (OUT / f"{name}.json").write_text(json.dumps(m, indent=1) + "\n")
        print(f"{name}: {len(m['entries'])} entries")


if __name__ == "__main__":
    main()
