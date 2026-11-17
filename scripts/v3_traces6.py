#!/usr/bin/env python3
"""Summarize the supplementary 6-case trace runs (CPU) and compare their outcomes with the batch-256 final records.

    python3 scripts/v3_traces6.py --runs <runs root> --index configs/v3/final_matrix_index.json [--output results/v3/traces6]

Writes summary.json: per executed final entry, the six traced cases with terminal reason in the trace run (batch 6)
and in the final matrix (batch 256), and whether each trace file holds all six cases.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--index", required=True)
    ap.add_argument("--output", default=str(ROOT / "results/v3/traces6"))
    a = ap.parse_args()
    R, O = Path(a.runs), Path(a.output)
    O.mkdir(parents=True, exist_ok=True)
    ids = [json.loads(l)["case_id"] for l in (ROOT / "configs/v3/suites/final_trace6.jsonl").read_text().splitlines() if l.strip()]
    idx = json.loads(Path(a.index).read_text())
    rows, seen = [], set()
    for e in idx["entries"]:
        if e["records"] in seen:
            continue
        seen.add(e["records"])
        eid = e["expected"]["entry_id"]
        d = R / "traces6" / eid
        tr = json.loads((d / "traces" / f"{eid}.json").read_text())
        rec = {json.loads(l)["case_id"]: json.loads(l) for l in (d / f"{eid}.jsonl").read_text().splitlines() if l.strip()}
        fin = {}
        for l in (R / e["records"]).read_text().splitlines():
            if l.strip():
                r = json.loads(l)
                if r["case_id"] in ids:
                    fin[r["case_id"]] = r
        rows.append({"entry": eid, "traced_cases": sorted(tr), "all_traced": sorted(tr) == sorted(ids),
                     "cases": {c: {"trace_run": rec[c]["terminal_reason"], "final_matrix": fin[c]["terminal_reason"]} for c in ids},
                     "agree": sum(rec[c]["terminal_reason"] == fin[c]["terminal_reason"] for c in ids)})
    out = {"cases": ids, "entries": len(rows), "agree_total": sum(r["agree"] for r in rows), "total": 6 * len(rows),
           "all_traced": all(r["all_traced"] for r in rows), "rows": rows,
           "note": "supplementary trace runs at batch 6 (separate from the primary batch-256 matrix)"}
    (O / "summary.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("entries", "agree_total", "total", "all_traced")}))


if __name__ == "__main__":
    main()
