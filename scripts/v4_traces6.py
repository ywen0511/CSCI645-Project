#!/usr/bin/env python3
"""Agreement of the supplementary six-case trace runs (batch 6) with the formal batch-240 final records (CPU).

    python3 scripts/v4_traces6.py --runs <runs root with traces6/ and final/> --output results/v4/traces6/summary.json

The trace runs exist only to record per-step traces; formal outcomes always come from the final matrix. Every
outcome disagreement is listed.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--runs", required=True)
ap.add_argument("--output", required=True)
a = ap.parse_args()
R = Path(a.runs)
idx = json.loads((ROOT / "configs/v4/final_matrix_index.json").read_text())
recs = {}
for e in idx["entries"]:
    if e.get("alias_of"):
        continue
    rows = {json.loads(l)["case_id"]: json.loads(l) for l in (R / e["records"]).read_text().splitlines() if l.strip()}
    recs[rows[next(iter(rows))]["entry_id"]] = rows
out = {"entries": 0, "pairs": 0, "agree": 0, "traced_cases": 0, "disagreements": []}
for d in sorted((R / "traces6").iterdir()):
    f = d / f"{d.name}.jsonl"
    if not f.exists():
        continue
    out["entries"] += 1
    tr = json.loads((d / "traces" / f"{d.name}.json").read_text())
    out["traced_cases"] += len(tr)
    for l in f.read_text().splitlines():
        r = json.loads(l)
        p = recs[d.name][r["case_id"]]
        out["pairs"] += 1
        if r["terminal_reason"] == p["terminal_reason"]:
            out["agree"] += 1
        else:
            out["disagreements"].append({"entry": d.name, "case": r["case_id"], "trace_run": r["terminal_reason"], "formal": p["terminal_reason"]})
Path(a.output).parent.mkdir(parents=True, exist_ok=True)
Path(a.output).write_text(json.dumps(out, indent=1) + "\n")
print({k: v for k, v in out.items() if k != "disagreements"}, len(out["disagreements"]))
