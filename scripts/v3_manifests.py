#!/usr/bin/env python3
"""Write v3 job manifests (CPU, deterministic). Each manifest lists every simulator/CPU task of one stage.

    python3 scripts/v3_manifests.py acceptance     # results/v3/jobs/acceptance_{sim,eval,smoke}.json
    python3 scripts/v3_manifests.py development    # results/v3/jobs/development.json (85 fresh-process entries)

Later stages (pilots, formal training, validation, final evaluation, interventions, repeatability, videos)
are added by the same script once their inputs exist. Runs execute with scripts/v3_jobs.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/v3/jobs"
PROFILES = {"combined_clean_ff": "combined", "combined_robust_ff": "combined", "combined_robust_history": "combined",
            "residual_robust_history": "residual", "combined_robust_repeat": "combined"}
SEED_EVAL = 6455501


def write(name, tasks):
    OUT.mkdir(parents=True, exist_ok=True)
    ids = [t["id"] for t in tasks]
    assert len(ids) == len(set(ids)), "duplicate task ids"
    (OUT / f"{name}.json").write_text(json.dumps({"name": name, "tasks": tasks}, indent=1) + "\n")
    print(f"{name}: {len(tasks)} tasks")


def acceptance():
    A = "$RUNS/acceptance"
    sim = [{"id": "acc_sensor", "kind": "isaac", "argv": ["scripts/v3_acceptance.py", "sensor", "--output", f"{A}/sensor.json"],
            "inputs": ["scripts/v3_acceptance.py", "src/csci645_handover/core/observation.py"], "outputs": [f"{A}/sensor.json"]}]
    for c in ("residual", "boundary"):
        sim.append({"id": f"acc_{c}", "kind": "isaac", "argv": ["scripts/v3_acceptance.py", c, "--output", f"{A}/{c}.json"],
                    "inputs": ["scripts/v3_acceptance.py", "src/csci645_handover/tasks/handover_env.py"], "outputs": [f"{A}/{c}.json"]})
    for v in ("archived", "ff_ema1p0_giver0", "ff_ema0p5_giver1", "hist5_ema0p2_giver0", "hist5_ema1p0_giver1"):
        sim.append({"id": f"acc_dependency_{v}", "kind": "isaac",
                    "argv": ["scripts/v3_acceptance.py", "dependency", "--variant", v, "--output", f"{A}/dependency_{v}.json"],
                    "inputs": ["scripts/v3_acceptance.py", "src/csci645_handover/tasks/handover_env.py"],
                    "outputs": [f"{A}/dependency_{v}.json"]})
    write("acceptance_sim", sim)
    ev = []
    for m in ("a1_b1", "a1_b8", "neg_no_receiver", "neg_giver_holds", "neg_table_support", "a3_b1", "a3_b23", "a3_b23rev",
              "a6_sensor0", "a6_archived"):
        mx = json.loads((ROOT / f"configs/v3/acceptance/{m}.json").read_text())
        for e in mx["entries"]:
            ev.append({"id": f"acc_{m}_{e['id']}", "kind": "isaac",
                       "argv": ["scripts/eval_matrix.py", "--matrix", f"configs/v3/acceptance/{m}.json", "--only", e["id"],
                                "--output", f"{A}/{m}/{e['id']}", "--seed", str(SEED_EVAL)],
                       "inputs": [f"configs/v3/acceptance/{m}.json", mx["suite"]],
                       "outputs": [f"{A}/{m}/{e['id']}/{e['id']}.jsonl"]})
    write("acceptance_eval", ev)
    sm = []
    for prof, method in PROFILES.items():
        d = f"$RUNS/smoke/smoke_{prof}_s101"
        sm.append({"id": f"smoke_{prof}", "kind": "isaac",
                   "argv": ["scripts/train.py", "--method", method, "--seed", "101", "--protocol", f"configs/v3/training/{prof}.json",
                            "--run-type", "smoke", "--transitions", "131072", "--checkpoint-every", "65536", "--output", d],
                   "inputs": [f"configs/v3/training/{prof}.json", "scripts/train.py"], "outputs": [f"{d}/checkpoints/final.pt"]})
        sm.append({"id": f"smoke_{prof}_copy", "kind": "shell",
                   "argv": ["rm", "-rf", f"{d}_resume", "&&", "cp", "-r", d, f"{d}_resume"],
                   "inputs": [], "outputs": [f"{d}_resume/checkpoints/latest.pt"]})
        sm.append({"id": f"smoke_{prof}_resume", "kind": "isaac",
                   "argv": ["scripts/train.py", "--method", method, "--seed", "101", "--protocol", f"configs/v3/training/{prof}.json",
                            "--run-type", "smoke", "--transitions", "196608", "--checkpoint-every", "65536",
                            "--resume", f"{d}_resume/checkpoints/latest.pt", "--output", f"{d}_resume"],
                   "inputs": [f"configs/v3/training/{prof}.json"], "outputs": [f"{d}_resume/run_resume.json"]})
        sm.append({"id": f"smoke_{prof}_inspect", "kind": "isaac",
                   "argv": ["scripts/closeout_inspect_ckpt.py", "--before", f"{d}/checkpoints/latest.pt", "--after",
                            f"{d}_resume/checkpoints/final.pt", "--expect-iterations", "6", "--expect-transitions", "196608",
                            "--output", f"{A}/resume_{prof}.json"],
                   "inputs": [], "outputs": [f"{A}/resume_{prof}.json"]})
    for prof in ("combined_robust_ff", "combined_robust_history", "residual_robust_history"):
        mx = json.loads((ROOT / f"configs/v3/acceptance/a2_{prof}.json").read_text())
        for e in mx["entries"]:
            sm.append({"id": f"acc_a2_{prof}_{e['id']}", "kind": "isaac",
                       "argv": ["scripts/eval_matrix.py", "--matrix", f"configs/v3/acceptance/a2_{prof}.json", "--only", e["id"],
                                "--checkpoint-root", "$RUNS/smoke", "--output", f"{A}/a2_{prof}/{e['id']}", "--seed", str(SEED_EVAL)],
                       "inputs": [f"configs/v3/acceptance/a2_{prof}.json"], "outputs": [f"{A}/a2_{prof}/{e['id']}/{e['id']}.jsonl"]})
    for mode, prof in (("stack", "combined_robust_history"), ("repeat_current", "combined_robust_repeat"), ("permuted", "combined_robust_history")):
        sm.append({"id": f"acc_inputs_{mode}", "kind": "isaac",
                   "argv": ["scripts/v3_acceptance.py", "inputs", "--mode", mode, "--checkpoint",
                            f"$RUNS/smoke/smoke_{prof}_s101/checkpoints/final.pt", "--output", f"{A}/inputs_{mode}.json"],
                   "inputs": ["scripts/v3_acceptance.py"], "outputs": [f"{A}/inputs_{mode}.json"]})
    write("acceptance_smoke", sm)


def development():
    tasks = []
    for p in sorted((ROOT / "configs/v3/matrices/development").glob("*.json")):
        mx = json.loads(p.read_text())
        for e in mx["entries"]:
            if e["id"] == "nominal" and p.stem != "ema1p0_giver0":
                continue  # nominal ignores the estimator: run once, alias in the selection table
            tasks.append({"id": f"dev_{p.stem}_{e['id']}", "kind": "isaac",
                          "argv": ["scripts/eval_matrix.py", "--matrix", f"configs/v3/matrices/development/{p.name}", "--only", e["id"],
                                   "--output", f"$RUNS/development/{p.stem}/{e['id']}", "--seed", str(SEED_EVAL)],
                          "inputs": [f"configs/v3/matrices/development/{p.name}", "configs/v3/suites/development.jsonl"],
                          "outputs": [f"$RUNS/development/{p.stem}/{e['id']}/{e['id']}.jsonl"]})
    write("development", tasks)


def cache():
    A = "$RUNS/acceptance"
    write("acceptance_cache", [{"id": "acc_cache_test", "kind": "cpu",
        "argv": ["scripts/v3_cache_test.py", "--isaac-python", "$PY", "--matrix", "configs/v3/acceptance/a1_b8.json", "--entry", "geometry_1p5cm",
                 "--ckpt-matrix", "configs/v3/acceptance/a2_combined_robust_ff.json", "--ckpt-entry", "combined_robust_ff_step0",
                 "--checkpoint-root", "$RUNS/smoke", "--work", f"{A}/cache_test", "--output", f"{A}/cache_test.json"],
        "inputs": ["scripts/v3_cache_test.py"], "outputs": [f"{A}/cache_test.json"]}])


PILOTS = [("combined_robust_ff", 101), ("combined_robust_ff", 102), ("combined_robust_history", 101),
          ("combined_robust_history", 102), ("residual_robust_history", 101), ("residual_robust_history", 102),
          ("combined_robust_repeat", 101), ("combined_clean_ff", 101)]
PILOT_TRANSITIONS = 2752512  # 84 PPO iterations of 32,768; 8 x 2.75M + 1.97M smoke <= 24M cap


def pilots():
    tasks = []
    dev_strata = ["clean", "physical_only", "bias_5mm", "noise_2mm", "delay_2step", "mixed_id"]
    for prof, seed in PILOTS:
        d = f"$RUNS/pilot/{prof}_s{seed}"
        tasks.append({"id": f"pilot_{prof}_s{seed}", "kind": "isaac",
                      "argv": ["scripts/train.py", "--method", PROFILES[prof], "--seed", str(seed), "--protocol",
                               f"configs/v3/pilot/{prof}.json", "--run-type", "pilot", "--transitions", str(PILOT_TRANSITIONS),
                               "--checkpoint-every", "1000000", "--output", d],
                      "inputs": [f"configs/v3/pilot/{prof}.json"], "outputs": [f"{d}/checkpoints/final.pt", f"{d}/DONE.json"]})
        mx = {"name": f"v3_pilot_{prof}_s{seed}", "suite": "configs/v3/suites/development.jsonl", "num_envs": 144,
              "protocol": f"configs/v3/pilot/{prof}.json", "trace_cases": ["v3-development-mixed_id-0000"],
              "entries": [{"id": f"{prof}_s{seed}_final", "method": PROFILES[prof], "training_seed": seed, "trace": True,
                           "checkpoint": f"{prof}_s{seed}/checkpoints/final.pt", "conditions": dev_strata}]}
        mp = ROOT / f"configs/v3/pilot/matrices/{prof}_s{seed}.json"
        mp.parent.mkdir(parents=True, exist_ok=True)
        mp.write_text(json.dumps(mx, indent=1) + "\n")
        e = mx["entries"][0]["id"]
        tasks.append({"id": f"pilot_eval_{prof}_s{seed}", "kind": "isaac",
                      "argv": ["scripts/eval_matrix.py", "--matrix", f"configs/v3/pilot/matrices/{prof}_s{seed}.json",
                               "--checkpoint-root", "$RUNS/pilot", "--output", f"$RUNS/pilot_eval/{prof}_s{seed}", "--seed", str(SEED_EVAL)],
                      "inputs": [f"configs/v3/pilot/matrices/{prof}_s{seed}.json"],
                      "outputs": [f"$RUNS/pilot_eval/{prof}_s{seed}/{e}.jsonl"]})
    write("pilots", tasks)


if __name__ == "__main__":
    for stage in sys.argv[1:]:
        {"acceptance": acceptance, "development": development, "cache": cache, "pilots": pilots}[stage]()
