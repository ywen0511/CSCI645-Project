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


if __name__ == "__main__":
    for stage in sys.argv[1:]:
        {"development": development, "constants": constants}[stage]()
