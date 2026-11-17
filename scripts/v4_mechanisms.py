#!/usr/bin/env python3
"""Aggregate V4 mechanism checks and repeatability (CPU; standard library + numpy).

    python3 scripts/v4_mechanisms.py --runs <runs root> --output results/v4/mechanisms

Inputs (60-case subset = first 5 base cases per final condition):
  mechanisms/parents/{parent_zero_residual,nominal_zero_residual}.jsonl      zero residual = the parents
  mechanisms/{selected,reversed,current_only,constant}/<run>/<run>__<x>.jsonl  per selected history run
  mechanisms/zero/<profile>/<profile>_s111__step0.jsonl                     untrained step-0 controls
  repeatability/b{6,20}/p{6456601,6456602,6456603}/<entry>/<entry>.jsonl
  results/v4/mechanisms/constant_fits.json                                  development-fitted constants
Outputs mechanisms.json (per run: successes per intervention and per-case outcome agreement with the selected
policy; residual statistics) and repeatability.json (outcome/success agreement across batch sizes and process
seeds against the first configuration; every disagreement listed).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
INTERVENTIONS = ("selected", "reversed", "current_only", "constant")


def jl(p: Path) -> dict:
    return {json.loads(l)["case_id"]: json.loads(l) for l in p.read_text().splitlines() if l.strip()}


def outcome_cmp(a: dict, b: dict) -> dict:
    common = sorted(set(a) & set(b))
    diff = [c for c in common if a[c]["terminal_reason"] != b[c]["terminal_reason"]]
    return {"cases": len(common), "agree": len(common) - len(diff), "disagreements": diff}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--output", default=str(ROOT / "results/v4/mechanisms"))
    a = ap.parse_args()
    R, O = Path(a.runs), Path(a.output)
    O.mkdir(parents=True, exist_ok=True)
    fits = json.loads((ROOT / "results/v4/mechanisms/constant_fits.json").read_text())
    M = R / "mechanisms"
    parents = {"geometry": jl(M / "parents/parent_zero_residual.jsonl"), "nominal": jl(M / "parents/nominal_zero_residual.jsonl")}
    out = {"subset_cases": len(parents["geometry"]), "parents": {k: sum(r["success"] for r in v.values()) for k, v in parents.items()},
           "runs": {}, "untrained_controls": {}}
    for run in sorted(fits):
        prof = run.rsplit("_s", 1)[0]
        recs = {}
        for x in INTERVENTIONS:
            p = M / x / run / f"{run}__{x}.jsonl"
            recs[x] = jl(p)
        par = parents["geometry" if prof.startswith("combined") else "nominal"]
        sel = recs["selected"]
        res = np.array([r["residual_mean_xyz_m"] for r in sel.values()])
        out["runs"][run] = {
            "success": {x: sum(r["success"] for r in v.values()) for x, v in recs.items()} | {"zero_residual_parent": sum(r["success"] for r in par.values())},
            "agreement_with_selected": {x: outcome_cmp(sel, recs[x]) for x in INTERVENTIONS[1:]} | {"zero_residual_parent": outcome_cmp(sel, par)},
            "fitted_constant_m": fits[run]["constant_residual_m"],
            "residual_episode_mean_xyz_m": {"mean": res.mean(0).tolist(), "sd_across_cases": res.std(0).tolist()},
            "residual_abs_max_mean_m": float(np.mean([r["residual_abs_max_m"] for r in sel.values()])),
            "residual_saturated_episode_frac": float(np.mean([r["residual_abs_max_m"] >= 0.02 - 1e-6 for r in sel.values()])),
        }
    for d in sorted((M / "zero").iterdir()):
        f = next(d.glob("*__step0.jsonl"))
        z = jl(f)
        par = parents["geometry" if d.name.startswith("combined") else "nominal"]
        out["untrained_controls"][d.name] = {"success": sum(r["success"] for r in z.values()),
                                             "agreement_with_parent": outcome_cmp(z, par),
                                             "residual_abs_max_m": max(r["residual_abs_max_m"] for r in z.values())}
    (O / "mechanisms.json").write_text(json.dumps(out, indent=1) + "\n")
    rep = {}
    Rp = R / "repeatability"
    for entry_dir in sorted({p.parent.name for p in Rp.glob("b*/p*/*/*.jsonl")}):
        cfgs = {}
        for f in sorted(Rp.glob(f"b*/p*/{entry_dir}/*.jsonl")):
            if f.name == "eval_runs.jsonl":
                continue
            cfgs[f"{f.parts[-4]}/{f.parts[-3]}"] = jl(f)
        ref_key = sorted(cfgs)[0]
        ref = cfgs[ref_key]
        rep[entry_dir] = {"reference": ref_key, "configurations": {k: {"success": sum(r["success"] for r in v.values()), "cases": len(v),
                                                                        **outcome_cmp(ref, v)} for k, v in cfgs.items()}}
        rep[entry_dir]["all_agree"] = all(v["agree"] == v["cases"] for v in rep[entry_dir]["configurations"].values())
    tot = sum(len(v["configurations"]) * 60 for v in rep.values())
    agree = sum(c["agree"] for v in rep.values() for c in v["configurations"].values())
    (O / "repeatability.json").write_text(json.dumps({"entries": rep, "episodes": tot, "agree_with_reference": agree}, indent=1) + "\n")
    print(json.dumps({"runs": len(out["runs"]), "controls": len(out["untrained_controls"]), "repeatability_episodes": tot,
                      "repeatability_agree": agree}))


if __name__ == "__main__":
    main()
