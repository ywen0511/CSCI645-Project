#!/usr/bin/env python3
"""Preregistered analysis of V5 Study B (dynamic in-grasp slip). CPU only; numpy.

python scripts/v5_slip_analysis.py --runs <runs root> --out results/v5/slip/analysis \
    [--v4-raw-final downloads/raw-final.tar.gz]

``--runs`` holds the runner outputs: final/baselines/<role>.jsonl, final/<run>/<run>__{selected,final}.jsonl,
repeat/baselines/<role>.jsonl, repeat/<run>/<run>__selected.jsonl, regression/<run>/<run>__selected.jsonl and
mechanisms/{parent,selected,reversed,current_only,constant}/... . The plan is configs/v5/slip/analysis_plan.json;
this script refuses to run if any input frozen in configs/v5/slip/FREEZE.json changed. The primary interval is
``scripts/final_review_audit.py::paired_bootstrap`` (training seed x base case; deterministic controllers broadcast
over seeds), 10,000 draws, seed 6458401. Outputs summary.json and summary.md in --out.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tarfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from final_review_audit import paired_bootstrap  # noqa: E402
from v5_taxonomy_records import summarize as taxonomy  # noqa: E402

SL = ROOT / "configs/v5/slip"
PROFILES = ("slip_robust_ff", "slip_robust_history", "slip_robust_repeat")
V4_FAMILY = {"slip_robust_ff": "combined_robust_ff", "slip_robust_history": "combined_robust_history",
             "slip_robust_repeat": "combined_robust_repeat"}
REASONS = ("success", "prohibited_collision", "drop", "episode_timeout", "release_timeout", "invalid_reset",
           "invalid_slip")


def require(ok, msg):
    if not ok:
        raise ValueError(msg)


def check_freeze():
    frozen = json.loads((SL / "FREEZE.json").read_text())["inputs"]
    for k, v in frozen.items():
        require((ROOT / k).is_file() and hashlib.sha256((ROOT / k).read_bytes()).hexdigest() == v,
                f"frozen Study B input changed: {k}")
    return json.loads((SL / "analysis_plan.json").read_text())


def load_suite(path: Path):
    rows = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    by_cond = {}
    for r in rows:
        by_cond.setdefault(r["condition"], []).append(r)
    order = {c: [r["case_id"] for r in sorted(v, key=lambda r: r["base_case_id"])] for c, v in by_cond.items()}
    return {r["case_id"]: r for r in rows}, order


def load_records(path: Path, suite: dict, *, expect_seed=None) -> dict:
    require(path.exists(), f"missing records {path}")
    rows = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    by = {}
    for r in rows:
        cid = r["case_id"]
        require(cid in suite and cid not in by, f"{path.name}: unexpected or duplicate {cid}")
        require(r["condition"] == suite[cid]["condition"], f"{path.name}: condition mismatch {cid}")
        require(r.get("source_dirty") is False, f"{path.name}: dirty source")
        require(r["terminal_reason"] in REASONS, f"{path.name}: unknown reason {r['terminal_reason']}")
        require(r["success"] == (r["terminal_reason"] == "success"), f"{path.name}: success/reason {cid}")
        require(r["reset_valid"] or not r["success"], f"{path.name}: invalid reset scored as success")
        for k in ("slip_xyz_m", "slip_onset_s"):
            if k in suite[cid] and k in r:
                require(r[k] == suite[cid][k], f"{path.name}: {k} differs from the suite for {cid}")
        if expect_seed is not None:
            require(r.get("training_seed") == expect_seed, f"{path.name}: training seed")
        by[cid] = r
    require(set(by) == set(suite), f"{path.name}: incomplete ({len(by)} of {len(suite)})")
    require(len({r["source_commit"] for r in rows}) == 1, f"{path.name}: mixed source commits")
    return by


def matrix(recs: list[dict], ids: list[str]) -> np.ndarray:
    return np.array([[float(r[i]["success"]) for i in ids] for r in recs])


def boot(left, right, seed, repeats):
    out = {}
    for conf in (0.95, 0.975):
        b = paired_bootstrap(left, right, confidence=conf, repeats=repeats, seed=seed)
        out["difference_pp"] = b["difference_pp"]
        out[f"ci{int(conf * 1000) / 10:g}"] = [b["ci_low_pp"], b["ci_high_pp"]]
    return out


def analyse(runs: Path, v4_raw: Path | None = None, repeats: int = 10000) -> dict:
    plan = check_freeze()
    suite, order = load_suite(ROOT / plan["suites"]["final"]["path"])
    seed = int(plan["seeds"]["analysis"])
    seeds = plan["learned"]["seeds"]
    aliases = json.loads((SL / "matrices/final_baselines/aliases.json").read_text())["declared_aliases"]
    roles = plan["training_free"]["roles"]
    base = {}
    for role in roles:
        src = aliases.get(role, role)
        base[role] = load_records(runs / "final/baselines" / f"{src}.jsonl", suite)
    learned = {p: {k: [load_records(runs / f"final/{p}_s{s}" / f"{p}_s{s}__{k}.jsonl", suite, expect_seed=s) for s in seeds]
                   for k in ("selected", "final")} for p in PROFILES}

    def arm(name, ckpt="selected"):
        return learned[name][ckpt] if name in learned else [base[name]]

    # ------------------------------------------------------------ primary
    primary = []
    pc = plan["primary"]["condition"]
    for c in plan["primary"]["contrasts"]:
        r = boot(matrix(arm(c["left"]), order[pc]), matrix(arm(c["right"]), order[pc]), seed, repeats)
        r["superiority_established"] = r["ci97.5"][0] > 0
        primary.append({**c, "condition": pc, **r})

    # ------------------------------------------------------------ cells (every method x condition)
    cells = []
    methods = [(r, "baseline") for r in roles] + [(p, k) for p in PROFILES for k in ("selected", "final")]
    for name, kind in methods:
        recs = arm(name, kind if kind != "baseline" else "selected")
        for cond, ids in order.items():
            m = matrix(recs, ids)
            pooled = [rr[i] for rr in recs for i in ids]
            cells.append({"method": name, "checkpoints": kind, "condition": cond, "n": int(m.size),
                          "success_pct": float(m.mean() * 100),
                          "per_seed_success_pct": [float(x) for x in (m.mean(axis=1) * 100)],
                          "terminal_reasons": {k: sum(r["terminal_reason"] == k for r in pooled) for k in REASONS}})

    # ------------------------------------------------------------ secondary / exploratory
    sec = {"contrasts": []}
    pairs = [("B1", "slip_robust_history", "slip_robust_ff", "selected"),
             ("B2", "slip_robust_history", "geometry_best", "selected"),
             ("repeat_minus_ff", "slip_robust_repeat", "slip_robust_ff", "selected"),
             ("history_minus_repeat", "slip_robust_history", "slip_robust_repeat", "selected"),
             ("tracking_minus_calibrated", "geometry_tracking", "geometry_calibrated", None),
             ("history_minus_tracking", "slip_robust_history", "geometry_tracking", "selected"),
             ("ff_minus_calibrated_parent", "slip_robust_ff", "geometry_calibrated", "selected"),
             ("history_minus_calibrated_parent", "slip_robust_history", "geometry_calibrated", "selected")]
    for cid, left, right, ck in pairs:
        for cond, ids in order.items():
            if cid in ("B1", "B2") and cond == pc:
                continue
            r = boot(matrix(arm(left, ck or "selected"), ids), matrix(arm(right, ck or "selected"), ids), seed, repeats)
            sec["contrasts"].append({"id": cid, "left": left, "right": right, "condition": cond, **r})
    for p in PROFILES:
        for cond, ids in order.items():
            r = boot(matrix(learned[p]["final"], ids), matrix(learned[p]["selected"], ids), seed, repeats)
            sec["contrasts"].append({"id": "final_minus_selected", "left": f"{p}:final", "right": f"{p}:selected",
                                     "condition": cond, **r})

    # ------------------------------------------------------------ taxonomy (slip-specific reasons)
    tax = []
    for name, kind in methods:
        recs = arm(name, kind if kind != "baseline" else "selected")
        for cond, ids in order.items():
            tax.append({"method": name, "checkpoints": kind, "condition": cond, **taxonomy([rr[i] for rr in recs for i in ids])})

    # ------------------------------------------------------------ repeatability
    rep = []
    rdir = runs / "repeat"
    if rdir.exists():
        for role in roles:
            if role in aliases:
                continue
            other = load_records(rdir / "baselines" / f"{role}.jsonl", suite)
            rep.append({"entry": role, "cases": len(suite),
                        "matching_terminal_outcomes": sum(base[role][i]["terminal_reason"] == other[i]["terminal_reason"] for i in suite),
                        "matching_success": sum(base[role][i]["success"] == other[i]["success"] for i in suite)})
        for p in PROFILES:
            s = seeds[0]
            other = load_records(rdir / f"{p}_s{s}" / f"{p}_s{s}__selected.jsonl", suite, expect_seed=s)
            mine = learned[p]["selected"][0]
            rep.append({"entry": f"{p}_s{s}__selected", "cases": len(suite),
                        "matching_terminal_outcomes": sum(mine[i]["terminal_reason"] == other[i]["terminal_reason"] for i in suite),
                        "matching_success": sum(mine[i]["success"] == other[i]["success"] for i in suite)})

    # ------------------------------------------------------------ regression on the V4 final suite
    regression = None
    rgdir = runs / "regression"
    if rgdir.exists():
        v4suite, v4order = load_suite(ROOT / plan["suites"]["v4_final_noslip"]["path"])
        regression = {"cells": [], "contrasts": []}
        v4recs = load_v4_selected(v4_raw, v4suite) if v4_raw else None
        for p in PROFILES:
            mine = [load_records(rgdir / f"{p}_s{s}" / f"{p}_s{s}__selected.jsonl", v4suite, expect_seed=s) for s in seeds]
            for cond, ids in v4order.items():
                m = matrix(mine, ids)
                cell = {"method": p, "condition": cond, "success_pct": float(m.mean() * 100), "n": int(m.size)}
                if v4recs is not None:
                    v = matrix(v4recs[V4_FAMILY[p]], ids)
                    cell["v4_selected_success_pct"] = float(v.mean() * 100)
                    regression["contrasts"].append({"id": "v5_slip_minus_v4", "left": p, "right": V4_FAMILY[p],
                                                    "condition": cond, **boot(m, v, seed, repeats)})
                regression["cells"].append(cell)

    # ------------------------------------------------------------ mechanisms
    mech = mechanisms(runs, seeds) if (runs / "mechanisms/selected").exists() else None

    return {"schema": 1, "study": plan["study"], "preregistered_plan": "configs/v5/slip/analysis_plan.json",
            "suite_sha256": plan["suites"]["final"]["sha256"], "bootstrap_repeats": repeats, "bootstrap_seed": seed,
            "declared_aliases": aliases, "primary": primary, "secondary_exploratory": sec, "cells": cells,
            "taxonomy": tax, "repeatability": rep, "regression_exploratory": regression, "mechanisms": mech}


def load_v4_selected(archive: Path, suite: dict) -> dict:
    index = json.loads((ROOT / "configs/v4/final_matrix_index.json").read_text())
    out = {}
    with tarfile.open(archive) as tar:
        for fam in V4_FAMILY.values():
            ents = sorted([e for e in index["entries"] if e["family"] == fam and e["role"] == "selected"], key=lambda e: e["seed"])
            require(len(ents) == 5, f"{fam}: expected five selected V4 runs")
            recs = []
            for e in ents:
                raw = tar.extractfile(tar.getmember(e["records"])).read()
                require(hashlib.sha256(raw).hexdigest() == e["sha256"], f"V4 record checksum: {e['records']}")
                rows = {json.loads(x)["case_id"]: json.loads(x) for x in raw.splitlines()}
                require(set(rows) == set(suite), f"V4 records incomplete: {e['records']}")
                recs.append(rows)
            out[fam] = recs
    return out


def mechanisms(runs: Path, seeds) -> dict:
    sub = [json.loads(x) for x in (SL / "suites/final_subset60.jsonl").read_text().splitlines() if x.strip()]
    suite = {r["case_id"]: r for r in sub}
    ids = [r["case_id"] for r in sub]
    parent = load_records(runs / "mechanisms/parent/parent_zero_residual.jsonl", suite)
    out = {"subset": "configs/v5/slip/suites/final_subset60.jsonl", "cases": len(ids),
           "parent_zero_residual_successes": sum(parent[i]["success"] for i in ids), "runs": {}}
    for s in seeds:
        run = f"slip_robust_history_s{s}"
        res = {}
        sel = load_records(runs / f"mechanisms/selected/{run}" / f"{run}__selected.jsonl", suite)
        for name in ("selected", "reversed", "current_only", "constant"):
            r = load_records(runs / f"mechanisms/{name}/{run}" / f"{run}__{name}.jsonl", suite)
            res[name] = {"successes": sum(r[i]["success"] for i in ids),
                         "outcome_agreement_with_selected": sum(r[i]["terminal_reason"] == sel[i]["terminal_reason"] for i in ids)}
        out["runs"][run] = res
    return out


def fmt_ci(c):
    return f"[{c[0]:+.1f}, {c[1]:+.1f}]"


def markdown(res: dict) -> str:
    L = ["# V5 Study B - dynamic in-grasp slip (preregistered analysis)", "",
         "| Primary | Contrast | Condition | Difference (pp) | 95% CI | 97.5% CI | Superiority |", "|---|---|---|---:|---|---|---|"]
    for p in res["primary"]:
        L.append(f"| {p['id']} | {p['left']} - {p['right']} | {p['condition']} | {p['difference_pp']:+.1f} | "
                 f"{fmt_ci(p['ci95'])} | {fmt_ci(p['ci97.5'])} | {'established' if p['superiority_established'] else 'not established'} |")
    conds = list(dict.fromkeys(c["condition"] for c in res["cells"]))
    L += ["", "Success (%) by method and condition (learned: five seeds pooled):", "",
          "| Method | Checkpoints | " + " | ".join(conds) + " |", "|---|---|" + "---:|" * len(conds)]
    for m in dict.fromkeys((c["method"], c["checkpoints"]) for c in res["cells"]):
        vals = {c["condition"]: c["success_pct"] for c in res["cells"] if (c["method"], c["checkpoints"]) == m}
        L.append(f"| {m[0]} | {m[1]} | " + " | ".join(f"{vals[c]:.1f}" for c in conds) + " |")
    L += ["", "Exploratory contrasts (95% CI):", "", "| Contrast | Condition | Difference (pp) | 95% CI |", "|---|---|---:|---|"]
    for c in res["secondary_exploratory"]["contrasts"]:
        L.append(f"| {c['id']} ({c['left']} - {c['right']}) | {c['condition']} | {c['difference_pp']:+.1f} | {fmt_ci(c['ci95'])} |")
    if res.get("repeatability"):
        L += ["", "Repeatability (second process, seed 6458601):", "", "| Entry | Matching terminal outcomes |", "|---|---:|"]
        for r in res["repeatability"]:
            L.append(f"| {r['entry']} | {r['matching_terminal_outcomes']}/{r['cases']} |")
    if res.get("regression_exploratory"):
        L += ["", "Regression on the V4 final suite (no slip; selected policies):", "",
              "| Method | Condition | V5 slip-trained (%) | V4 selected (%) |", "|---|---|---:|---:|"]
        for c in res["regression_exploratory"]["cells"]:
            L.append(f"| {c['method']} | {c['condition']} | {c['success_pct']:.1f} | {c.get('v4_selected_success_pct', float('nan')):.1f} |")
    if res.get("mechanisms"):
        m = res["mechanisms"]
        L += ["", f"Mechanisms on {m['cases']} slip_mixed_id cases (parent zero residual: {m['parent_zero_residual_successes']}):", "",
              "| Run | Selected | Reversed | Current only | Dev-fitted constant |", "|---|---:|---:|---:|---:|"]
        for run, r in m["runs"].items():
            L.append(f"| {run} | " + " | ".join(f"{r[k]['successes']} ({r[k]['outcome_agreement_with_selected']})"
                                              for k in ("selected", "reversed", "current_only", "constant")) + " |")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=ROOT / "results/v5/slip/analysis")
    ap.add_argument("--v4-raw-final", type=Path, default=None)
    a = ap.parse_args()
    res = analyse(a.runs, a.v4_raw_final)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "summary.json").write_text(json.dumps(res, indent=1) + "\n")
    (a.out / "summary.md").write_text(markdown(res))
    print(markdown(res))


if __name__ == "__main__":
    main()
