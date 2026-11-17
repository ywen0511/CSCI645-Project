#!/usr/bin/env python3
"""Preregistered analysis of V5 Study A (matched calibration ablation). CPU only; numpy.

python scripts/v5_calibration_analysis.py --records runs/v5/calibration/primary \
    --repeat runs/v5/calibration/repeat --out results/v5/calibration

``--records`` holds the eval_matrix.py outputs of matrix_ema1p0.json and matrix_ema0p2.json (one
``<config id>.jsonl`` per configuration, 2,400 records each). ``--repeat`` holds the outputs of
matrix_repeat_ema0p2.json. The plan is configs/v5/calibration/analysis_plan.json; this script refuses to
run if the frozen inputs changed. Outputs: summary.json and summary.md in --out.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CAL = ROOT / "configs/v5/calibration"
REASONS = ["success", "prohibited_collision", "drop", "episode_timeout", "release_timeout", "invalid_reset"]


def require(ok, msg):
    if not ok:
        raise ValueError(msg)


def load_plan():
    freeze = json.loads((CAL / "FREEZE.json").read_text())
    for name, sha in freeze["files"].items():
        require(hashlib.sha256((CAL / name).read_bytes()).hexdigest() == sha, f"frozen Study A input changed: {name}")
    return json.loads((CAL / "analysis_plan.json").read_text())


def load_suite(plan):
    rows = [json.loads(x) for x in (ROOT / plan["suite"]["path"]).read_text().splitlines()]
    require(len(rows) == plan["suite"]["cases"], "suite size")
    by_cond = {}
    for r in rows:
        by_cond.setdefault(r["condition"], []).append(r)
    order = {c: [r["case_id"] for r in sorted(v, key=lambda r: r["base_case_id"])] for c, v in by_cond.items()}
    return {r["case_id"]: r for r in rows}, order


def load_records(path: Path, config_id: str, suite: dict) -> dict:
    f = path / f"{config_id}.jsonl"
    require(f.exists(), f"missing records for {config_id}: {f}")
    rows = [json.loads(x) for x in f.read_text().splitlines() if x.strip()]
    by_id = {}
    for r in rows:
        cid = r["case_id"]
        require(cid in suite and cid not in by_id, f"{config_id}: unexpected or duplicate {cid}")
        require(r["condition"] == suite[cid]["condition"], f"{config_id}: condition mismatch {cid}")
        require(r.get("source_dirty") is False, f"{config_id}: dirty source")
        require(isinstance(r["success"], bool) and isinstance(r["reset_valid"], bool), f"{config_id}: flags")
        require(r["success"] == (r["terminal_reason"] == "success"), f"{config_id}: success/reason {cid}")
        require(r["reset_valid"] or not r["success"], f"{config_id}: invalid reset scored as success {cid}")
        require(r["terminal_reason"] in REASONS, f"{config_id}: unknown reason {r['terminal_reason']}")
        by_id[cid] = r
    require(set(by_id) == set(suite), f"{config_id}: incomplete ({len(by_id)} of {len(suite)})")
    commits = {r["source_commit"] for r in rows}
    require(len(commits) == 1, f"{config_id}: mixed source commits")
    return by_id


def bootstrap(diff_fn, n, repeats, seed, confidence):
    """Percentile interval of a statistic of resampled base-case indices (paired across all arms)."""
    rng = np.random.default_rng(seed)
    draws = np.array([diff_fn(rng.integers(n, size=n)) for _ in range(repeats)])
    tail = (1 - confidence) / 2
    lo, hi = np.quantile(draws, [tail, 1 - tail])
    return float(lo), float(hi)


def contrast(vectors, weights, repeats, seed):
    """Weighted sum of per-config success vectors (same case order); returns estimate and intervals, in pp."""
    stack = np.array([vectors[k] for k in weights], float)
    w = np.array([weights[k] for k in weights], float)
    stat = lambda idx: float((w @ stack[:, idx].mean(axis=1)) * 100)  # noqa: E731
    n = stack.shape[1]
    est = stat(np.arange(n))
    out = {"difference_pp": est}
    for conf in (0.95, 0.975):
        lo, hi = bootstrap(stat, n, repeats, seed, conf)
        out[f"ci{int(conf * 1000) / 10:g}"] = [lo, hi]
    return out


def main_effect_weights(configs, factor, low, high):
    """Mean over the other factors' combinations of (high - low)."""
    w = {}
    pairs = [c for c in configs if c[factor] == high]
    for c in pairs:
        twin = next(d for d in configs if d[factor] == low and all(d[k] == c[k] for k in ("reference", "ema", "bound") if k != factor))
        w[c["id"]] = w.get(c["id"], 0) + 1 / len(pairs)
        w[twin["id"]] = w.get(twin["id"], 0) - 1 / len(pairs)
    return w


LEVELS = {"reference": ("fixed", "cal050"), "ema": ("ema1p0", "ema0p2"), "bound": ("a15", "a25")}


