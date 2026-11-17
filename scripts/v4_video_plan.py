#!/usr/bin/env python3
"""Apply the frozen video rule (configs/v4/video_rule.json) to the final records and write recording plans.

    python3 scripts/v4_video_plan.py --runs <runs root with final/ and train/>

Writes configs/v4/video/{protocol_<p>.json, plan_<p>.json, selection.json} and results/v4/jobs/videos.json
(one record_video process per estimator/observation protocol, then index + montage). Cases are chosen exactly
as the rule states from the formal final records; if a designated failure does not exist, no substitute is
chosen and selection.json says so.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from v4_dev import REFERENCES, base_overrides, entry_overrides  # noqa: E402

SEEDS = (111, 222, 333, 444, 555)


def jl(p: Path):
    return {json.loads(l)["case_id"]: json.loads(l) for l in p.read_text().splitlines() if l.strip()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", required=True)
    a = ap.parse_args()
    R = Path(a.runs)
    O = ROOT / "configs/v4/video"
    O.mkdir(parents=True, exist_ok=True)
    roles = json.loads((ROOT / "configs/v4/development/baseline_selection.json").read_text())["roles"]
    sel = json.loads((ROOT / "results/v4/selection/selection.json").read_text())
    v2env = json.loads((ROOT / "configs/v2/protocol.json").read_text())["env_overrides"]
    hist_proto = json.loads((ROOT / "configs/v4/frozen/training/combined_robust_history.json").read_text())

    def base_rec(role):
        return jl(R / "final" / role / f"{role}.jsonl"), f"$RUNS/final/{role}/{role}.jsonl"

    def hist(seed):
        run = f"combined_robust_history_s{seed}"
        return jl(R / "final" / run / f"{run}__selected.jsonl"), f"$RUNS/final/{run}/{run}__selected.jsonl", run

    protos = {}
    for name, role in (("fixed", "geometry_fixed"), ("calibrated", "geometry_calibrated"), ("ema", "geometry_ema")):
        x = roles[role]
        env = {**v2env, **base_overrides(x["ema_alpha"], REFERENCES[x["reference"]][0])}
        protos[name] = env
    protos["history"] = hist_proto["env_overrides"]
    protos["history_reversed"] = {**hist_proto["env_overrides"], "observation_history_permutation": [3, 2, 1, 0]}
    for name, env in protos.items():
        (O / f"protocol_{name}.json").write_text(json.dumps({"protocol_id": f"v4-video-{name}", "env_overrides": env,
                                                             "ppo_overrides": {}}, indent=1) + "\n")
    plans = {k: [] for k in protos}
    why = []

    def geo(role, case, clip, plan, order=0):
        recs, path = base_rec(role)
        x = roles[role]
        ov = entry_overrides(x) if x["method"] != "nominal" else {}
        plans[plan].append({"method": x["method"], "overrides": ov, "checkpoint": None, "case_id": case, "run_id": role,
                            "category": clip, "order": order, "eval_records": path,
                            "output": f"$RUNS/videos/{clip}__{role}__{case}.mp4"})
        return recs[case]["terminal_reason"]

    def pol(seed, case, clip, plan, tag="selected", order=0):
        recs, path, run = hist(seed)
        ck = sel[run]["selected"]
        plans[plan].append({"method": "combined", "checkpoint": f"$RUNS/train/{run}/checkpoints/{ck}.pt", "case_id": case,
                            "run_id": f"{run}__{tag}", "category": clip, "order": order, "eval_records": path,
                            "output": f"$RUNS/videos/{clip}__{run}_{tag}__{case}.mp4"})
        return recs[case]["terminal_reason"] if tag == "selected" else None

    c1 = "v4-final-grasp_15mm-0000"
    geo("nominal", c1, "nominal_vs_geometry_vs_learned", "calibrated", 0)
    geo("geometry_fixed", c1, "nominal_vs_geometry_vs_learned", "fixed", 1)
    geo("geometry_calibrated", c1, "nominal_vs_geometry_vs_learned", "calibrated", 2)
    pol(111, c1, "nominal_vs_geometry_vs_learned", "history", order=3)
    why.append({"clip": "nominal_vs_geometry_vs_learned", "case": c1, "rule": "fixed case"})
    fx, _ = base_rec("geometry_fixed")
    g15 = sorted(c for c in fx if fx[c]["condition"] == "grasp_15mm")
    fail = next((c for c in g15 if not fx[c]["success"]), None)
    geo("geometry_fixed", fail or g15[0], "unknown_grasp_boundary", "fixed")
    why.append({"clip": "unknown_grasp_boundary", "case": fail or g15[0],
                "rule": "first failing grasp_15mm case of geometry_fixed" if fail else "no failure: first grasp_15mm case shown"})
    geo("geometry_calibrated", "v4-final-mixed_ood-0000", "noisy_calibration", "calibrated")
    why.append({"clip": "noisy_calibration", "case": "v4-final-mixed_ood-0000", "rule": "fixed case"})
    found = None
    for s in SEEDS:
        recs, _, _ = hist(s)
        bad = sorted(c for c in recs if recs[c]["condition"] == "mixed_id" and not recs[c]["success"])
        if bad:
            found = (s, bad[0])
            break
    if found:
        pol(found[0], found[1], "failure", "history")
    why.append({"clip": "failure", "case": found and found[1], "seed": found and found[0],
                "rule": "first mixed_id non-success of combined_robust_history selected (seeds 111..555, then case id)",
                "note": None if found else "no selected history policy failed any mixed_id case; no substitute chosen"})
    pol(111, "v4-final-mixed_id-0000", "intervention", "history_reversed", tag="reversed_history")
    why.append({"clip": "intervention", "case": "v4-final-mixed_id-0000", "rule": "history order reversed [3,2,1,0]"})
    pol(111, "v4-final-mixed_id-0001", "learned_mixed_id", "history")
    why.append({"clip": "learned_mixed_id", "case": "v4-final-mixed_id-0001", "rule": "fixed case"})
    geo("geometry_ema", "v4-final-noise_2mm-0000", "ema_noise", "ema")
    geo("geometry_calibrated", "v4-final-clean-0000", "clean", "calibrated")
    why += [{"clip": "ema_noise", "case": "v4-final-noise_2mm-0000", "rule": "fixed case"},
            {"clip": "clean", "case": "v4-final-clean-0000", "rule": "fixed case"}]
    tasks = []
    for name, plan in plans.items():
        if not plan:
            continue
        (O / f"plan_{name}.json").write_text(json.dumps(plan, indent=1) + "\n")
        tasks.append({"id": f"video_{name}", "kind": "isaac",
                      "argv": ["scripts/record_video.py", "--plan", f"$DELIVERY/configs/v4/video/plan_{name}.json",
                               "--suite", "$DELIVERY/configs/v4/suites/final.jsonl", "--protocol",
                               f"$DELIVERY/configs/v4/video/protocol_{name}.json"],
                      "inputs": [f"configs/v4/video/plan_{name}.json", f"configs/v4/video/protocol_{name}.json"],
                      "outputs": [p["output"] for p in plan]})
    tasks.append({"id": "video_index_montage", "kind": "cpu",
                  "argv": ["$DELIVERY/scripts/v4_video_index.py", "--videos", "$RUNS/videos", "--plans",
                           "$DELIVERY/configs/v4/video", "--output", "$RUNS/videos"],
                  "inputs": ["scripts/v4_video_index.py"], "outputs": ["$RUNS/videos/video_index.json", "$RUNS/videos/montage.mp4"]})
    (ROOT / "results/v4/jobs/videos.json").write_text(json.dumps({"name": "videos", "tasks": tasks}, indent=1) + "\n")
    n = sum(len(p) for p in plans.values())
    (O / "selection.json").write_text(json.dumps({"rule": "configs/v4/video_rule.json", "clips": why, "recordings": n},
                                                 indent=1) + "\n")
    print(json.dumps({"recordings": n, "failure_clip": bool(found), "boundary_failure": bool(fail)}))


if __name__ == "__main__":
    main()
