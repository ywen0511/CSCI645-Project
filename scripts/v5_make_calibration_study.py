#!/usr/bin/env python3
"""Generate and freeze the V5 Study A inputs (matched calibration ablation) on CPU, before any outcome exists.

Study A asks whether the calibrated giver reference itself improves success when EMA filtering and the
alignment bound are held fixed, on fresh held-out cases. V4's headline (fixed 5.5% -> calibrated 94.5% on
grasp_15mm) changed three settings at once: reference (fixed -> 0.5 s calibration), EMA alpha (1.0 -> 0.2)
and alignment bound (15 -> 25 mm). Study A crosses all three in a 2 x 2 x 2 factorial of training-free
geometry controllers, so each factor's contribution is estimated on cases nobody has seen.

python scripts/v5_make_calibration_study.py            # writes configs/v5/calibration/*
python scripts/v5_make_calibration_study.py --check    # regenerate in memory and compare with the committed files

Standard library only (imports the V4 case generator, which is standard-library only).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from csci645_handover import v4_protocol as v4  # noqa: E402

OUT = ROOT / "configs/v5/calibration"
SPLIT_SEED = 6457301          # new; disjoint from every V1-V4 split/analysis/process seed
ANALYSIS_SEED = 6457401
PROCESS_SEEDS = {"primary": 6457501, "repeat": 6457502}
COUNT = 200
PREFIX = "v5cal"
SUITE_NAME = "suite_heldout.jsonl"
SENSOR = {"bias_bound_m": 0.005, "noise_std_m": 0.002, "delay_steps": 2, "max_delay_steps": 8,
          "clean_probability": 0.25}  # identical to the V4 final baseline matrices except ema_alpha
TRACE = [f"{PREFIX}-heldout-{c}-0000" for c in ("mixed_id", "grasp_15mm", "grasp_10mm", "mixed_ood", "clean")]
REFERENCES = {"fixed": None, "cal050": 0.5}
ALPHAS = {"ema1p0": 1.0, "ema0p2": 0.2}
BOUNDS = {"a15": 0.015, "a25": 0.025}


def config_id(ref, alpha, bound):
    return f"{alpha}_{ref}_{bound}"


def configurations():
    rows = []
    for alpha in ALPHAS:
        for ref in REFERENCES:
            for bound in BOUNDS:
                rows.append({"id": config_id(ref, alpha, bound), "reference": ref, "ema": alpha, "bound": bound,
                             "ema_alpha": ALPHAS[alpha], "giver_calibration_window_s": REFERENCES[ref],
                             "align_max_m": BOUNDS[bound]})
    return rows


def suite_rows():
    return v4.make_cases("heldout", v4.CONDITIONS, v4.ORDER, count=COUNT, seed=SPLIT_SEED, prefix=PREFIX)


def suite_bytes():
    return "".join(json.dumps(r, sort_keys=True) + "\n" for r in suite_rows()).encode()


def matrix(alpha, process):
    entries = []
    for c in configurations():
        if c["ema"] != alpha:
            continue
        overrides = {"align_max": c["align_max_m"]}
        if c["giver_calibration_window_s"] is not None:
            overrides["giver_calibration_window_s"] = c["giver_calibration_window_s"]
        entries.append({"id": c["id"], "method": "geometry", "overrides": overrides, "trace": process == "primary"})
    return {"name": f"v5_calibration_{alpha}_{process}", "suite": f"configs/v5/calibration/{SUITE_NAME}",
            "num_envs": 240, "protocol": "configs/v2/protocol.json",
            "base_overrides": {"observation_sensor": {**SENSOR, "ema_alpha": ALPHAS[alpha]},
                               "observation_giver_reference": True, "grasp_uncertainty": True},
            "trace_cases": TRACE if process == "primary" else [], "entries": entries}


def repeat_matrix():
    """Second, independent evaluation process for the two primary arms only (run-to-run agreement)."""
    m = matrix("ema0p2", "repeat")
    m["entries"] = [e for e in m["entries"] if e["id"] in ("ema0p2_fixed_a25", "ema0p2_cal050_a25")]
    return m


def analysis_plan(suite_sha):
    return {
        "status": "PREREGISTERED on CPU before any Study A outcome was generated; see FREEZE.json. "
                  "Any deviation must be recorded in docs/v5/DECISIONS.md and labelled in the report.",
        "study": "V5 Study A - matched calibration ablation on fresh held-out cases",
        "research_question": "With EMA alpha and alignment bound held fixed, does the 0.5 s calibrated giver reference "
                             "improve handover success over the fixed nominal giver transform?",
        "suite": {"path": f"configs/v5/calibration/{SUITE_NAME}", "sha256": suite_sha, "cases": COUNT * len(v4.ORDER),
                  "per_condition": COUNT, "conditions": v4.ORDER, "split_seed": SPLIT_SEED,
                  "generator": "scripts/v5_make_calibration_study.py (V4 make_cases, prefix v5cal)",
                  "note": "Same condition definitions as the V4 final suite; new base cases, grasp draws and sensor seeds."},
        "configurations": configurations(),
        "factor_levels": {"reference": list(REFERENCES), "ema": list(ALPHAS), "bound": list(BOUNDS)},
        "anchors": {"historical_fixed_geometry_v4": "ema1p0_fixed_a15", "calibrated_geometry_v4": "ema0p2_cal050_a25"},
        "process_seeds": PROCESS_SEEDS,
        "success_definition": "Unchanged V4 definition: receiver holds independently for 2 s within the 8 s episode; "
                              "prohibited terminal collision, drop, release timeout and episode timeout are failures.",
        "denominator": "All scheduled cases. Invalid resets count as failures. No case is excluded from the primary analysis.",
        "primary": {
            "contrasts": [
                {"id": "A1", "condition": "mixed_id", "left": "ema0p2_cal050_a25", "right": "ema0p2_fixed_a25"},
                {"id": "A2", "condition": "grasp_15mm", "left": "ema0p2_cal050_a25", "right": "ema0p2_fixed_a25"}],
            "estimand": "left minus right success rate, percentage points, on the 200 paired base cases",
            "interval": "paired base-case bootstrap, 10,000 draws, seed 6457401, percentile; report 95% and the "
                        "Bonferroni 97.5% interval (two primary contrasts)",
            "decision_rule": "A contrast supports a calibration-only improvement if and only if its 97.5% interval "
                             "lower bound is > 0. A lower bound of exactly 0 or below is 'not established'. "
                             "No equivalence claim is made in either case."},
        "secondary": {
            "factorial_main_effects": "For each factor, the mean over the four combinations of the other two factors "
                                      "of (level B minus level A), on mixed_id, grasp_15mm and mixed_ood separately; "
                                      "same bootstrap, 95% intervals, exploratory and unadjusted.",
            "two_way_interactions": "reference x ema and reference x bound, difference-in-differences, exploratory.",
            "v4_replication": "ema0p2_cal050_a25 minus ema1p0_fixed_a15 on mixed_id and grasp_15mm; compares with the "
                              "published V4 final contrast; exploratory.",
            "all_conditions_table": "Success, exclusive terminal reasons and invalid resets for all 8 x 12 cells.",
            "repeatability": "Second evaluation process (seed 6457502) for the two primary arms; report terminal-outcome "
                             "agreement per case. Disagreement does not change the primary analysis, which uses the "
                             "primary process only."},
        "stopping_rules": "Run every configured cell to completion. Do not add conditions, cases or configurations after "
                          "outcomes are seen; any additional analysis is labelled post hoc.",
        "analysis_script": "scripts/v5_calibration_analysis.py",
        "compute_estimate": "19,200 primary + 4,800 repeat geometry-only episodes; no training.",
    }


def files():
    sb = suite_bytes()
    sha = hashlib.sha256(sb).hexdigest()
    out = {SUITE_NAME: sb}
    for alpha in ALPHAS:
        out[f"matrix_{alpha}.json"] = (json.dumps(matrix(alpha, "primary"), indent=1) + "\n").encode()
    out["matrix_repeat_ema0p2.json"] = (json.dumps(repeat_matrix(), indent=1) + "\n").encode()
    out["analysis_plan.json"] = (json.dumps(analysis_plan(sha), indent=1) + "\n").encode()
    freeze = {"frozen_before_outcomes": True, "generator": "scripts/v5_make_calibration_study.py",
              "files": {k: hashlib.sha256(v).hexdigest() for k, v in sorted(out.items())}}
    out["FREEZE.json"] = (json.dumps(freeze, indent=1) + "\n").encode()
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="Fail unless committed files match regeneration.")
    args = parser.parse_args()
    out = files()
    if args.check:
        bad = [k for k, v in out.items() if not (OUT / k).exists() or (OUT / k).read_bytes() != v]
        if bad:
            raise SystemExit(f"FAIL: Study A inputs differ from regeneration: {bad}")
        print(f"PASS: {len(out)} Study A files match regeneration")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in out.items():
        (OUT / name).write_bytes(data)
    print(f"Wrote {len(out)} files to {OUT}")


if __name__ == "__main__":
    main()
