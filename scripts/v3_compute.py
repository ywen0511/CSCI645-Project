#!/usr/bin/env python3
"""Compute cost of the v3 study from the merged job ledger (CPU).

    python3 scripts/v3_compute.py [--ledger results/v3/task_ledger.jsonl] [--output results/v3/compute.json]

Every simulator task ran alone on one A100-SXM4-40GB (LSF j_exclusive), so GPU-hours = wall-clock hours of
the task, including simulator start-up and the bounded shutdown watchdog. CPU tasks are counted separately.
Counts every attempt (failed attempts included). Training throughput uses realized transitions from DONE.json
when the runs roots are given.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def t(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ledger", default=str(ROOT / "results/v3/task_ledger.jsonl"))
    ap.add_argument("--runs-root", action="append", default=[], help="runs roots holding train/*/DONE.json")
    ap.add_argument("--output", default=str(ROOT / "results/v3/compute.json"))
    a = ap.parse_args()
    rows = [json.loads(l) for l in Path(a.ledger).read_text().splitlines() if l.strip()]
    by = defaultdict(lambda: {"attempts": 0, "failed_attempts": 0, "gpu_hours": 0.0, "cpu_hours": 0.0, "max_task_min": 0.0})
    for r in rows:
        d = (t(r["end_utc"]) - t(r["start_utc"])).total_seconds() / 3600
        b = by[f"{r['runs_root']}/{r['manifest']}"]
        b["attempts"] += 1
        b["failed_attempts"] += r["rc"] != 0
        b["gpu_hours" if r["kind"] == "isaac" else "cpu_hours"] += d
        b["max_task_min"] = max(b["max_task_min"], d * 60)
    train = {}
    for root in a.runs_root:
        for p in sorted(Path(root).glob("train/*/DONE.json")):
            dj = json.loads(p.read_text())
            train[f"{Path(root).name}/{p.parent.name}"] = dj
    formal = [r for r in rows if r["runs_root"] == "formal" and r["manifest"] == "train"]
    fsec = sum((t(r["end_utc"]) - t(r["start_utc"])).total_seconds() for r in formal)
    ftrans = sum(v.get("transitions", 0) for k, v in train.items() if k.startswith("formal/"))
    out = {"hardware": "NVIDIA A100-SXM4-40GB, one GPU per simulator task (LSF exclusive), driver 580.159.03",
           "software": "Isaac Lab 3.0.0 / Isaac Sim 6.2.0.0 / RSL-RL 5.5.1 / torch 2.11.0+cu130",
           "by_stage": {k: {**v, "gpu_hours": round(v["gpu_hours"], 3), "cpu_hours": round(v["cpu_hours"], 3),
                            "max_task_min": round(v["max_task_min"], 1)} for k, v in sorted(by.items())},
           "total_gpu_hours": round(sum(v["gpu_hours"] for v in by.values()), 2),
           "total_attempts": len(rows),
           "formal_training": {"runs": len(formal), "gpu_hours": round(fsec / 3600, 2),
                               "realized_transitions": ftrans or None,
                               "transitions_per_s_incl_startup": round(ftrans / fsec, 0) if ftrans and fsec else None,
                               "mean_run_min": round(fsec / 60 / max(len(formal), 1), 1)},
           "note": "wall-clock per task including Isaac Sim start-up/shutdown; superseded attempts at the earlier "
                   "candidate commit (moved to v3/superseded/) are not counted here"}
    Path(a.output).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("total_gpu_hours", "total_attempts", "formal_training")}, indent=1))


if __name__ == "__main__":
    main()
