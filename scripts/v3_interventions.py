#!/usr/bin/env python3
"""Inference-time history interventions on the 65-case subset (CPU). Distribution shifts, not causal proof.

    python3 scripts/v3_interventions.py --runs <runs root> --index configs/v3/final_matrix_index.json \
        --output results/v3/interventions

For each selected history policy (combined_robust_history, residual_robust_history; all seeds): success on the
65 subset cases unmodified (from the final records), with frames permuted [4,2,0,3,1], and with previous frames
replaced by the current frame. Raw intervention records stay separate from the primary matrix.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def jl(p: Path):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--index", required=True)
    ap.add_argument("--output", default=str(ROOT / "results/v3/interventions"))
    a = ap.parse_args()
    R, O = Path(a.runs), Path(a.output)
    O.mkdir(parents=True, exist_ok=True)
    ids = [json.loads(l)["case_id"] for l in (ROOT / "configs/v3/suites/final_subset65.jsonl").read_text().splitlines() if l.strip()]
    idx = json.loads(Path(a.index).read_text())
    rows = []
    for e in idx["entries"]:
        if e["role"] != "selected" or e["family"] not in ("combined_robust_history", "residual_robust_history"):
            continue
        run = f"{e['family']}_s{e['seed']}"
        base = {r["case_id"]: r for r in jl(R / e["records"])}
        row = {"family": e["family"], "seed": e["seed"], "unmodified": sum(base[c]["success"] for c in ids)}
        for name in ("permuted", "current_only"):
            p = R / "interventions" / name / run / f"{run}__selected__{name}.jsonl"
            rr = {r["case_id"]: r for r in jl(p)}
            if set(rr) != set(ids):
                raise SystemExit(f"{p}: incomplete")
            row[name] = sum(rr[c]["success"] for c in ids)
            row[f"{name}_changed_terminal"] = sum(rr[c]["terminal_reason"] != base[c]["terminal_reason"] for c in ids)
            row[f"{name}_config_mismatch_declared"] = all(r.get("config_mismatch") for r in rr.values())
        rows.append(row)
    out = {"cases": len(ids), "rows": rows,
           "note": "inference-time interventions on trained history policies; the trained repeated-current control "
                   "(combined_robust_repeat) is the stronger memory comparison"}
    (O / "interventions.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
