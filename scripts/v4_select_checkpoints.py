#!/usr/bin/env python3
"""Select one checkpoint per formal V4 run from its validation records only (CPU, standard library).

    python3 scripts/v4_select_checkpoints.py --validation <runs>/validation --output results/v4/selection

Rule (frozen in configs/v4/analysis_plan.json): candidates are the first saved checkpoints at or after 2, 4, 6,
8 and 10 million transitions; step 0 is an untrained control and never eligible. Key, in order:
  1. validation mean success, equal weight per validation condition (6 x 40 cases), descending;
  2. unsafe-event rate (any prohibited collision or a drop), ascending;
  3. residual magnitude (mean over cases of the per-episode mean max-axis |residual|), ascending;
  4. latest candidate (largest transition count).
Numerical ties: each value is rounded to 12 decimal places before comparison. Every scheduled validation case must
be recorded exactly once; invalid resets abort selection for reconciliation. Final outcomes are never read.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from csci645_handover import v4_protocol as v4  # noqa: E402


def score(rows):
    conds = list(v4.VALIDATION)
    per = {c: [r for r in rows if r["condition"] == c] for c in conds}
    succ = sum(sum(r["success"] for r in v) / len(v) for v in per.values()) / len(conds)
    unsafe = sum(bool(r["collision"]) or r["terminal_reason"] == "drop" for r in rows) / len(rows)
    resid = sum(r["residual_abs_mean_m"] for r in rows) / len(rows)
    return {"success_rate": succ, "unsafe_rate": unsafe, "residual_magnitude_m": resid,
            "transitions": rows[0]["checkpoint_transitions"], "checkpoint_sha256": rows[0]["checkpoint_sha256"],
            "by_condition": {c: sum(r["success"] for r in v) for c, v in per.items()}}


def key(s):
    r = lambda x: round(x, 12)  # noqa: E731
    return (-r(s["success_rate"]), r(s["unsafe_rate"]), r(s["residual_magnitude_m"]), -s["transitions"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--validation", required=True)
    ap.add_argument("--output", default=str(ROOT / "results/v4/selection"))
    a = ap.parse_args()
    V, O = Path(a.validation), Path(a.output)
    O.mkdir(parents=True, exist_ok=True)
    suite = [json.loads(l)["case_id"] for l in (ROOT / "configs/v4/suites/validation.jsonl").read_text().splitlines() if l.strip()]
    out = {}
    for mp in sorted((ROOT / "configs/v4/frozen/matrices/validation").glob("*.json")):
        run = mp.stem
        cands, control = [], None
        for e in json.loads(mp.read_text())["entries"]:
            f = V / run / e["id"] / f"{e['id']}.jsonl"
            rows = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
            ids = [r["case_id"] for r in rows]
            if sorted(ids) != sorted(suite):
                raise SystemExit(f"{f}: {len(ids)} records, expected all {len(suite)} validation cases exactly once")
            if not all(r["reset_valid"] for r in rows):
                raise SystemExit(f"{f}: invalid resets; reconcile before selection")
            s = {**score(rows), "tag": Path(e["checkpoint"]).stem, "entry": e["id"]}
            if e.get("role") == "untrained_control":
                control = s
            else:
                cands.append(s)
        best = sorted(cands, key=key)[0]
        (O / f"{run}.json").write_text(json.dumps({"run": run, "rule": __doc__.split("Key, in order:")[1].strip(),
                                                   "selected": best["tag"], "candidates": cands, "untrained_control": control},
                                                  indent=1) + "\n")
        out[run] = {"selected": best["tag"], "success_rate": best["success_rate"], "unsafe_rate": best["unsafe_rate"],
                    "residual_magnitude_m": best["residual_magnitude_m"], "checkpoint_sha256": best["checkpoint_sha256"]}
    (O / "selection.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: v["selected"] for k, v in out.items()}, indent=1))


if __name__ == "__main__":
    main()
