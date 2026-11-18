#!/usr/bin/env python3
"""Summarize V5 Study B pilots (labelled pilots; never used for claims). CPU, standard library.

    python3 scripts/v5_pilot_summary.py --pilots <runs>/v5/pilot_r2 [--eval <runs>/v5/pilot_eval_r2] \
        --out results/v5/slip/pilot/summary_r2.json

Per pilot: throughput (transitions per wall second), wall time, and the training-episode success rate, mean step
reward and action std over the first and last ten PPO iterations (does the learning curve move?); optionally the
development-suite success of the pilot checkpoints.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def window(rows, a, b):
    rows = rows[a:b]
    eps = sum(r["episodes"] for r in rows)
    return {"iterations": [rows[0]["iteration"], rows[-1]["iteration"]],
            "train_success_rate": sum(r["train_success"] for r in rows) / max(1, eps),
            "train_invalid_slip_rate": sum(r.get("train_invalid_slip", 0) for r in rows) / max(1, eps),
            "mean_step_reward": sum(r["mean_step_reward"] for r in rows) / len(rows),
            "action_std_mean": sum(sum(r["action_std"]) / 3 for r in rows) / len(rows), "episodes": eps}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pilots", required=True)
    ap.add_argument("--eval", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = {"status": "pilot runs: labelled, released, never used for claims", "pilots": {}}
    for d in sorted(Path(a.pilots).iterdir()):
        if not (d / "train_log.jsonl").exists():
            continue
        rows = [json.loads(x) for x in (d / "train_log.jsonl").read_text().splitlines() if x.strip()]
        done = json.loads((d / "DONE.json").read_text()) if (d / "DONE.json").exists() else None
        run = json.loads((d / "run.json").read_text())
        p = {"source_commit": run["git"]["commit"], "source_dirty": run["git"]["dirty"],
             "protocol": run["protocol"], "config_hash": run["config_hash"], "iterations": len(rows),
             "transitions": rows[-1]["transitions"], "done": done is not None,
             "wall_s": done["wall_s"] if done else rows[-1]["wall_s"],
             "first10": window(rows, 0, 10), "last10": window(rows, -10, None)}
        p["transitions_per_s"] = p["transitions"] / p["wall_s"]
        p["projected_formal_run_minutes"] = 10027008 / p["transitions_per_s"] / 60
        if a.eval:
            ev = {}
            for f in sorted((Path(a.eval) / d.name).glob("*.jsonl")):
                if f.name == "eval_runs.jsonl":
                    continue
                recs = [json.loads(x) for x in f.read_text().splitlines() if x.strip()]
                by = {}
                for r in recs:
                    by.setdefault(r["condition"], []).append(r["success"])
                ev[f.stem] = {c: sum(v) / len(v) for c, v in sorted(by.items())}
            p["development_success"] = ev
        out["pilots"][d.name] = p
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    for k, p in out["pilots"].items():
        print(k, f"{p['transitions_per_s']:.0f} tr/s, formal ~{p['projected_formal_run_minutes']:.1f} min,",
              "succ", round(p["first10"]["train_success_rate"], 3), "->", round(p["last10"]["train_success_rate"], 3),
              "rew", round(p["first10"]["mean_step_reward"], 4), "->", round(p["last10"]["mean_step_reward"], 4),
              "std", round(p["first10"]["action_std_mean"], 3), "->", round(p["last10"]["action_std_mean"], 3))


if __name__ == "__main__":
    main()
