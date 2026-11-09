#!/usr/bin/env python3
"""Fit one constant residual per selected history policy from its DEVELOPMENT-suite records only (CPU).

    python3 scripts/v4_fit_constants.py --devfit <runs>/mechanisms/devfit --output results/v4/mechanisms/constant_fits.json

The constant is the case-weighted mean of each episode's mean residual vector (scored steps) over all 288
development cases, clipped to the +-2 cm bound. Final-suite records are never read.
"""
import argparse
import json
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--devfit", required=True)
ap.add_argument("--output", required=True)
a = ap.parse_args()
out = {}
for d in sorted(Path(a.devfit).iterdir()):
    rows = [json.loads(l) for f in d.glob("*__selected__dev.jsonl") for l in f.read_text().splitlines() if l.strip()]
    if len(rows) != 288 or len({r["case_id"] for r in rows}) != 288 or not all(r["case_id"].startswith("v4-development-") for r in rows):
        raise SystemExit(f"{d.name}: expected the 288 development cases")
    m = [sum(r["residual_mean_xyz_m"][k] for r in rows) / len(rows) for k in range(3)]
    out[d.name] = {"constant_residual_m": [max(-0.02, min(0.02, x)) for x in m], "cases": len(rows),
                   "checkpoint_sha256": rows[0]["checkpoint_sha256"], "development_success": sum(r["success"] for r in rows)}
Path(a.output).parent.mkdir(parents=True, exist_ok=True)
Path(a.output).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
print(json.dumps({k: [round(x * 1000, 2) for x in v["constant_residual_m"]] for k, v in out.items()}))
