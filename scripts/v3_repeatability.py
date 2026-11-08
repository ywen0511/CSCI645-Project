#!/usr/bin/env python3
"""V3 repeatability on the predeclared 65-case subset (CPU; numpy). Sensitivity check on existing cases.

    python3 scripts/v3_repeatability.py --runs <runs root> --index configs/v3/final_matrix_index.json \
        --output results/v3/repeatability

Entries: geometry_common, geometry_best_constant, combined_robust_history seeds 11..55 (selected); process seeds
6455601/2/3; batch sizes 1 and 23 (2,730 episodes). Reports per entry/process/batch: success, terminal-reason and
success agreement with the original final record (batch 256, seed 6455501) and between processes; the
exogenous sensor stream is identical by construction (case seed/frame indexed, acceptance check 3) and every record
carries its observation_error, which is compared here. Paired effect history - geometry_common: per process and
batch, and after averaging each case over the three processes within each training seed (processes are never
treated as extra seeds or cases); bootstrap over training seeds and base-case clusters (v3_analysis.paired_effect).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from csci645_handover.v3_analysis import paired_effect  # noqa: E402

PS, BS = (6455601, 6455602, 6455603), (1, 23)


def jl(p: Path):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--index", required=True)
    ap.add_argument("--output", default=str(ROOT / "results/v3/repeatability"))
    a = ap.parse_args()
    R, O = Path(a.runs), Path(a.output)
    O.mkdir(parents=True, exist_ok=True)
    sub = [json.loads(l) for l in (ROOT / "configs/v3/suites/final_subset65.jsonl").read_text().splitlines() if l.strip()]
    ids = [c["case_id"] for c in sub]
    idx = json.loads(Path(a.index).read_text())
    orig = {}
    for e in idx["entries"]:
        key = e["family"] if e["seed"] is None else f"{e['family']}_s{e['seed']}__{e['role']}"
        orig[key] = {r["case_id"]: r for r in jl(R / e["records"])}
    hist = [f"combined_robust_history_s{s}__selected" for s in (11, 22, 33, 44, 55)]
    ents = ["geometry_common", "geometry_best_constant"] + hist
    data, rows = {}, []
    for e in ents:
        for b in BS:
            for ps in PS:
                p = R / "repeatability" / f"b{b}" / f"p{ps}" / e / f"{e}.jsonl"
                rr = {r["case_id"]: r for r in jl(p)}
                if set(rr) != set(ids):
                    raise SystemExit(f"{p}: {len(rr)} of {len(ids)} cases")
                data[(e, b, ps)] = rr
                o = orig[e]
                rows.append({"entry": e, "batch": b, "process_seed": ps, "success": sum(rr[c]["success"] for c in ids),
                             "terminal_equal_original": sum(rr[c]["terminal_reason"] == o[c]["terminal_reason"] for c in ids),
                             "success_equal_original": sum(rr[c]["success"] == o[c]["success"] for c in ids),
                             "observation_error_equal": all(rr[c]["observation_error"] == o[c]["observation_error"] for c in ids),
                             "invalid_resets": sum(not rr[c]["reset_valid"] for c in ids)})
    between = {}
    for e in ents:
        for b in BS:
            ref = data[(e, b, PS[0])]
            between[f"{e}|b{b}"] = [sum(data[(e, b, p)][c]["terminal_reason"] == ref[c]["terminal_reason"] for c in ids) for p in PS[1:]]
        between[f"{e}|b1_vs_b23"] = [sum(data[(e, 1, p)][c]["terminal_reason"] == data[(e, 23, p)][c]["terminal_reason"] for c in ids) for p in PS]
    conds = sorted({c["condition"] for c in sub})
    order = [sorted([c for c in sub if c["condition"] == k], key=lambda c: c["base_case_id"]) for k in conds]

    def arr(e, b, ps_list):
        return np.array([[[np.mean([data[(e, b, p)][c["case_id"]]["success"] for p in ps_list]) for c in cs] for cs in order]])

    eff = []
    for b in BS:
        for ps in list(PS) + ["mean_of_3"]:
            psl = PS if ps == "mean_of_3" else (ps,)
            A = np.concatenate([arr(h, b, psl) for h in hist])
            B = arr("geometry_common", b, psl)
            r = paired_effect(A, B, repeats=10000, seed=6455401)
            eff.append({"batch": b, "process": ps, "comparison": "combined_robust_history - geometry_common", **r})
    out = {"cases": len(ids), "episodes": len(rows) * len(ids), "per_run": rows, "between_process_terminal_equal": between,
           "paired_effects": eff,
           "note": "65-case subset; processes averaged within case before resampling; training seeds are the replicates"}
    (O / "repeatability.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"episodes": out["episodes"], "effects": [(x["batch"], x["process"], round(x["difference_pp"], 2),
                                                                round(x["ci_low_pp"], 2), round(x["ci_high_pp"], 2)) for x in eff]}, indent=1))


if __name__ == "__main__":
    main()