def interaction_weights(configs, f1, f2):
    """Difference-in-differences (f1 high-low effect at f2 high minus at f2 low), averaged over the third factor."""
    w = {}
    for c in configs:
        s1 = 1 if c[f1] == LEVELS[f1][1] else -1
        s2 = 1 if c[f2] == LEVELS[f2][1] else -1
        w[c["id"]] = w.get(c["id"], 0) + s1 * s2 / (len(configs) / 4)
    return w


def analyse(records_dir: Path, repeat_dir: Path | None, repeats=10000):
    plan = load_plan()
    suite, order = load_suite(plan)
    seed = int(plan["primary"]["interval"].split("seed ")[1].split(",")[0])
    configs = plan["configurations"]
    data = {c["id"]: load_records(records_dir, c["id"], suite) for c in configs}
    vec = {cond: {k: np.array([data[k][i]["success"] for i in ids], float) for k in data} for cond, ids in order.items()}

    table = []
    for c in configs:
        for cond, ids in order.items():
            reasons = {r: sum(data[c["id"]][i]["terminal_reason"] == r for i in ids) for r in REASONS}
            table.append({"config": c["id"], "condition": cond, "n": len(ids),
                          "success_pct": 100 * reasons["success"] / len(ids), "terminal_reasons": reasons})

    primary = []
    for p in plan["primary"]["contrasts"]:
        r = contrast(vec[p["condition"]], {p["left"]: 1, p["right"]: -1}, repeats, seed)
        r["supports_calibration_only_improvement"] = r["ci97.5"][0] > 0
        primary.append({**p, **r})

    secondary = {"main_effects": [], "interactions": [], "v4_replication": []}
    for cond in ("mixed_id", "grasp_15mm", "mixed_ood"):
        for factor, (lo, hi) in LEVELS.items():
            r = contrast(vec[cond], main_effect_weights(configs, factor, lo, hi), repeats, seed)
            secondary["main_effects"].append({"condition": cond, "factor": factor, "effect": f"{hi} minus {lo}", **r})
        for f2 in ("ema", "bound"):
            r = contrast(vec[cond], interaction_weights(configs, "reference", f2), repeats, seed)
            secondary["interactions"].append({"condition": cond, "factors": ["reference", f2], **r})
    a = plan["anchors"]
    for cond in ("mixed_id", "grasp_15mm"):
        r = contrast(vec[cond], {a["calibrated_geometry_v4"]: 1, a["historical_fixed_geometry_v4"]: -1}, repeats, seed)
        secondary["v4_replication"].append({"condition": cond, **r})

    repeat = None
    if repeat_dir is not None:
        repeat = []
        for k in ("ema0p2_fixed_a25", "ema0p2_cal050_a25"):
            other = load_records(repeat_dir, k, suite)
            same = sum(data[k][i]["terminal_reason"] == other[i]["terminal_reason"] for i in suite)
            repeat.append({"config": k, "matching_terminal_outcomes": same, "cases": len(suite)})

    return {"schema": 1, "study": plan["study"], "suite_sha256": plan["suite"]["sha256"],
            "preregistered_plan": "configs/v5/calibration/analysis_plan.json", "bootstrap_repeats": repeats,
            "bootstrap_seed": seed, "primary": primary, "secondary_exploratory": secondary,
            "repeatability": repeat, "cells": table}


def markdown(res):
    lines = ["# V5 Study A - matched calibration ablation (preregistered)", "",
             "| Primary | Condition | Calibrated minus fixed (pp) | 95% CI | 97.5% CI | Calibration-only improvement |",
             "|---|---|---:|---|---|---|"]
    for p in res["primary"]:
        lines.append(f"| {p['id']} | {p['condition']} | {p['difference_pp']:+.1f} | [{p['ci95'][0]:+.1f}, {p['ci95'][1]:+.1f}] | "
                     f"[{p['ci97.5'][0]:+.1f}, {p['ci97.5'][1]:+.1f}] | "
                     f"{'supported' if p['supports_calibration_only_improvement'] else 'not established'} |")
    lines += ["", "Exploratory factorial main effects (95% CI):", "", "| Condition | Factor | Effect (pp) | 95% CI |",
              "|---|---|---:|---|"]
    for m in res["secondary_exploratory"]["main_effects"]:
        lines.append(f"| {m['condition']} | {m['factor']} ({m['effect']}) | {m['difference_pp']:+.1f} | "
                     f"[{m['ci95'][0]:+.1f}, {m['ci95'][1]:+.1f}] |")
    conds = sorted({c["condition"] for c in res["cells"]})
    cfgs = list(dict.fromkeys(c["config"] for c in res["cells"]))
    lines += ["", "Success (%) by configuration and condition:", "", "| Config | " + " | ".join(conds) + " |",
              "|---|" + "---:|" * len(conds)]
    for k in cfgs:
        vals = {c["condition"]: c["success_pct"] for c in res["cells"] if c["config"] == k}
        lines.append(f"| {k} | " + " | ".join(f"{vals[c]:.1f}" for c in conds) + " |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--repeat", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=ROOT / "results/v5/calibration")
    args = parser.parse_args()
    res = analyse(args.records, args.repeat)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(json.dumps(res, indent=1) + "\n")
    (args.out / "summary.md").write_text(markdown(res))
    print(markdown(res))


if __name__ == "__main__":
    main()
