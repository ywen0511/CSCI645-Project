#!/usr/bin/env python3
"""GPU-hour accounting of V5 (Study A, Study B, verification) from LSF job logs (CPU, standard library).

    python3 scripts/v5_compute.py --lsf-logs runs/v5/lsf_logs --output results/v5/compute.json

Every V5 job requested exactly one GPU (`-gpu num=1:mode=shared:j_exclusive=yes`), so GPU-hours = the job's LSF
"Run time" (wall clock, including simulator start-up and idle tails) x 1. Several simulator processes run one after
another inside one job are counted once. Failed, killed and superseded jobs are counted. The 60 GPU-hour cap
(V5_EXECUTION.md) applies to the sum.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

STAGE = [("v5a_", "study_a"), ("v5b_probe", "b_feasibility_probe"), ("v5b_dev", "b_development"),
         ("v5b_pilot", "b_pilots"), ("v5b_train", "b_formal_training"), ("v5b_val", "b_validation"),
         ("v5b_final", "b_final_evaluation"), ("v5b_fl", "b_final_evaluation"), ("v5b_mdev", "b_mechanisms"),
         ("v5b_mech", "b_mechanisms"), ("v5b_rep", "b_repeatability"), ("v5b_reg", "b_v4_regression"),
         ("v5b_trace", "b_traces"), ("v5_video", "videos"), ("v5_verify", "verification"), ("v5_fresh", "verification")]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lsf-logs", action="append", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    jobs = []
    for d in a.lsf_logs:
        for f in sorted(Path(d).glob("*.log")):
            t = f.read_text(errors="replace")
            m = re.search(r"Subject: Job (\d+): <([^>]+)> in cluster <[^>]+> (\w+)", t)
            rt = re.search(r"Run time :\s+(\d+) sec", t)
            st = re.search(r"Started at (.+)", t)
            gpu = re.search(r"NVIDIA (A100[^,\n]*)", t)
            if not m or not rt:
                continue
            name = m.group(2)
            stage = next((s for k, s in STAGE if k in name), "other")
            jobs.append({"job": m.group(1), "name": name, "status": m.group(3), "stage": stage,
                         "started": st.group(1).strip() if st else None, "run_s": int(rt.group(1)),
                         "gpu": gpu.group(1).strip() if gpu else None})
    by = {}
    for j in jobs:
        b = by.setdefault(j["stage"], {"jobs": 0, "gpu_hours": 0.0, "failed_or_killed_jobs": 0})
        b["jobs"] += 1
        b["gpu_hours"] += j["run_s"] / 3600
        b["failed_or_killed_jobs"] += j["status"] != "Done"
    out = {"rule": __doc__.split("\n\n")[1].strip(), "hardware": "NVIDIA A100-SXM4 (80 GB, LSF gpu_large hosts), "
           "driver bundle 580.159.03", "by_stage": {k: {**v, "gpu_hours": round(v["gpu_hours"], 3)} for k, v in sorted(by.items())},
           "total_gpu_hours": round(sum(j["run_s"] for j in jobs) / 3600, 2), "cap_gpu_hours": 60, "jobs": jobs}
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("by_stage", "total_gpu_hours")}, indent=1))


if __name__ == "__main__":
    main()
