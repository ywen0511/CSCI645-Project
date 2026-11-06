#!/usr/bin/env python3
"""Summarize pilot checkpoints on the 1,150 development cases and apply the predeclared P1/P2 rule.

    python3 scripts/v2_analyze_pilots.py --pilot <raw>/pilot --output results/v2/pilot
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from csci645_handover import v2_analysis as va  # noqa: E402

SUITES = ("development", "development_valproxy", "development_feasibility")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pilot", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    P, O = Path(a.pilot), Path(a.output)
    O.mkdir(parents=True, exist_ok=True)
    runs = sorted(p.name for p in (P / "eval").iterdir() if p.is_dir())
    table, res = [], {}
    for run in runs:
        recs = {s: va.load_records(P / "eval" / run / s) for s in SUITES if (P / "eval" / run / s).exists()}
        tags = sorted({k for r in recs.values() for k in r})
        for k in tags:
            row = {"run": run, "entry": k}
            allr = []
            for s in SUITES:
                rs = recs.get(s, {}).get(k, [])
                allr += rs
                row[f"{s}_success"] = sum(r["success"] for r in rs) / len(rs) if rs else None
                row[f"{s}_n"] = len(rs)
            row["all_success"] = sum(r["success"] for r in allr) / len(allr) if allr else None
            row["all_n"] = len(allr)
            row["collision_rate"] = sum(r["collision"] for r in allr) / len(allr) if allr else None
            row["transitions"] = allr[0].get("checkpoint_transitions") if allr else None
            v = [r for r in allr if r["reset_valid"]]
            row["mean_signed_residual_x_mm"] = 1000 * float(np.mean([r["residual_mean_xyz_m"][0] for r in v])) if v else None
            row["rms_residual_mm"] = 1000 * float(np.sqrt(np.mean([r["residual_sq_norm_mean_m2"] for r in v]))) if v else None
            table.append(row)
    va.write_csv(O / "pilot_checkpoints.csv", table)
    def mean_after(run, t0=2_000_000):
        xs = [r["all_success"] for r in table if r["run"] == run and r["transitions"] and r["transitions"] >= t0
              and not r["entry"].endswith("__final") and r["all_n"] == 1150]
        return float(np.mean(xs)) if xs else None, len(xs)
    p1, n1 = mean_after("combined_P1_s101")
    p2, n2 = mean_after("combined_P2_s101")
    decision = None
    if p1 is not None and p2 is not None:
        decision = "P1_default_init" if p2 < p1 - 0.01 else "P2_zero_mean_init"
    res = {"rule": "use P2 unless the mean success of P2 checkpoints >= 2M transitions is > 1.0 pp below P1's on the 1,150 development cases",
           "combined_P1_mean_success_ge2M": p1, "n_ckpts_P1": n1, "combined_P2_mean_success_ge2M": p2, "n_ckpts_P2": n2,
           "decision": decision}
    (O / "pilot_decision.json").write_text(json.dumps(res, indent=1) + "\n")
    L = ["| run | checkpoint | transitions | development (450) | valproxy (400) | feasibility (300) | all (1150) | collision | mean residual x [mm] | RMS residual [mm] |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for r in table:
        L.append(f"| {r['run']} | {r['entry'].split('__')[-1]} | {r['transitions']} | " + " | ".join(
            va.pct(r[f"{s}_success"]) for s in SUITES) + f" | {va.pct(r['all_success'])} | {va.pct(r['collision_rate'])} | "
            f"{r['mean_signed_residual_x_mm']:+.2f} | {r['rms_residual_mm']:.2f} |")
    (O / "pilot_tables.md").write_text("\n".join(L) + "\n\n" + json.dumps(res, indent=1) + "\n")
    print("\n".join(L)); print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
