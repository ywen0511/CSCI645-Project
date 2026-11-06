#!/usr/bin/env python3
"""Select the v2 constant-offset controls on 750 development cases (CPU only).

    python3 scripts/v2_select_constants.py --dev <raw>/dev --output results/v2/diagnostics/constants_v2.json

Cases: development (450) + development_feasibility (300). Grid: x = -5..+10 mm (frozen -5..+5 grid plus the
documented +6..+10 extension), y = z = 0. Rule: highest success; then fewer collision episodes; then smaller
|x|; then ascending x. x = 0 reuses the base controller's zero-residual records.
Folders used under --dev: controls, geometry, feasibility, feas_constants, constants_ext, feas_constants_ext.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from csci645_handover import v2_analysis as va  # noqa: E402

GRID = [x / 1000 for x in range(-5, 11)]
ZERO_DEV = {"nominal": "nominal", "geometry_1cm": "geometry_zero", "geometry_1p5cm": "geom_bound_0p015"}
ZERO_FEAS = {"nominal": "nominal", "geometry_1cm": "geometry_1cm", "geometry_1p5cm": "geometry_1p5cm"}


def fx(x):
    return f"{'+' if x >= 0 else '-'}{abs(round(x * 1000)):03d}mm"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dev", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    D = Path(a.dev)
    dev = {}
    for sub in ("controls", "geometry", "constants_ext"):
        dev.update(va.load_records(D / sub))
    feas = {}
    for sub in ("feasibility", "feas_constants", "feas_constants_ext"):
        feas.update(va.load_records(D / sub))
    out = {"cases": {"development": 450, "development_feasibility": 300}, "grid_x_m": GRID,
           "rule": "highest success on the 750 development cases; then fewer collision episodes; then smaller |x|; then ascending x",
           "grid_note": "-5..+5 mm frozen in configs/v2/diagnostics.json; +6..+10 mm added after the frozen grid selected its edge (docs/v2/DECISIONS.md)",
           "bases": {}}
    for b in ZERO_DEV:
        scores = []
        for x in GRID:
            ed = ZERO_DEV[b] if x == 0 else f"const_{b}_x{fx(x)}"
            ef = ZERO_FEAS[b] if x == 0 else f"const_{b}_x{fx(x)}"
            rd, rf = dev[ed], feas[ef]
            if len(rd) != 450 or len(rf) != 300:
                raise SystemExit(f"{b} x={x}: incomplete records ({len(rd)}, {len(rf)})")
            rs = rd + rf
            scores.append({"x_m": x, "success": sum(r["success"] for r in rs), "n": len(rs),
                           "collision_episodes": sum(r["collision"] for r in rs), "drops": sum(r["drop"] for r in rs),
                           "success_development": sum(r["success"] for r in rd),
                           "success_feasibility": sum(r["success"] for r in rf),
                           "success_extrapolation_x3": sum(r["success"] for r in rf if "x3" in r["condition"]),
                           "entries": [ed, ef]})
        sel = va.select_constant(scores)
        out["bases"][b] = {"selected_x_m": sel["x_m"], "selected": sel, "scores": scores,
                           "selected_at_grid_edge": sel["x_m"] in (GRID[0], GRID[-1])}
        print(f"{b}: x = {1000 * sel['x_m']:+.0f} mm  ({sel['success']}/750, coll {sel['collision_episodes']})"
              f"{'  [AT GRID EDGE]' if out['bases'][b]['selected_at_grid_edge'] else ''}")
        for s in scores:
            print(f"   {1000 * s['x_m']:+3.0f} mm: {s['success']}/750 dev {s['success_development']} feas {s['success_feasibility']} "
                  f"x3 {s['success_extrapolation_x3']}/150 coll {s['collision_episodes']} drops {s['drops']}")
    Path(a.output).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
