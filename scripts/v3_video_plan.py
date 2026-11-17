#!/usr/bin/env python3
"""Apply the frozen video rule (configs/v3/video_rule.json) to the final records and write recording plans.

    python3 scripts/v3_video_plan.py --runs <runs root with final/> --output configs/v3/video

One plan per recording process (estimator configuration x observation shape):
  plan_common.json   protocol = frozen combined_robust_history (EMA 1.0 + giver reference, 5-frame history):
                     main comparison (combined_robust_history s11 selected vs geometry_best_constant on identical cases),
                     clean baseline (geometry_common), giver-reference side of the estimator comparison (geometry_giver)
  plan_raw.json      protocol = raw estimator (EMA 1.0, no giver reference): severe-noise example (geometry_raw)
  plan_filtered.json protocol = EMA 0.2 estimator: filtered side of the estimator comparison (geometry_filtered)
Writes results/v3/jobs/videos.json (record_video tasks, then index/montage) and selection.json (why each clip).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def jl(p: Path):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--output", default=str(ROOT / "configs/v3/video"))
    a = ap.parse_args()
    R, O = Path(a.runs), Path(a.output)
    O.mkdir(parents=True, exist_ok=True)
    sel = json.loads((ROOT / "results/v3/selection/selection.json").read_text())
    roles = json.loads((ROOT / "configs/v3/baseline_selection.json").read_text())["roles"]
    aliases = json.loads((ROOT / "configs/v3/final_matrices/baseline_aliases.json").read_text())
    draft = json.loads((ROOT / "configs/v3/protocol.draft.json").read_text())["sensor"]
    base_env = json.loads((ROOT / "configs/v2/protocol.json").read_text())["env_overrides"]

    def recs(role):
        src = aliases.get(role, role)
        return {r["case_id"]: r for r in jl(R / "final" / src / f"{src}.jsonl")}, f"$RUNS/final/{src}/{src}.jsonl"

    hist_run = "combined_robust_history_s11"
    H = {r["case_id"]: r for r in jl(R / "final" / hist_run / "selected" / f"{hist_run}__selected.jsonl")}
    hist_rec = f"$RUNS/final/{hist_run}/selected/{hist_run}__selected.jsonl"
    G, g_rec = recs("geometry_best_constant")
    why, main_cases = [], []
    for name, rr in (("combined_robust_history_s11_selected", H), ("geometry_best_constant", G)):
        for cond in ("mixed_id", "mixed_ood"):
            ids = sorted(c for c in rr if rr[c]["condition"] == cond)
            s = next((c for c in ids if rr[c]["success"]), None)
            f = next((c for c in ids if not rr[c]["success"]), None)
            why.append({"method": name, "condition": cond, "first_success": s, "first_failure": f,
                        "note": None if f else "no failure in this condition; no substitute chosen"})
            main_cases += [c for c in (s, f) if c and c not in main_cases]
    Fr, f_rec = recs("geometry_filtered")
    Gv, gv_rec = recs("geometry_giver")
    ood = sorted(c for c in Fr if Fr[c]["condition"] == "mixed_ood")
    diff = next((c for c in ood if Fr[c]["success"] != Gv[c]["success"]), None)
    giver_case = diff or ood[0]
    clean_case = sorted(c for c in G if G[c]["condition"] == "clean")[0]
    noise_case = sorted(c for c in G if G[c]["condition"] == "noise_4mm")[0]
    gc = roles["geometry_common"]

    def geo(role, case, rec, out):
        s = roles[role]
        ov = {"align_max": s["align_max_m"]}
        if s["constant_x_m"]:
            ov["constant_residual_m"] = [s["constant_x_m"], 0.0, 0.0]
        return {"method": "geometry", "overrides": ov, "checkpoint": None, "case_id": case, "run_id": role,
                "category": out, "eval_records": rec, "output": f"$RUNS/videos/{out}__{role}__{case}.mp4"}

    common = []
    for c in main_cases:
        common.append({"method": "combined", "checkpoint": f"$RUNS/train/{hist_run}/checkpoints/{sel[hist_run]['selected']}.pt",
                       "case_id": c, "run_id": f"{hist_run}__selected", "category": "main_comparison", "eval_records": hist_rec,
                       "output": f"$RUNS/videos/main_comparison__{hist_run}_selected__{c}.mp4"})
        common.append(geo("geometry_best_constant", c, g_rec, "main_comparison"))
    common.append(geo("geometry_common", clean_case, recs("geometry_common")[1], "clean_baseline"))
    common.append(geo("geometry_giver", giver_case, gv_rec, "giver_reference_comparison"))
    prot_common = "configs/v3/frozen/training/combined_robust_history.json"
    for name, alpha, giver in (("raw", 1.0, False), ("filtered", roles["geometry_filtered"]["ema_alpha"], False)):
        env = dict(base_env)
        env.update(observation_sensor={**draft, "ema_alpha": alpha}, observation_giver_reference=giver)
        (O / f"protocol_{name}.json").write_text(json.dumps({"protocol_id": f"v3-video-{name}", "env_overrides": env,
                                                             "ppo_overrides": {}}, indent=1) + "\n")
    plans = {"common": (common, prot_common),
             "raw": ([geo("geometry_raw", noise_case, recs("geometry_raw")[1], "severe_noise")], "$DELIVERY/configs/v3/video/protocol_raw.json"),
             "filtered": ([geo("geometry_filtered", giver_case, f_rec, "giver_reference_comparison")], "$DELIVERY/configs/v3/video/protocol_filtered.json")}
    tasks = []
    for name, (plan, prot) in plans.items():
        (O / f"plan_{name}.json").write_text(json.dumps(plan, indent=1) + "\n")
        tasks.append({"id": f"video_{name}", "kind": "isaac",
                      "argv": ["scripts/record_video.py", "--plan", f"$DELIVERY/configs/v3/video/plan_{name}.json",
                               "--suite", "configs/v3/suites/final.jsonl", "--protocol", prot],
                      "inputs": [f"configs/v3/video/plan_{name}.json"], "outputs": [p["output"] for p in plan]})
    tasks.append({"id": "video_index_montage", "kind": "cpu",
                  "argv": ["$DELIVERY/scripts/v3_video_index.py", "--videos", "$RUNS/videos", "--plans",
                           "$DELIVERY/configs/v3/video", "--output", "$RUNS/videos"],
                  "inputs": ["scripts/v3_video_index.py"], "outputs": ["$RUNS/videos/video_index.json", "$RUNS/videos/montage.mp4"]})
    (ROOT / "results/v3/jobs/videos.json").write_text(json.dumps({"name": "videos", "tasks": tasks}, indent=1) + "\n")
    (O / "selection.json").write_text(json.dumps({"rule": "configs/v3/video_rule.json", "main": why,
                                                  "giver_reference_case": giver_case,
                                                  "giver_reference_case_reason": "first mixed_ood case where filtered and giver-reference outcomes differ"
                                                  if diff else "no mixed_ood case differs; first mixed_ood case",
                                                  "clean_case": clean_case, "noise_case": noise_case,
                                                  "clips": sum(len(p[0]) for p in plans.values())}, indent=1) + "\n")
    print(json.dumps({"clips": sum(len(p[0]) for p in plans.values()), "main_cases": main_cases, "giver_case": giver_case}, indent=1))


if __name__ == "__main__":
    main()
