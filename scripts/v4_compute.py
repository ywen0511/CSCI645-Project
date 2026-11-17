#!/usr/bin/env python3
"""GPU-hour accounting of the post-V3 continuation (Stage A maintenance + V4) from LSF job logs (CPU).

    python3 scripts/v4_compute.py --lsf-logs <dir> [--lsf-logs <dir> ...] --output results/v4/compute.json

Every job requested exactly one GPU (`-gpu num=1:mode=shared:j_exclusive=yes`), so GPU-hours = the job's LSF
"Run time" (wall clock, including simulator start-up, packed processes and idle tails) x 1. Several simulator
processes packed into one job are therefore counted once, never per process; failed, killed and superseded jobs
are counted. The 100 GPU-hour cap applies to the sum, not per GPU.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

STAGE = [("pv3_inv", "stage_a"), ("pv3_stageA", "stage_a"), ("pv3_fresh301", "stage_a"),
         ("v4_probe", "v4_development"), ("v4_dev", "v4_development"), ("v4_acc", "v4_acceptance"),
         ("v4_pilot", "v4_pilots"), ("v4_train", "v4_formal_training"), ("v4_val", "v4_validation"),
         ("v4_final", "v4_final_evaluation"), ("v4_mech", "v4_mechanisms_repeatability"), ("v4_extra", "v4_mechanisms_repeatability"),
         ("v4_trace", "v4_traces"), ("v4_video", "v4_videos"), ("v4_verify", "v4_verification"), ("v4_fresh", "v4_verification")]


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
            if not m or not rt:
                continue
            name = m.group(2)
            stage = next((s for k, s in STAGE if k in name), "other")
            jobs.append({"job": m.group(1), "name": name, "status": m.group(3), "stage": stage,
                         "started": st.group(1).strip() if st else None, "run_s": int(rt.group(1))})
    by = {}
    for j in jobs:
        b = by.setdefault(j["stage"], {"jobs": 0, "gpu_hours": 0.0, "failed_or_killed_jobs": 0})
        b["jobs"] += 1
        b["gpu_hours"] += j["run_s"] / 3600
        b["failed_or_killed_jobs"] += j["status"] != "Done"
    out = {"rule": __doc__.split("\n\n")[1].strip(), "hardware": "NVIDIA A100-SXM4-40GB (dgx047), driver 580.159.03",
           "by_stage": {k: {**v, "gpu_hours": round(v["gpu_hours"], 3)} for k, v in sorted(by.items())},
           "total_gpu_hours": round(sum(j["run_s"] for j in jobs) / 3600, 2), "cap_gpu_hours": 100, "jobs": jobs}
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("by_stage", "total_gpu_hours")}, indent=1))


if __name__ == "__main__":
    main()
