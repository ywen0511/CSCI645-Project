#!/usr/bin/env python3
"""Apply the frozen v2 video rule (configs/v2/video_rule.json) to final records and write a recording plan.

    python3 scripts/v2_select_videos.py --final <raw>/final/eval --manifest configs/v2/matrices/final/final_manifest.json \
        --matrices configs/v2/matrices/final --output-dir <videos> --plan video_plan.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from csci645_handover import v2_analysis as va  # noqa: E402

PROT = json.loads((ROOT / "configs/v2/protocol.json").read_text())
RULE = json.loads((ROOT / "configs/v2/video_rule.json").read_text())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--final", required=True)
    ap.add_argument("--manifest", default=str(ROOT / "configs/v2/matrices/final/final_manifest.json"))
    ap.add_argument("--matrices", default=str(ROOT / "configs/v2/matrices/final"))
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--plan", required=True)
    a = ap.parse_args()
    man = json.loads(Path(a.manifest).read_text())
    rec = va.load_records(*[p for p in sorted(Path(a.final).iterdir()) if p.is_dir()])
    for dup, src in man["reuse"].items():
        rec[dup] = rec[src]
    entries = {}
    for f in Path(a.matrices).glob("final_*.json"):
        if "manifest" in f.name:
            continue
        for e in json.loads(f.read_text())["entries"]:
            entries[e["id"]] = e
    for dup, src in man["reuse"].items():
        entries[dup] = {**entries[src], "id": dup}
    by = {k: {r["case_id"]: r for r in v} for k, v in rec.items()}
    ids = sorted(by["nominal"])
    extrap = set(PROT["evaluation"]["groups"]["extrapolation"])
    ok = lambda e, c: by[e][c]["success"]  # noqa: E731
    cond = lambda c: by["nominal"][c]["condition"]  # noqa: E731

    def first(pred):
        return next((c for c in ids if pred(c)), None)

    chosen, notes = [], []
    # 1
    c = first(lambda c: cond(c) == "joint_early_2cm_030" and not ok("nominal", c))
    used = "rule" if c else "fallback"
    c = c or first(lambda c: not ok("nominal", c))
    chosen.append(("matched_comparison", c, used))
    # 2
    early = {"timing_early_015", "joint_early_1cm_015", "joint_early_2cm_030"}
    c = first(lambda c: cond(c) in early and by["ablation_1cm_A"][c]["terminal_reason"] == "drop" and ok("ablation_1cm_AG", c))
    used = "rule"
    if not c:
        c, used = first(lambda c: not ok("ablation_1cm_A", c) and ok("ablation_1cm_AG", c)), "fallback"
    if not c:
        c, used = first(lambda c: by["ablation_1cm_A"][c]["terminal_reason"] == "drop"), "fallback-2"
    chosen.append(("release_gate_rescue", c, used))
    # 3
    c, used = first(lambda c: not ok("geometry_1cm", c) and ok("geometry_1p5cm", c)), "rule"
    if not c:
        c, used = first(lambda c: not ok("bound_0p005", c) and ok("geometry_1cm", c)), "fallback"
    chosen.append(("alignment_bound", c, used))
    # 4
    cs = "combined_seed11__selected"
    c, used = first(lambda c: cond(c) in extrap and ok(cs, c) and not ok("geometry_1p5cm", c)), "rule"
    if not c:
        c, used = first(lambda c: ok(cs, c) and not ok("const_geometry_1p5cm", c)), "fallback"
    if not c:
        c, used = first(lambda c: cond(c) in extrap and ok(cs, c)), "fallback-2"
    chosen.append(("trained_success", c, used))
    # 5
    c, used, vid = first(lambda c: not ok(cs, c)), "rule", cs
    if not c:
        c, used, vid = first(lambda c: not ok("combined_seed11__final", c)), "fallback", "combined_seed11__final"
    if not c:
        notes.append("trained_failure: no failure of combined seed 11 (selected or final); showing residual seed 11 failure")
        c, used, vid = first(lambda c: not ok("residual_seed11__selected", c)), "fallback-2", "residual_seed11__selected"
    chosen.append(("trained_failure", c, used, vid))
    # 6
    rs = "residual_seed11__selected"
    c, used = first(lambda c: ok(rs, c) and not ok("nominal", c)), "rule"
    if not c:
        c, used = first(lambda c: not ok(rs, c)), "fallback"
    chosen.append(("residual_policy", c, used))

    rules = {x["id"]: x for x in RULE["categories"]}
    out = Path(a.output_dir)
    plan = []
    for item in chosen:
        cat, case, used = item[:3]
        if case is None:
            notes.append(f"{cat}: empty (no case satisfies the rule or fallbacks)")
            continue
        vids = [item[3]] if len(item) > 3 else rules[cat]["videos"]
        for eid in vids:
            e = entries[eid]
            name = f"{cat}__{eid}__{case}.mp4"
            rec_file = None
            for d in sorted(Path(a.final).iterdir()):
                src = man["reuse"].get(eid, eid)
                if (d / f"{src}.jsonl").exists():
                    rec_file = str(d / f"{src}.jsonl")
            plan.append({"category": cat, "rule": rules[cat]["rule"] if used == "rule" else rules[cat]["fallback"],
                         "rule_used": used, "entry_id": eid, "method": e["method"], "checkpoint": e.get("checkpoint"),
                         "overrides": e.get("overrides", {}), "run_id": e.get("run_id", eid), "case_id": case,
                         "output": str(out / name), "eval_records": rec_file,
                         "evaluation_outcome": by[eid][case]["terminal_reason"],
                         "replay_command": f"python scripts/record_video.py --plan <plan.json> --suite configs/v2/suites/final.jsonl --protocol configs/v2/protocol.json  # entry {eid}, case {case}"})
    Path(a.plan).write_text(json.dumps(plan, indent=1) + "\n")
    Path(a.plan).with_name("video_selection_notes.json").write_text(json.dumps({"notes": notes, "chosen": chosen}, indent=1) + "\n")
    print(f"{len(plan)} videos; notes: {notes}")
    for p in plan:
        print(p["category"], p["entry_id"], p["case_id"], p["evaluation_outcome"], p["rule_used"])


if __name__ == "__main__":
    main()
