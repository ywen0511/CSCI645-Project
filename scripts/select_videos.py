#!/usr/bin/env python3
"""Choose representative videos with a declared, outcome-independent-of-taste rule.

Rule (first case by case ID within each category, using the final-evaluation records):
  1. clean_baseline      nominal on final-clean-0000.
  2. comparison          all five methods (learned methods: seed-11 run, selected checkpoint) on the first
                         joint_early_stress case (by case ID) on which nominal fails.
  3. position_failure    nominal: first position_stress case whose record fails with the misalignment flag set.
  4. premature_release   nominal: first case whose record is a drop with the premature-release flag set.
  5. conflicting_motion  any method/run: first failed record with the conflicting-motion flag set (if none
                         exists, the category is reported as not observed).
  6. learned_failure     combined seed 11: first failed record by case ID.
  7. timeout_geometry    geometry: first release_timeout record, if any.

Usage:
    python3 scripts/select_videos.py --eval-dir RUNS/eval --selection results/summary/selection.json \
        --train-dir RUNS/train --output-dir VIDEOS --plan video_plan.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--eval-dir", required=True)
    ap.add_argument("--selection", required=True)
    ap.add_argument("--train-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--plan", required=True)
    a = ap.parse_args()
    ev, tr, od = Path(a.eval_dir), Path(a.train_dir), Path(a.output_dir)
    sel = json.loads(Path(a.selection).read_text())
    files = {}
    for f in ev.glob("*.jsonl"):
        if f.name.startswith("eval_runs"):
            continue
        files[f.stem.split("__")[0]] = f
    recs = {rid: sorted(load(f), key=lambda r: r["case_id"]) for rid, f in files.items()}
    plan, notes = [], {}

    def ckpt(rid):
        if rid not in sel:
            return None
        return str(tr / rid / "checkpoints" / f"{sel[rid]['selected']['checkpoint']}.pt")

    def add(category, rule, rid, case_id):
        method = rid.split("_seed")[0] if "_seed" in rid else rid
        plan.append({"category": category, "rule": rule, "method": method, "run_id": rid, "case_id": case_id,
                     "checkpoint": ckpt(rid), "eval_records": str(files[rid]),
                     "output": str(od / f"{category}__{rid}__{case_id}.mp4")})

    add("clean_baseline", "nominal on final-clean-0000", "nominal", "final-clean-0000")
    nom = recs["nominal"]
    first_fail = next((r for r in nom if r["condition"] == "joint_early_stress" and not r["success"]), None)
    if first_fail:
        for rid in ("nominal", "geometry", "residual_seed11", "combined_seed11", "combined_no_phase_seed11"):
            add("comparison", "all methods on the first joint_early_stress case where nominal fails", rid,
                first_fail["case_id"])
    pos = next((r for r in nom if r["condition"] == "position_stress" and not r["success"] and r["flag_misaligned_at_grasp"]), None)
    if pos:
        add("position_failure", "nominal: first position_stress failure with misalignment flag", "nominal", pos["case_id"])
    else:
        notes["position_failure"] = "not observed"
    pre = next((r for r in nom if r["drop"] and r["flag_premature_release"]), None)
    if pre:
        add("premature_release", "nominal: first drop with premature-release flag", "nominal", pre["case_id"])
    else:
        notes["premature_release"] = "not observed"
    con = None
    for rid in sorted(recs):
        c = next((r for r in recs[rid] if r["flag_conflicting_motion"] and not r["success"]), None)
        if c and (con is None or c["case_id"] < con[1]["case_id"]):
            con = (rid, c)
    if con:
        add("conflicting_motion", "first failed record with conflicting-motion flag (any run)", con[0], con[1]["case_id"])
    else:
        notes["conflicting_motion"] = "not observed in any final-evaluation record"
    lf = next((r for r in recs.get("combined_seed11", []) if not r["success"]), None)
    if lf:
        add("learned_failure", "combined seed 11: first failure by case ID", "combined_seed11", lf["case_id"])
    gto = next((r for r in recs.get("geometry", []) if r["terminal_reason"] == "release_timeout"), None)
    if gto:
        add("timeout_geometry", "geometry: first release_timeout", "geometry", gto["case_id"])
    else:
        notes["timeout_geometry"] = "geometry produced no release_timeout"
    Path(a.plan).write_text(json.dumps(plan, indent=2))
    Path(a.plan).with_suffix(".notes.json").write_text(json.dumps(notes, indent=2))
    print(json.dumps({"videos": len(plan), "notes": notes}, indent=2))


if __name__ == "__main__":
    main()
