#!/usr/bin/env python3
"""Apply the frozen V5 video rule (configs/v5/video_rule.json) to the final records and write recording plans.

    python3 scripts/v5_video_plan.py --runs <Study B runs root (final/, train/)> --study-a <Study A primary records>

Writes configs/v5/video/{protocol_<p>.json, plan_<p>.json, selection.json} and results/v5/jobs/videos.json (one
record_video.py process per protocol, then index + montage). Cases follow the rule exactly from the formal final
records; if a designated failure does not exist, no substitute is chosen and selection.json says so.
Study A clips replay in their own process (Study A suite and base configuration). Paths: $RUNS = Study B runs
root; Study A records are addressed relative to it ($RUNS/../calibration/primary), as on the release layout.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from csci645_handover import v5_protocol as v5  # noqa: E402
from v5_slip_study import mech_base  # noqa: E402

SEEDS = v5.TRAINING_SEEDS
O = ROOT / "configs/v5/video"


def jl(p: Path):
    return {json.loads(x)["case_id"]: json.loads(x) for x in p.read_text().splitlines() if x.strip()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--study-a", required=True)
    a = ap.parse_args()
    R, A = Path(a.runs), Path(a.study_a)
    O.mkdir(parents=True, exist_ok=True)
    sel_roles = json.loads((ROOT / "configs/v5/slip/development/baseline_selection.json").read_text())["roles"]
    aliases = json.loads((ROOT / "configs/v5/slip/matrices/final_baselines/aliases.json").read_text())["declared_aliases"]
    sel = json.loads((ROOT / "results/v5/slip/selection/selection.json").read_text())
    v2env = json.loads((ROOT / "configs/v2/protocol.json").read_text())["env_overrides"]
    amx = json.loads((ROOT / "configs/v5/calibration/matrix_ema0p2.json").read_text())
    protos = {"study_a": {**v2env, **amx["base_overrides"]}, "slip_baselines": {**v2env, **mech_base("a")}}
    for prof in ("slip_robust_history", "slip_robust_ff"):
        protos[prof] = json.loads((ROOT / f"configs/v5/slip/training/{prof}.json").read_text())["env_overrides"]
    for name, env in protos.items():
        (O / f"protocol_{name}.json").write_text(json.dumps({"protocol_id": f"v5-video-{name}", "env_overrides": env,
                                                             "ppo_overrides": {}}, indent=1) + "\n")
    plans = {k: [] for k in protos}
    why = []

    def study_a(cfg, case, clip, order):
        ent = next(e for e in amx["entries"] if e["id"] == cfg)
        recs = jl(A / f"{cfg}.jsonl")
        plans["study_a"].append({"method": "geometry", "overrides": ent["overrides"], "checkpoint": None, "case_id": case,
                                 "run_id": cfg, "category": clip, "order": order,
                                 "eval_records": f"$RUNS/../calibration/primary/{cfg}.jsonl",
                                 "output": f"$RUNS/videos/{clip}__{cfg}__{case}.mp4"})
        return recs[case]["terminal_reason"]

    def base(role, case, clip, order=0):
        src = aliases.get(role, role)
        recs = jl(R / "final/baselines" / f"{src}.jsonl")
        x = sel_roles[role]
        plans["slip_baselines"].append({"method": x["method"], "overrides": x["overrides"], "checkpoint": None,
                                        "case_id": case, "run_id": role, "category": clip, "order": order,
                                        "eval_records": f"$RUNS/final/baselines/{src}.jsonl",
                                        "output": f"$RUNS/videos/{clip}__{role}__{case}.mp4"})
        return recs[case]["terminal_reason"]

    def pol(prof, seed, case, clip, order=0):
        run = f"{prof}_s{seed}"
        recs = jl(R / f"final/{run}" / f"{run}__selected.jsonl")
        plans[prof].append({"method": "combined", "checkpoint": f"$RUNS/train/{run}/checkpoints/{sel[run]['selected']}.pt",
                            "case_id": case, "run_id": f"{run}__selected", "category": clip, "order": order,
                            "eval_records": f"$RUNS/final/{run}/{run}__selected.jsonl",
                            "output": f"$RUNS/videos/{clip}__{run}_selected__{case}.mp4"})
        return recs[case]["terminal_reason"]

    ca = "v5cal-heldout-grasp_15mm-0000"
    study_a("ema0p2_fixed_a25", ca, "study_a_matched_calibration", 0)
    study_a("ema0p2_cal050_a25", ca, "study_a_matched_calibration", 1)
    why.append({"clip": "study_a_matched_calibration", "case": ca, "rule": "fixed case"})

    cal = jl(R / "final/baselines/geometry_calibrated.jsonl")
    mixed = sorted(c for c in cal if cal[c]["condition"] == "slip_mixed_id")
    pick = next((c for c in mixed if not cal[c]["success"] and cal[c]["terminal_reason"] != "invalid_slip"), None)
    cs = pick or f"{v5.PREFIX}-final-slip_mixed_id-0000"
    base("geometry_calibrated", cs, "slip_one_shot_vs_tracking_vs_history", 0)
    base("geometry_tracking", cs, "slip_one_shot_vs_tracking_vs_history", 1)
    pol("slip_robust_history", 111, cs, "slip_one_shot_vs_tracking_vs_history", 2)
    pol("slip_robust_ff", 111, cs, "slip_feed_forward", 0)
    why.append({"clip": "slip_one_shot_vs_tracking_vs_history", "case": cs,
                "rule": "first slip_mixed_id failure (not invalid_slip) of geometry_calibrated" if pick
                else "no such failure: v5slip-final-slip_mixed_id-0000"})
    why.append({"clip": "slip_feed_forward", "case": cs, "rule": "same case as the comparison clip"})

    found = None
    for s in SEEDS:
        run = f"slip_robust_history_s{s}"
        recs = jl(R / f"final/{run}" / f"{run}__selected.jsonl")
        bad = sorted(c for c in recs if recs[c]["condition"] == "slip_mixed_id" and not recs[c]["success"]
                     and recs[c]["terminal_reason"] != "invalid_slip")
        if bad:
            found = ("history", s, bad[0])
            break
    if found:
        pol("slip_robust_history", found[1], found[2], "study_b_failure")
    else:
        gb = jl(R / "final/baselines" / f"{aliases.get('geometry_best', 'geometry_best')}.jsonl")
        bad = sorted(c for c in gb if gb[c]["condition"] == "slip_mixed_id" and not gb[c]["success"]
                     and gb[c]["terminal_reason"] != "invalid_slip")
        if bad:
            found = ("geometry_best", None, bad[0])
            base("geometry_best", bad[0], "study_b_failure")
    why.append({"clip": "study_b_failure", "case": found and found[2], "seed": found and found[1],
                "method": found and found[0],
                "rule": "first slip_mixed_id non-success (not invalid_slip) of slip_robust_history selected (seeds 111..555, "
                        "then case id); else of geometry_best",
                "note": None if found else "no failure of either; no substitute chosen"})
    pol("slip_robust_history", 111, f"{v5.PREFIX}-final-static_mixed_id-0000", "no_slip_control")
    why.append({"clip": "no_slip_control", "case": f"{v5.PREFIX}-final-static_mixed_id-0000", "rule": "fixed case"})
    base("geometry_tracking", f"{v5.PREFIX}-final-slip_pos_8-0000", "large_slip_tracking")
    why.append({"clip": "large_slip_tracking", "case": f"{v5.PREFIX}-final-slip_pos_8-0000", "rule": "fixed case"})

    tasks = []
    suites = {"study_a": "$DELIVERY/configs/v5/calibration/suite_heldout.jsonl"}
    for name, plan in plans.items():
        if not plan:
            continue
        (O / f"plan_{name}.json").write_text(json.dumps(plan, indent=1) + "\n")
        tasks.append({"id": f"video_{name}", "kind": "isaac",
                      "argv": ["scripts/record_video.py", "--plan", f"$DELIVERY/configs/v5/video/plan_{name}.json",
                               "--suite", suites.get(name, "$DELIVERY/configs/v5/slip/suites/final.jsonl"), "--protocol",
                               f"$DELIVERY/configs/v5/video/protocol_{name}.json"],
                      "inputs": [f"configs/v5/video/plan_{name}.json", f"configs/v5/video/protocol_{name}.json"],
                      "outputs": [p["output"] for p in plan]})
    tasks.append({"id": "video_index_montage", "kind": "cpu",
                  "argv": ["$DELIVERY/scripts/v5_video_index.py", "--videos", "$RUNS/videos", "--plans",
                           "$DELIVERY/configs/v5/video", "--output", "$RUNS/videos"],
                  "inputs": ["scripts/v5_video_index.py"], "outputs": ["$RUNS/videos/videos.json", "$RUNS/videos/montage.mp4"]})
    (ROOT / "results/v5/jobs/videos.json").write_text(json.dumps({"name": "videos", "tasks": tasks}, indent=1) + "\n")
    n = sum(len(p) for p in plans.values())
    (O / "selection.json").write_text(json.dumps({"rule": "configs/v5/video_rule.json", "clips": why, "recordings": n},
                                                 indent=1) + "\n")
    print(json.dumps({"recordings": n, "failure_clip": bool(found), "comparison_case": cs}))


if __name__ == "__main__":
    main()
