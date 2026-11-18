#!/usr/bin/env python3
"""POST HOC sensitivity analysis of the V5 Study B primary contrasts: excluding invalid slips (CPU; numpy).

Not preregistered; added after v5.0.0 (docs/v5/DECISIONS.md, 2026-11-18). It does not replace the preregistered
analysis (scripts/v5_slip_analysis.py), in which an ``invalid_slip`` counts as a failure for every method.

Question: are B1 and B2 "not established" only because 5-7% of held-out slips missed their target? For each
reported condition, a base case is kept only if no episode of any primary arm (``slip_robust_history`` and
``slip_robust_ff`` selected checkpoints, all five seeds, and ``geometry_best``) ended in ``invalid_slip``. B1 and
B2 are then recomputed on the kept cases with the preregistered bootstrap (training seed x base case, 10,000 draws,
seed 6458401, 95% and 97.5% percentile intervals). Caveat: the filter conditions on an outcome of the episodes
themselves, so the kept cases are those on which the slip mechanism worked for every arm, not a random subset.

    python scripts/v5_slip_sensitivity.py --runs <extracted raw-final.tar.gz> --out results/v5/slip/sensitivity
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import v5_slip_analysis as sa  # noqa: E402

CONDITIONS = ("slip_mixed_id", "slip_mixed_ood")  # primary condition first; the second is exploratory


def analyse(runs: Path, repeats: int = 10000) -> dict:
    plan = sa.check_freeze()
    suite, order = sa.load_suite(sa.ROOT / plan["suites"]["final"]["path"])
    seed = int(plan["seeds"]["analysis"])
    seeds = plan["learned"]["seeds"]
    aliases = json.loads((sa.SL / "matrices/final_baselines/aliases.json").read_text())["declared_aliases"]
    contrasts = plan["primary"]["contrasts"]
    names = list(dict.fromkeys(n for c in contrasts for n in (c["left"], c["right"])))
    arms = {}
    for n in names:
        if n in sa.PROFILES:
            arms[n] = [sa.load_records(runs / f"final/{n}_s{s}" / f"{n}_s{s}__selected.jsonl", suite, expect_seed=s)
                       for s in seeds]
        else:
            arms[n] = [sa.load_records(runs / "final/baselines" / f"{aliases.get(n, n)}.jsonl", suite)]
    sa.require(plan["primary"]["condition"] == CONDITIONS[0] and CONDITIONS[0] in order, "primary condition changed")

    out = []
    for cond in (c for c in CONDITIONS if c in order):
        ids = order[cond]
        bad = {i for recs in arms.values() for r in recs for i in ids if r[i]["terminal_reason"] == "invalid_slip"}
        kept = [i for i in ids if i not in bad]
        sa.require(len(kept) > 0, f"{cond}: no case left")
        row = {"condition": cond, "role": "primary" if cond == CONDITIONS[0] else "exploratory",
               "base_cases": len(ids), "excluded_base_cases": len(bad), "kept_base_cases": len(kept),
               "invalid_slip_episodes": {n: sum(r[i]["terminal_reason"] == "invalid_slip" for r in recs for i in ids)
                                         for n, recs in arms.items()},
               "episodes_per_case": {n: len(recs) for n, recs in arms.items()},
               "success_pct_all": {n: float(sa.matrix(recs, ids).mean() * 100) for n, recs in arms.items()},
               "success_pct_kept": {n: float(sa.matrix(recs, kept).mean() * 100) for n, recs in arms.items()},
               "contrasts": []}
        for c in contrasts:
            full = sa.boot(sa.matrix(arms[c["left"]], ids), sa.matrix(arms[c["right"]], ids), seed, repeats)
            sub = sa.boot(sa.matrix(arms[c["left"]], kept), sa.matrix(arms[c["right"]], kept), seed, repeats)
            row["contrasts"].append({"id": c["id"], "left": c["left"], "right": c["right"], "all_cases": full,
                                     "valid_slip_cases": sub,
                                     "lower_975_above_zero_valid_slip_cases": sub["ci97.5"][0] > 0})
        out.append(row)
    return {"schema": 1, "status": "POST HOC sensitivity analysis, not preregistered; the preregistered result is "
                                   "results/v5/slip/analysis/summary.json",
            "rule": "keep a base case only if no episode of any primary arm ended in invalid_slip",
            "arms": names, "checkpoints": "selected", "bootstrap_repeats": repeats, "bootstrap_seed": seed,
            "conditions": out}


def fmt(c):
    return f"[{c[0]:+.1f}, {c[1]:+.1f}]"


def markdown(res: dict) -> str:
    L = ["# V5 Study B - post hoc sensitivity: excluding invalid slips", "",
         "Not preregistered. A base case is kept only if no episode of any primary arm (history and feed-forward "
         "selected checkpoints, five seeds each, and `geometry_best`) ended in `invalid_slip`. Same bootstrap as the "
         "preregistered analysis. The filter conditions on an episode outcome, so kept cases are not a random subset.",
         "", "| Condition | Contrast | All cases: diff (97.5% CI) | Kept cases | Valid-slip cases: diff (95% CI) | (97.5% CI) |",
         "|---|---|---|---:|---|---|"]
    for r in res["conditions"]:
        for c in r["contrasts"]:
            a, s = c["all_cases"], c["valid_slip_cases"]
            L.append(f"| {r['condition']} ({r['role']}) | {c['id']}: {c['left']} - {c['right']} | "
                     f"{a['difference_pp']:+.1f} {fmt(a['ci97.5'])} | {r['kept_base_cases']}/{r['base_cases']} | "
                     f"{s['difference_pp']:+.1f} {fmt(s['ci95'])} | {fmt(s['ci97.5'])} |")
    L += ["", "| Condition | Arm | Invalid-slip episodes | Success, all cases (%) | Success, kept cases (%) |",
          "|---|---|---:|---:|---:|"]
    for r in res["conditions"]:
        for n in res["arms"]:
            L.append(f"| {r['condition']} | {n} | {r['invalid_slip_episodes'][n]} of "
                     f"{r['episodes_per_case'][n] * r['base_cases']} | {r['success_pct_all'][n]:.1f} | "
                     f"{r['success_pct_kept'][n]:.1f} |")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=ROOT / "results/v5/slip/sensitivity")
    a = ap.parse_args()
    res = analyse(a.runs)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "summary.json").write_text(json.dumps(res, indent=1) + "\n")
    (a.out / "summary.md").write_text(markdown(res))
    print(markdown(res))


if __name__ == "__main__":
    main()
