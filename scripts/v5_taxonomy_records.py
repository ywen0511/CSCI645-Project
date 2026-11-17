#!/usr/bin/env python3
"""Terminal-reason / failure taxonomy for V5 record directories (CPU; reuses the V4 taxonomy definitions).

    python scripts/v5_taxonomy_records.py --records runs/v5/calibration/primary --entries a,b,c \
        --title "V5 Study A" --out results/v5/calibration/taxonomy

Reads ``<entry>.jsonl`` for each entry (all scheduled episodes), and writes taxonomy.json + taxonomy.md with,
per entry x condition: exclusive terminal reasons (% of all scheduled episodes), any-collision / any-drop rates,
completion time of successes, and the non-exclusive misaligned / premature-release / conflicting-motion flags
among failed valid-reset episodes. Study B records add the exclusive reason ``invalid_slip`` and slip-specific
diagnostics (slip validity and realized-slip error, receiver contact before the nominal grasp, misalignment at
grasp). The V4 outputs of scripts/v5_failure_taxonomy.py are not touched.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import statistics

REASONS = ["success", "prohibited_collision", "drop", "episode_timeout", "release_timeout", "invalid_reset",
           "invalid_slip"]
FLAGS = {"misaligned": "flag_misaligned_at_grasp", "premature_release": "flag_premature_release",
         "conflicting_motion": "flag_conflicting_motion"}


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    if n == 0:
        raise ValueError("empty cell")
    reasons = Counter(r["terminal_reason"] for r in rows)
    unknown = set(reasons) - set(REASONS)
    if unknown:
        raise ValueError(f"unknown terminal reason {sorted(unknown)}")
    for r in rows:
        if r["success"] != (r["terminal_reason"] == "success"):
            raise ValueError(f"{r['case_id']}: success flag disagrees with terminal reason")
        if (not r["reset_valid"]) != (r["terminal_reason"] == "invalid_reset"):
            raise ValueError(f"{r['case_id']}: reset flag disagrees with terminal reason")
    failed = [r for r in rows if r["reset_valid"] and not r["success"]]
    times = [r["completion_time_s"] for r in rows if r["success"]]
    out = {"episodes": n, "terminal_reason_counts": {k: reasons.get(k, 0) for k in REASONS},
           "terminal_reason_pct": {k: 100.0 * reasons.get(k, 0) / n for k in REASONS},
           "failed_valid_episodes": len(failed),
           "flags_among_failed_counts": {k: sum(bool(r[f]) for r in failed) for k, f in FLAGS.items()},
           "any_collision_pct": 100.0 * sum(bool(r["collision"]) for r in rows) / n,
           "any_drop_pct": 100.0 * sum(bool(r["drop"]) for r in rows) / n,
           "misaligned_at_grasp_pct": 100.0 * sum(bool(r["flag_misaligned_at_grasp"]) for r in rows) / n,
           "completion_time_s_successes": None}
    if times:
        out["completion_time_s_successes"] = {"median": statistics.median(times), "mean": statistics.fmean(times),
                                              "n": len(times)}
    if any("slip_active" in r for r in rows):
        active = [r for r in rows if r.get("slip_active")]
        errs = [r["slip_error_m"] for r in active if r.get("slip_error_m") is not None]
        out["slip"] = {
            "scheduled": len(active),
            "completed": sum(bool(r.get("slip_completed")) for r in active),
            "valid": sum(r.get("slip_valid") is True for r in active),
            "invalid": sum(r.get("slip_valid") is False for r in active),
            "not_reached": sum(r.get("slip_valid") is None for r in active),
            "error_m_median": statistics.median(errs) if errs else None,
            "error_m_max": max(errs) if errs else None,
            "receiver_contact_before_grasp": sum(bool(r.get("receiver_contact_before_grasp")) for r in rows),
        }
    return out


def build(records: Path, entries: list[str]) -> dict:
    cells = []
    for e in entries:
        rows = [json.loads(x) for x in (records / f"{e}.jsonl").read_text().splitlines() if x.strip()]
        conds = sorted({r["condition"] for r in rows}, key=lambda c: next(i for i, r in enumerate(rows) if r["condition"] == c))
        for c in ["__all__"] + conds:
            sel = rows if c == "__all__" else [r for r in rows if r["condition"] == c]
            cells.append({"entry": e, "condition": c, **summarize(sel)})
    return {"schema": 1, "definitions": {"terminal_reason": "exclusive, % of all scheduled episodes",
                                         "flags": "non-exclusive diagnostics among failed valid-reset episodes",
                                         "misalign_tol_m": 0.01, "conflict_tol_m": 0.01}, "cells": cells}


def markdown(result: dict, title: str) -> str:
    lines = [f"# {title}: failure taxonomy", "",
             "Exclusive terminal reasons as % of all scheduled episodes. Flags (misaligned / premature release / "
             "conflicting motion) are counted among failed valid-reset episodes.", ""]
    conds = []
    for c in result["cells"]:
        if c["condition"] not in conds:
            conds.append(c["condition"])
    slip = any("slip" in c for c in result["cells"])
    for cond in conds:
        lines += [f"## {'all conditions' if cond == '__all__' else cond}", "",
                  "| Entry | Success | Collision | Drop | Ep. timeout | Rel. timeout | Invalid reset |"
                  + (" Invalid slip | Slip valid/sched | Recv. contact pre-grasp |" if slip else "")
                  + " Median completion (s) | Failed: mis / pre / con |",
                  "|---|---:|---:|---:|---:|---:|---:|" + ("---:|---:|---:|" if slip else "") + "---:|---|"]
        for c in [c for c in result["cells"] if c["condition"] == cond]:
            p, t, f = c["terminal_reason_pct"], c["completion_time_s_successes"], c["flags_among_failed_counts"]
            row = (f"| {c['entry']} | {p['success']:.1f} | {p['prohibited_collision']:.1f} | {p['drop']:.1f} | "
                   f"{p['episode_timeout']:.1f} | {p['release_timeout']:.1f} | {p['invalid_reset']:.1f} |")
            if slip:
                s = c.get("slip", {})
                row += (f" {p['invalid_slip']:.1f} | {s.get('valid', 0)}/{s.get('scheduled', 0)} | "
                        f"{s.get('receiver_contact_before_grasp', 0)} |")
            row += (f" {t['median']:.2f} |" if t else " n/a |")
            row += f" {c['failed_valid_episodes']}: {f['misaligned']} / {f['premature_release']} / {f['conflicting_motion']} |"
            lines.append(row)
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--records", required=True)
    ap.add_argument("--entries", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res = build(Path(a.records), [e for e in a.entries.split(",") if e])
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "taxonomy.json").write_text(json.dumps(res, indent=1) + "\n")
    (out / "taxonomy.md").write_text(markdown(res, a.title) + "\n")
    print(f"{len(res['cells'])} cells -> {out}")


if __name__ == "__main__":
    main()
