#!/usr/bin/env python3
"""Summarize the v3 pilots (development only; seeds 101/102) from train logs and pilot evaluations (CPU).

    python3 scripts/v3_pilot_report.py --pilot <runs>/pilot --eval <runs>/pilot_eval --output results/v3/pilot

Per pilot: throughput, training-episode outcomes over the run, loss/entropy/action-std trajectory (finite?),
scored fraction, and on the 144 validation-like development cases: success, residual magnitude, workspace
clipping, geometry saturation, reset validity, and the dense vs terminal reward split. Writes
pilot_summary.json and pilot_tables.md. Nothing here selects a final checkpoint.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def jl(p: Path):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def mean(v):
    v = [x for x in v if x is not None]
    return sum(v) / len(v) if v else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pilot", required=True)
    ap.add_argument("--eval", required=True)
    ap.add_argument("--output", default="results/v3/pilot")
    a = ap.parse_args()
    P, E, O = Path(a.pilot), Path(a.eval), Path(a.output)
    O.mkdir(parents=True, exist_ok=True)
    out = {}
    for d in sorted(p for p in P.iterdir() if p.is_dir()):
        log = jl(d / "train_log.jsonl")
        done = json.loads((d / "DONE.json").read_text()) if (d / "DONE.json").exists() else {}
        n = len(log)
        last = log[int(0.8 * n):] if n else []
        finite = all(all(math.isfinite(float(r[k])) for k in ("loss_value", "loss_surrogate", "loss_entropy", "mean_step_reward"))
                     and all(math.isfinite(x) for x in r["action_std"]) for r in log)
        ep = lambda rows, k: sum(r.get(k, 0) for r in rows)  # noqa: E731
        s = {"iterations": n, "transitions": log[-1]["transitions"] if log else None, "done": bool(done),
             "fps_mean": mean([r["fps"] for r in log]), "wall_s": log[-1]["wall_s"] if log else None,
             "losses_finite": finite, "action_std_final": log[-1]["action_std"] if log else None,
             "action_std_first": log[0]["action_std"] if log else None,
             "train_episodes": ep(log, "episodes"),
             "train_success_rate_all": ep(log, "train_success") / max(1, ep(log, "episodes")),
             "train_success_rate_last20pct": ep(last, "train_success") / max(1, ep(last, "episodes")),
             "train_failures_last20pct": {k: ep(last, f"train_{k}") for k in ("drop", "collision", "release_timeout", "timeout", "invalid_reset", "infra_error")},
             "scored_fraction": mean([r["scored_transitions"] / (r["transitions"] - (log[i - 1]["transitions"] if i else 0))
                                      for i, r in enumerate(log)]),
             "mean_step_reward_first_last": [log[0]["mean_step_reward"], log[-1]["mean_step_reward"]] if log else None}
        recs = []
        for f in (E / d.name).glob("*.jsonl"):
            if f.name != "eval_runs.jsonl":
                recs += jl(f)
        if recs:
            by = {}
            for r in recs:
                by.setdefault(r["condition"], []).append(r)
            s["dev_eval"] = {"cases": len(recs), "success": sum(r["success"] for r in recs),
                             "valid_resets": sum(r["reset_valid"] for r in recs),
                             "per_condition_success": {c: sum(r["success"] for r in v) for c, v in sorted(by.items())},
                             "residual_abs_mean_mm": 1000 * mean([r.get("residual_abs_mean_m") for r in recs]),
                             "residual_abs_max_mm": 1000 * max(r.get("residual_abs_max_m") or 0 for r in recs),
                             "workspace_clip_mean_mm": 1000 * mean([r.get("workspace_clip_mean_m") for r in recs]),
                             "geometry_align_saturation_frac": mean([r.get("geometry_align_saturation_frac") for r in recs]),
                             "residual_mean_xyz_mm": [1000 * mean([r["residual_mean_xyz_m"][k] for r in recs]) for k in range(3)],
                             "return_dense_mean": mean([r.get("episode_return_excl_terminal_step") for r in recs]),
                             "return_terminal_step_mean": mean([r.get("terminal_step_reward") for r in recs])}
        out[d.name] = s
    (O / "pilot_summary.json").write_text(json.dumps(out, indent=1) + "\n")
    L = ["# v3 pilots (development only; not results)", "",
         "| pilot | transitions | fps | losses finite | train success (last 20%) | dev success /144 | resid. mean [mm] | resid. max [mm] | clip [mm] | align sat. | mean resid. x,y,z [mm] |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, s in out.items():
        e = s.get("dev_eval", {})
        f = lambda v, d=2: "-" if v is None else f"{v:.{d}f}"  # noqa: E731
        L.append(f"| {k} | {s['transitions']:,} | {f(s['fps_mean'], 0)} | {s['losses_finite']} | {f(100 * s['train_success_rate_last20pct'], 1)}% | "
                 f"{e.get('success', '-')} | {f(e.get('residual_abs_mean_mm'))} | {f(e.get('residual_abs_max_mm'))} | "
                 f"{f(e.get('workspace_clip_mean_mm'))} | {f(e.get('geometry_align_saturation_frac'), 3)} | "
                 f"{', '.join(f(x) for x in e.get('residual_mean_xyz_mm', []))} |")
    (O / "pilot_tables.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
