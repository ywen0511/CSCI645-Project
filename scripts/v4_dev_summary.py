#!/usr/bin/env python3
"""Per-condition development summary of every entry's records (CPU).

    python3 scripts/v4_dev_summary.py --runs <dev runs dir> --output <summary.json>
"""
import argparse
import json
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--runs", required=True)
ap.add_argument("--output", required=True)
a = ap.parse_args()
out = {}
for f in sorted(Path(a.runs).glob("**/*.jsonl")):
    if f.name == "eval_runs.jsonl" or f.parent.name == "ledger":
        continue
    rows = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
    conds = list(dict.fromkeys(r["condition"] for r in rows))
    out[f.stem] = {c: {"cases": sum(r["condition"] == c for r in rows),
                       "success": sum(r["success"] for r in rows if r["condition"] == c),
                       "collision": sum(bool(r["collision"]) for r in rows if r["condition"] == c),
                       "invalid_reset": sum(not r["reset_valid"] for r in rows if r["condition"] == c),
                       "terminal": {t: sum(r["terminal_reason"] == t for r in rows if r["condition"] == c)
                                    for t in sorted({r["terminal_reason"] for r in rows})}}
                   for c in conds}
    out[f.stem]["_source_commit"] = rows[0]["source_commit"]
Path(a.output).parent.mkdir(parents=True, exist_ok=True)
Path(a.output).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
print(len(out), "entries")
