#!/usr/bin/env python3
"""Compare separate-process replays with archived evaluation records (Stage 1 audit; Stage 6 verification).

    python3 scripts/v2_compare_replay.py --archived downloads/v1.0.0/extracted/results/eval \
        --archived downloads/v1.0.0/extracted/results/eval_final_checkpoint \
        --replay replay_b23 --replay replay_b1 --output results/v2/audit/v1_replay_comparison.json

Matches records by (run_id, checkpoint SHA-256 or None for deterministic controllers, case_id). Reports per
replay folder: terminal-reason agreement, success agreement, completion-time and release-command-time
differences, and, when two replay folders both hold traces, the per-step agreement of the hold timer,
receiver finger forces and object position between the two batch sizes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def load(d: Path) -> dict:
    out = {}
    for f in sorted(d.rglob("*.jsonl")):
        if f.name == "eval_runs.jsonl":
            continue
        for x in f.read_text().splitlines():
            if x.strip():
                r = json.loads(x)
                if "case_id" not in r:
                    continue
                if r.get("entry_id"):  # v2 records: entry IDs distinguish controllers that share a method
                    key = (r["entry_id"], r.get("checkpoint_sha256"), r["case_id"])
                else:
                    key = (r.get("run_id") if r.get("checkpoint_sha256") else r.get("method"), r.get("checkpoint_sha256"), r["case_id"])
                out[key] = r
    return out


def load_traces(d: Path) -> dict:
    out = {}
    for f in sorted(d.glob("traces__*.json")):
        stem = f.stem.replace("traces__", "")
        out[stem] = json.loads(f.read_text())
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--archived", action="append", required=True)
    ap.add_argument("--replay", action="append", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    arch = {}
    for d in a.archived:
        arch.update(load(Path(d)))
    res = {"replays": {}, "trace_agreement": None}
    for d in a.replay:
        rep = load(Path(d))
        rows, n_match, n_reason, n_succ = [], 0, 0, 0
        for k, r in sorted(rep.items()):
            o = arch.get(k)
            if o is None:
                continue
            n_match += 1
            same_reason = o["terminal_reason"] == r["terminal_reason"]
            n_reason += same_reason
            n_succ += o["success"] == r["success"]
            dt = None
            if o["success"] and r["success"]:
                dt = r["completion_time_s"] - o["completion_time_s"]
            rel = None
            if o.get("release_command_time_s") is not None and r.get("release_command_time_s") is not None:
                rel = r["release_command_time_s"] - o["release_command_time_s"]
            rows.append({"run": k[0], "checkpoint": r.get("checkpoint"), "case_id": k[2],
                         "archived": o["terminal_reason"], "replay": r["terminal_reason"], "agree": same_reason,
                         "completion_dt_s": dt, "release_cmd_dt_s": rel,
                         "archived_hold_s": o["independent_hold_s"], "replay_hold_s": r["independent_hold_s"]})
        dts = [abs(x["completion_dt_s"]) for x in rows if x["completion_dt_s"] is not None]
        res["replays"][Path(d).name] = {
            "matched_records": n_match, "unmatched_replay_records": len(rep) - n_match,
            "terminal_reason_agreement": n_reason, "success_agreement": n_succ,
            "disagreement_rate": 1 - n_reason / n_match if n_match else None,
            "completion_time_abs_diff_s": {"max": max(dts) if dts else None, "mean": float(np.mean(dts)) if dts else None,
                                            "n_exact": sum(x < 1e-6 for x in dts)},
            "disagreements": [x for x in rows if not x["agree"]],
        }
    if len(a.replay) >= 2:
        t1, t2 = load_traces(Path(a.replay[0])), load_traces(Path(a.replay[1]))
        stats = {"files": 0, "cases": 0, "max_abs_hold_timer_diff_s": 0.0, "max_abs_recv_force_diff_N": 0.0,
                 "max_abs_obj_pos_diff_m": 0.0, "identical_cases": 0, "per_case_max_obj_pos_diff_m": []}
        for name in sorted(set(t1) & set(t2)):
            stats["files"] += 1
            for cid in sorted(set(t1[name]) & set(t2[name])):
                a1, a2 = t1[name][cid], t2[name][cid]
                n = min(len(a1), len(a2))
                if n == 0:
                    continue
                stats["cases"] += 1
                h = max(abs(a1[i]["hold_timer"] - a2[i]["hold_timer"]) for i in range(n))
                f = max(abs(x - y) for i in range(n) for x, y in zip(a1[i]["recv_force"], a2[i]["recv_force"]))
                p = max(abs(x - y) for i in range(n) for x, y in zip(a1[i]["obj_pos"], a2[i]["obj_pos"]))
                stats["max_abs_hold_timer_diff_s"] = max(stats["max_abs_hold_timer_diff_s"], h)
                stats["max_abs_recv_force_diff_N"] = max(stats["max_abs_recv_force_diff_N"], f)
                stats["max_abs_obj_pos_diff_m"] = max(stats["max_abs_obj_pos_diff_m"], p)
                stats["identical_cases"] += int(h == 0 and f == 0 and p == 0 and len(a1) == len(a2))
                stats["per_case_max_obj_pos_diff_m"].append(p)
        d = np.array(stats.pop("per_case_max_obj_pos_diff_m"))
        if len(d):
            stats["per_case_max_obj_pos_diff_m_percentiles"] = {q: float(np.percentile(d, int(q[1:]))) for q in ("p50", "p90", "p99")}
            stats["cases_obj_pos_within_1mm"] = int((d < 1e-3).sum())
        res["trace_agreement"] = {"between": [Path(x).name for x in a.replay[:2]], **stats}
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "disagreements"} for k, v in res["replays"].items()},
                     indent=1))
    print(json.dumps(res["trace_agreement"], indent=1))


if __name__ == "__main__":
    main()
