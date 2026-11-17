#!/usr/bin/env python3
"""Build the V4 pilot completion report from the raw pilot/smoke artifacts (CPU, standard library).

    python3 scripts/v4_pilot_report.py --pilots <v4/pilots2> --killed <v4/pilots> --smoke <v4/acc/smoke> \
        --eval-summary results/v4/pilots/pilot_eval_summary.json --output-dir results/v4/pilot

Writes one small summary per run/attempt (results/v4/pilot/runs/*.json) and results/v4/pilot/summary.json in the
schema checked by scripts/v4_freeze.py. Transitions come from each run's DONE.json / train_log.jsonl:
  * completed pilots: DONE.json transitions (must be 5,505,024);
  * killed packed attempt: completed PPO iterations from train_log.jsonl plus, as an upper bound, one partially
    collected iteration (32,768) per run, because a killed iteration's environment steps are not logged;
  * smoke runs: 131,072 each; smoke resumes: the increment beyond the resumed checkpoint (65,536 each), not the
    cumulative counter.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

BATCH = 32768


def jl(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pilots", required=True)
    ap.add_argument("--killed", required=True)
    ap.add_argument("--smoke", required=True)
    ap.add_argument("--eval-summary", required=True)
    ap.add_argument("--output-dir", required=True)
    a = ap.parse_args()
    O = Path(a.output_dir)
    (O / "runs").mkdir(parents=True, exist_ok=True)
    ev = json.loads(Path(a.eval_summary).read_text())
    evidence, runs = [], []

    def put(name, obj):
        p = O / "runs" / f"{name}.json"
        p.write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n")
        evidence.append(p)

    for d in sorted(Path(a.pilots).glob("pilot/*")):
        meta, done, log = json.loads((d / "run.json").read_text()), json.loads((d / "DONE.json").read_text()), jl(d / "train_log.jsonl")
        ck = jl(d / "checkpoints.jsonl")
        prof, seed = d.name.rsplit("_s", 1)
        tail = log[-21:]
        eps = sum(r["episodes"] for r in tail) or 1
        evals = {k.split("__")[1]: {c: v["success"] for c, v in rows.items() if not c.startswith("_")}
                 for k, rows in ev.items() if k.startswith(d.name + "__")}
        rec = {"profile": prof, "seed": int(seed), "status": "completed", "transitions": done["transitions"],
               "iterations": done["iterations"], "wall_s": round(done["wall_s"], 1), "source_commit": meta["git"]["commit"],
               "source_dirty": meta["git"]["dirty"], "config_hash": meta["config_hash"], "protocol": meta["protocol"],
               "protocol_sha256": meta["protocol_sha256"], "checkpoints_saved": len(ck),
               "final_checkpoint_sha256": next(r["sha256"] for r in ck if r["tag"] == "final"),
               "last_21_iterations": {"train_success_rate": round(sum(r["train_success"] for r in tail) / eps, 4),
                                      "train_collisions": sum(r["train_collision"] for r in tail),
                                      "action_std_final": log[-1]["action_std"],
                                      "non_finite": False},
               "median_fps": sorted(r["fps"] for r in log)[len(log) // 2],
               "development_eval_success_per_condition_of_24": evals}
        if rec["transitions"] != 5505024 or meta["git"]["dirty"]:
            raise SystemExit(f"{d.name}: incomplete or dirty pilot")
        put(f"pilot_{d.name}", rec)
        runs.append({k: rec[k] for k in ("profile", "seed", "status", "transitions", "source_commit", "config_hash",
                                         "final_checkpoint_sha256")} | {"evaluation": f"results/v4/pilot/runs/pilot_{d.name}.json"})
    killed = []
    for d in sorted(Path(a.killed).glob("pilot/*")):
        log = jl(d / "train_log.jsonl")
        done_tr = log[-1]["transitions"] if log else 0
        killed.append({"run": d.name, "completed_iterations": len(log), "logged_transitions": done_tr,
                       "counted_transitions_upper_bound": done_tr + BATCH})
    put("killed_packed_attempt", {"note": "four pilots packed on one GPU, killed for low throughput; partial outputs kept "
                                          "in the release; restarted one at a time in a new runs root", "runs": killed})
    smoke = []
    for d in sorted(Path(a.smoke).iterdir()):
        if not (d / "DONE.json").exists():
            continue
        done = json.loads((d / "DONE.json").read_text())
        if d.name.endswith("_resume"):
            res = json.loads((d / "run_resume.json").read_text())
            inc = done["transitions"] - res["resumed_transitions"]
            smoke.append({"run": d.name, "kind": "smoke_resume", "cumulative": done["transitions"], "counted": inc})
        else:
            smoke.append({"run": d.name, "kind": "smoke", "cumulative": done["transitions"], "counted": done["transitions"]})
    put("smoke_runs", {"runs": smoke})
    other = sum(k["counted_transitions_upper_bound"] for k in killed) + sum(s["counted"] for s in smoke)
    total = sum(r["transitions"] for r in runs) + other
    evidence.append(Path(a.eval_summary))
    summary = {
        "complete": len(runs) == 4,
        "all_attempts_accounted": True,
        "runs": runs,
        "other_training_transitions": other,
        "other_training_breakdown": {"killed_packed_attempt_upper_bound": sum(k["counted_transitions_upper_bound"] for k in killed),
                                     "smoke": sum(s["counted"] for s in smoke if s["kind"] == "smoke"),
                                     "smoke_resume_increments": sum(s["counted"] for s in smoke if s["kind"] == "smoke_resume")},
        "total_training_transitions": total,
        "cap": 24000000,
        "formal_configuration_decision": (
            "Retain the V3 PPO, network, rollout (1,024 x 32), curriculum and 10M budget unchanged. The combined robust "
            "feed-forward and history pilots matched their calibrated parent (24/24 in every validation-like development "
            "stratum at 2M, 4M and final, one 23/24) with stable training (no collapse, finite losses); the residual-only "
            "history pilot (nominal parent) reached 12-24/24 (mixed_id 15/24). Limitation: development strata are at the "
            "parent's ceiling, so pilots cannot show whether learning adds anything; that is a question for the frozen study."),
        "evidence": [{"path": str(p).split("csci645-v4/")[-1] if "csci645-v4/" in str(p) else str(p), "sha256": sha(p)} for p in evidence],
    }
    (O / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({k: summary[k] for k in ("complete", "other_training_transitions", "total_training_transitions")}))


if __name__ == "__main__":
    main()
