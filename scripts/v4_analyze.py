#!/usr/bin/env python3
"""Validate every declared V4 final raw file and produce counts, metrics and paired effects (CPU; numpy).

    python3 scripts/v4_analyze.py --index configs/v4/final_matrix_index.json --root <runs root> --output results/v4/summary

Index schema as V3 (scripts/v3_analyze.py): {"suite", "entries": [{"family", "seed", "role", "records", "sha256",
"expected": {entry_id, suite_hash, config_hash, controller_hash, checkpoint_sha256, source_commit, source_dirty},
"alias_of"?}]}. Baselines: role "baseline", seed null. Learned: role "selected" / "final".

Statistics (frozen in configs/v4/analysis_plan.json): paired hierarchical bootstrap over training seeds and
base-case clusters (one base-case draw shared across conditions; conditions are fixed strata), 10,000 draws,
seed 6456401; a deterministic baseline is broadcast, never resampled as fake seeds; Bonferroni 97.5% intervals
for the two primary contrasts (mixed_id, selected checkpoints). A zero-width interval with both arms at 100%
(or 0%) is labelled degenerate (ceiling/floor); no equivalence claim is made.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from csci645_handover.v3_analysis import paired_effect  # noqa: E402
from csci645_handover import v4_protocol as v4  # noqa: E402

TERMINAL = ("success", "prohibited_collision", "drop", "release_timeout", "episode_timeout")
SEED = v4.ANALYSIS_SEED
FAMILIES = ("combined_clean_ff", "combined_robust_ff", "combined_robust_history", "combined_robust_repeat", "residual_robust_history")
BASELINES = ("nominal", "geometry_fixed", "geometry_ema", "geometry_calibrated", "best_constant_geometry")
PRIMARY = [("combined_robust_history", "combined_robust_ff"), ("combined_robust_history", "best_constant_geometry")]
SECONDARY = [("combined_robust_ff", "combined_clean_ff"), ("combined_robust_history", "combined_robust_repeat"),
             ("residual_robust_history", "nominal"), ("combined_robust_history", "geometry_calibrated"),
             ("geometry_calibrated", "geometry_fixed"), ("geometry_ema", "geometry_fixed"),
             ("geometry_calibrated", "geometry_ema"), ("combined_robust_ff", "best_constant_geometry")]
BOUND = 0.02


def mean_or_none(v):
    v = [x for x in v if x is not None]
    return float(np.mean(v)) if v else None


def metrics(rows):
    ok = [r for r in rows if r["reset_valid"]]
    cal = [np.abs(np.array(r["calibration_offset_world_m"]) - np.array(r["grasp_offset_achieved_xyz_m"])).max()
           for r in ok if r.get("calibration_offset_world_m") and r.get("grasp_offset_achieved_xyz_m") and r.get("calibration_frames_used")]
    return {"scheduled": len(rows), "valid_resets": len(ok), "invalid_resets": len(rows) - len(ok),
            "success": sum(r["success"] for r in rows),
            **{f"terminal_{k}": sum(r["terminal_reason"] == k for r in rows) for k in TERMINAL},
            "unsafe_events": sum(bool(r["collision"]) or r["terminal_reason"] == "drop" for r in rows),
            "success_rate": float(np.mean([r["success"] for r in rows])),
            "completion_time_success_mean_s": mean_or_none([r["completion_time_s"] for r in rows if r["success"]]),
            "release_delay_mean_s": mean_or_none([r.get("release_delay_s") for r in rows]),
            "residual_abs_mean_m": mean_or_none([r["residual_abs_mean_m"] for r in rows]),
            "residual_abs_max_m": mean_or_none([r["residual_abs_max_m"] for r in rows]),
            "residual_saturated_episode_frac": float(np.mean([r["residual_abs_max_m"] >= BOUND - 1e-6 for r in rows])),
            "geometry_align_saturation_frac": mean_or_none([r["geometry_align_saturation_frac"] for r in rows]),
            "calibration_error_max_axis_mean_m": float(np.mean(cal)) if cal else None,
            "achieved_grasp_offset_abs_mean_m": mean_or_none([float(np.abs(r["grasp_offset_achieved_xyz_m"]).max()) for r in ok]),
            "achieved_minus_requested_max_m": max((float(np.abs(np.array(r["grasp_offset_achieved_xyz_m"]) -
                                                                np.array(r["grasp_offset_requested_xyz_m"])).max()) for r in ok), default=None)}


def analyze(root: Path, index_path: Path, output: Path, repeats: int):
    index = json.loads(index_path.read_text())
    suite_path = root / index["suite"] if (root / index["suite"]).exists() else ROOT / index["suite"]
    cases = [json.loads(l) for l in suite_path.read_text().splitlines() if l.strip()]
    conditions = v4.ORDER
    seeds = list(v4.TRAINING_SEEDS)
    required = {(f, r, s) for f in FAMILIES for r in ("selected", "final") for s in seeds} | {(b, "baseline", None) for b in BASELINES}
    supplied = [(e["family"], e["role"], e["seed"]) for e in index["entries"]]
    if len(supplied) != len(set(supplied)) or set(supplied) != required:
        raise ValueError("final matrix must contain exactly 25 selected + 25 final + 5 baseline logical entries")
    suite_sha = v4.sha256(suite_path)
    groups, counts, recon = {}, [], []
    for e in index["entries"]:
        exp = e["expected"]
        if exp["source_dirty"] is not False or exp["suite_hash"] != suite_sha:
            raise ValueError("dirty source or suite hash mismatch in index")
        path = root / e["records"]
        if v4.sha256(path) != e["sha256"]:
            raise ValueError(f"raw-file checksum mismatch: {path}")
        rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
        chk = v4.validate_records(rows, cases, {**exp, "training_seed": e["seed"]}, complete=True)
        recon.append({"family": e["family"], "role": e["role"], "seed": e["seed"], "records": e["records"],
                      "alias_of": e.get("alias_of"), **chk})
        groups[(e["family"], e["role"], e["seed"])] = {r["case_id"]: r for r in rows}
        for c in conditions:
            sel = [r for r in rows if r["condition"] == c]
            counts.append({"family": e["family"], "role": e["role"], "seed": e["seed"], "condition": c,
                           "alias_of": e.get("alias_of"), **metrics(sel)})
    output.mkdir(parents=True, exist_ok=True)
    with (output / "per_seed_condition.csv").open("w") as f:
        w = csv.DictWriter(f, fieldnames=list(counts[0]))
        w.writeheader()
        w.writerows(counts)

    def seeds_for(fam, role):
        return sorted([s for f, r, s in groups if f == fam and r == role], key=lambda s: -1 if s is None else s)

    def array(fam, role, ss, subset):
        order = [sorted([c for c in cases if c["condition"] == cond], key=lambda c: c["base_case_id"]) for cond in subset]
        clusters = [[c["base_case_id"] for c in cs] for cs in order]
        if any(cs != clusters[0] for cs in clusters):
            raise ValueError("unaligned base-case clusters")
        return np.array([[[groups[(fam, role, s)][c["case_id"]]["success"] for c in cs] for cs in order] for s in ss], dtype=float)

    effects = []
    for role in ("selected", "final"):
        for left, right in PRIMARY + SECONDARY:
            primary = (left, right) in PRIMARY
            lr = "baseline" if left in BASELINES else role
            rr = "baseline" if right in BASELINES else role
            if role == "final" and lr == rr == "baseline":
                continue
            ls, rs = seeds_for(left, lr), seeds_for(right, rr)
            if ls != [None] and rs != [None]:
                ls = rs = sorted(set(ls) & set(rs))
            subsets = [[c] for c in conditions] + [[c for c in conditions if c != "clean"]]
            for subset in subsets:
                a, b = array(left, lr, ls, subset), array(right, rr, rs, subset)
                res = paired_effect(a, b, repeats=repeats, seed=SEED)
                both = (a.mean(), b.mean())
                res["degenerate"] = bool(res["ci_low_pp"] == res["ci_high_pp"] and both[0] in (0.0, 1.0) and both[0] == both[1])
                res["left_success_pct"], res["right_success_pct"] = float(both[0] * 100), float(both[1] * 100)
                row = {"left": left, "right": right, "role": role, "conditions": subset, "left_role": lr, "right_role": rr,
                       "primary": primary and role == "selected" and subset == ["mixed_id"],
                       "exploratory": not (primary and role == "selected" and subset == ["mixed_id"]),
                       "training_seeds_left": ls, "training_seeds_right": rs, **res}
                if row["primary"]:
                    row["bonferroni_97_5"] = paired_effect(a, b, repeats=repeats, seed=SEED, confidence=0.975)
                effects.append(row)
    (output / "paired_effects.json").write_text(json.dumps(effects, indent=1) + "\n")
    fam = {}
    for row in counts:
        fam.setdefault((row["family"], row["role"], row["condition"]), []).append(row)
    summary = []
    for (f, r, c), rows_ in sorted(fam.items()):
        rates = [x["success_rate"] for x in rows_]
        summary.append({"family": f, "role": r, "condition": c, "seeds": [x["seed"] for x in rows_],
                        "success_rate_mean": float(np.mean(rates)),
                        "success_rate_sd": float(np.std(rates, ddof=1)) if len(rates) > 1 else None,
                        "success_rate_per_seed": rates, "scheduled_per_seed": rows_[0]["scheduled"],
                        "invalid_resets_total": sum(x["invalid_resets"] for x in rows_),
                        "unsafe_events_mean": float(np.mean([x["unsafe_events"] for x in rows_])),
                        "terminal_mean": {k: float(np.mean([x[f"terminal_{k}"] for x in rows_])) for k in TERMINAL},
                        "completion_time_success_mean_s": mean_or_none([x["completion_time_success_mean_s"] for x in rows_]),
                        "residual_abs_mean_m": mean_or_none([x["residual_abs_mean_m"] for x in rows_]),
                        "residual_saturated_episode_frac": mean_or_none([x["residual_saturated_episode_frac"] for x in rows_]),
                        "calibration_error_max_axis_mean_m": mean_or_none([x["calibration_error_max_axis_mean_m"] for x in rows_]),
                        "achieved_grasp_offset_abs_mean_m": mean_or_none([x["achieved_grasp_offset_abs_mean_m"] for x in rows_]),
                        "training_support": v4.TRAINING_LABEL[c], "alias_of": rows_[0].get("alias_of")})
    (output / "family_condition_summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    tot = {"logical_entries": len(index["entries"]), "logical_episodes": len(index["entries"]) * len(cases),
           "executed_entries": len({e["records"] for e in index["entries"]}),
           "executed_episodes": len({e["records"] for e in index["entries"]}) * len(cases),
           "invalid_resets": sum(r["invalid_resets"] for r in recon if not r["alias_of"]),
           "infra_errors": sum(r["infra_errors"] for r in recon if not r["alias_of"])}
    (output / "reconciliation.json").write_text(json.dumps({"totals": tot, "entries": recon}, indent=1) + "\n")
    (output / "analysis_manifest.json").write_text(json.dumps({
        "index_sha256": v4.sha256(index_path), "suite_sha256": suite_sha, "bootstrap_seed": SEED, "repeats": repeats,
        "bootstrap": "paired training seeds x shared base-case clusters; fixed condition strata; deterministic baselines broadcast",
        "outputs": {p.name: v4.sha256(p) for p in sorted(output.iterdir()) if p.is_file() and p.name != "analysis_manifest.json"}},
        indent=1) + "\n")
    print(json.dumps(tot))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--index", required=True)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--output", type=Path, default=ROOT / "results/v4/summary")
    ap.add_argument("--bootstrap-repeats", type=int, default=10000)
    a = ap.parse_args()
    analyze(a.root, Path(a.index), a.output, a.bootstrap_repeats)
