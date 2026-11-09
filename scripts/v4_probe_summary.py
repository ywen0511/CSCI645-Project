#!/usr/bin/env python3
"""Summarize the V4 development grasp-feasibility probe (CPU).

    python3 scripts/v4_probe_summary.py --runs <probe output dir> --output results/v4/development/probe_summary.json
"""
import argparse
import json
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--runs", required=True)
ap.add_argument("--output", required=True)
a = ap.parse_args()
recs = {}
for f in sorted(Path(a.runs).glob("*/*.jsonl")):
    if f.name != "eval_runs.jsonl":
        recs[f.stem] = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
ref = recs["geometry_fixed"]
conds = list(dict.fromkeys(r["condition"] for r in ref))
out = {"suite": "configs/v4/development/probe/suite.jsonl", "entries": sorted(recs), "conditions": {}}
for c in conds:
    rs = [r for r in ref if r["condition"] == c]
    ach = [r["grasp_offset_achieved_xyz_m"] for r in rs if r["reset_valid"]]
    row = {"requested_m": rs[0]["grasp_offset_requested_xyz_m"], "cases": len(rs),
           "valid_resets": sum(r["reset_valid"] for r in rs),
           "reset_failed_checks": sorted({x for r in rs for x in r["reset_failed_checks"]}),
           "achieved_mean_m": [sum(v[k] for v in ach) / len(ach) for k in range(3)] if ach else None,
           "outcomes": {}}
    for e, rows in recs.items():
        rr = sorted((r for r in rows if r["condition"] == c), key=lambda r: r["case_id"])
        row["outcomes"][e] = [r["terminal_reason"] for r in rr]
    out["conditions"][c] = row
out["totals"] = {e: {"success": sum(r["success"] for r in rows), "cases": len(rows)} for e, rows in recs.items()}
Path(a.output).parent.mkdir(parents=True, exist_ok=True)
Path(a.output).write_text(json.dumps(out, indent=1) + "\n")
print(out["totals"])
