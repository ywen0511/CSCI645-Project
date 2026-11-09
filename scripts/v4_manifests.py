#!/usr/bin/env python3
"""Write V4 job manifests (CPU, deterministic) for scripts/v3_jobs.py (the hash-checked runner is reused).

    python3 scripts/v4_manifests.py development       # results/v4/jobs/development.json
    python3 scripts/v4_manifests.py constants         # results/v4/jobs/constants.json (after baseline selection)

Later stages (acceptance, smoke, pilots, formal training, validation, final, mechanisms, repeatability,
traces, videos, verification) are added here as their inputs exist. Every simulator task is a fresh process.
Paths starting with $RUNS resolve against the runner's --runs-root.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/v4/jobs"
SEED_EVAL = 6456501  # evaluation process seed (outside the split RNG namespaces)


def write(name, tasks):
    OUT.mkdir(parents=True, exist_ok=True)
    ids = [t["id"] for t in tasks]
    assert len(ids) == len(set(ids)), "duplicate task ids"
    (OUT / f"{name}.json").write_text(json.dumps({"name": name, "tasks": tasks}, indent=1) + "\n")
    print(f"{name}: {len(tasks)} tasks")


def matrix_task(tid, mp: Path, out: str, extra=(), seed=SEED_EVAL, only=None):
    mx = json.loads(mp.read_text())
    rel = str(mp.relative_to(ROOT))
    ents = [e for e in mx["entries"] if only is None or e["id"] in only]
    argv = ["scripts/eval_matrix.py", "--matrix", rel, "--output", out, "--seed", str(seed), *extra]
    if only is not None:
        argv[3:3] = ["--only", ",".join(e["id"] for e in ents)]
    return {"id": tid, "kind": "isaac", "argv": argv, "inputs": [rel, mx["suite"]],
            "outputs": [f"{out}/{e['id']}.jsonl" for e in ents]}


def development():
    tasks = [matrix_task(f"dev_{p.stem}", p, f"$RUNS/development/{p.stem}")
             for p in sorted((ROOT / "configs/v4/development/matrices").glob("*.json"))]
    write("development", tasks)


def constants():
    p = ROOT / "configs/v4/development/matrices_constant/constant_search.json"
    write("constants", [matrix_task("dev_constant_search", p, "$RUNS/development/constant_search")])


PILOTS = [("combined_robust_history", 901), ("combined_robust_history", 902), ("combined_robust_ff", 901),
          ("residual_robust_history", 901)]
PILOT_TRANSITIONS = 5505024  # 168 PPO iterations of 32,768; 4 x 5.51M + 5 smoke runs (0.98M) = 23.0M <= 24M cap


def pilots():
    sys.path.insert(0, str(ROOT / "src"))
    from csci645_handover import v4_protocol as v4
    tasks, evals = [], []
    for prof, seed in PILOTS:
        proto = json.loads((ROOT / f"configs/v4/pilot/{prof}.json").read_text())
        method = proto["training"]["methods"][0]
        d = f"$RUNS/pilot/{prof}_s{seed}"
        tasks.append({"id": f"pilot_{prof}_s{seed}", "kind": "isaac",
                      "argv": ["scripts/train.py", "--method", method, "--seed", str(seed), "--protocol", f"configs/v4/pilot/{prof}.json",
                               "--run-type", "pilot", "--transitions", str(PILOT_TRANSITIONS), "--checkpoint-every", "1000000",
                               "--output", d],
                      "inputs": [f"configs/v4/pilot/{prof}.json"], "outputs": [f"{d}/checkpoints/final.pt", f"{d}/DONE.json"]})
        ents = [{"id": f"{prof}_s{seed}__{t}", "method": method, "training_seed": seed, "conditions": list(v4.VALIDATION),
                 "checkpoint": f"{prof}_s{seed}/checkpoints/{t}.pt"} for t in ("step_002031616", "step_004030464", "final")]
        mp = ROOT / f"configs/v4/pilot/matrices/{prof}_s{seed}.json"
        mp.parent.mkdir(parents=True, exist_ok=True)
        mp.write_text(json.dumps({"name": f"v4_pilot_{prof}_s{seed}", "suite": "configs/v4/suites/development.jsonl",
                                  "num_envs": 144, "protocol": f"configs/v4/pilot/{prof}.json", "trace_cases": [],
                                  "entries": ents}, indent=1) + "\n")
        evals.append(matrix_task(f"pilot_eval_{prof}_s{seed}", mp, f"$RUNS/pilot_eval/{prof}_s{seed}",
                                 extra=["--checkpoint-root", "$RUNS/pilot"]))
    write("pilots", tasks)
    write("pilot_eval", evals)


if __name__ == "__main__":
    for stage in sys.argv[1:]:
        {"development": development, "constants": constants, "pilots": pilots}[stage]()
