#!/usr/bin/env python3
"""Write configs/v2/protocol.json from development decisions (run once, before the freeze).

    python3 scripts/make_v2_protocol.py --actor-init zero_mean_output \
        --const-geometry-1p5cm 0.005 --const-geometry-1cm 0.005 --const-nominal 0.005

All task physics, rewards, observations, evaluator thresholds and PPO settings are inherited from the frozen v1
protocol; the v2 changes are listed under ``changes_from_v1``. After writing, run scripts/make_v2_suites.py
heldout and scripts/freeze_v2.py.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CURRICULUM = [
    {"fraction_start": 0.0, "fraction_end": 0.1, "position_bound_m": 0.0, "release_offset_bound_s": 0.0},
    {"fraction_start": 0.1, "fraction_end": 0.3, "position_bound_m": 0.01, "release_offset_bound_s": 0.15},
    {"fraction_start": 0.3, "fraction_end": 0.5, "position_bound_m": 0.015, "release_offset_bound_s": 0.225},
    {"fraction_start": 0.5, "fraction_end": 1.0, "position_bound_m": 0.02, "release_offset_bound_s": 0.30},
]

# (id, v1 structure id, position bound, release offset, relation to v2 training)
FINAL_CONDITIONS = [
    ("clean", "clean", 0.0, 0.0, "in_training (clean; deterministic repeats)"),
    ("position_1cm", "position_in", 0.01, 0.0, "in_training"),
    ("position_2cm", "position_stress", 0.02, 0.0, "in_training (full final-stage range)"),
    ("timing_early_015", "timing_early_in", 0.0, -0.15, "in_training"),
    ("timing_late_015", "timing_late_in", 0.0, 0.15, "in_training"),
    ("joint_early_1cm_015", "joint_early_in", 0.01, -0.15, "in_training"),
    ("joint_late_1cm_015", "joint_late_in", 0.01, 0.15, "in_training"),
    ("joint_early_2cm_030", "joint_early_stress", 0.02, -0.30, "in_training (corner of the final-stage range)"),
    ("joint_late_2cm_030", "joint_late_stress", 0.02, 0.30, "in_training (corner of the final-stage range)"),
    ("position_3cm", None, 0.03, 0.0, "extrapolation (beyond training and validation ranges)"),
    ("joint_early_3cm_045", None, 0.03, -0.45, "extrapolation (beyond training and validation ranges)"),
    ("joint_late_3cm_045", None, 0.03, 0.45, "extrapolation (beyond training and validation ranges)"),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--actor-init", required=True, choices=["default", "zero_mean_output"])
    ap.add_argument("--const-geometry-1p5cm", type=float, required=True)
    ap.add_argument("--const-geometry-1cm", type=float, required=True)
    ap.add_argument("--const-nominal", type=float, required=True)
    ap.add_argument("--output", default=str(ROOT / "configs/v2/protocol.json"))
    a = ap.parse_args()
    v1 = json.loads((ROOT / "configs/frozen/protocol.json").read_text())
    sys_path = str(ROOT / "scripts")
    import sys
    sys.path.insert(0, sys_path)
    from make_v2_suites import VALIDATION_STRATA  # noqa: E402

    tr = copy.deepcopy(v1["training"])
    for k in ("iterations_per_run", "realized_transitions_per_run", "validation_episodes", "validation_every_transitions",
              "checkpoint_selection", "pilot_total_transitions_cap"):
        tr.pop(k, None)
    tr.update({
        "methods": ["residual", "combined", "combined_no_phase"], "seeds": [11, 22, 33],
        "final_transitions_per_run": 10_000_000, "curriculum": CURRICULUM, "actor_init": a.actor_init,
        "transition_definition": v1["training"]["transition_definition"],
        "scored_transitions": "also logged per iteration (environment steps in the SCORED phase, residual active)",
    })
    stronger = {"align_max": 0.015}
    det = {
        "nominal": {"method": "nominal", "overrides": {}},
        "geometry_1cm": {"method": "geometry", "overrides": {"align_max": 0.010}, "role": "historical v1 controller"},
        "geometry_1p5cm": {"method": "geometry", "overrides": {"align_max": 0.015}, "role": "stronger comparator (matches combined)"},
        "const_geometry_1p5cm": {"method": "geometry", "overrides": {"align_max": 0.015, "constant_residual_m": [a.const_geometry_1p5cm, 0.0, 0.0]},
                                 "role": "primary constant control for combined"},
        "const_geometry_1cm": {"method": "geometry", "overrides": {"align_max": 0.010, "constant_residual_m": [a.const_geometry_1cm, 0.0, 0.0]},
                               "role": "diagnostic (original geometry setting)"},
        "const_nominal": {"method": "nominal", "overrides": {"constant_residual_m": [a.const_nominal, 0.0, 0.0]},
                          "role": "constant control for residual"},
    }
    for combo in ("none", "A", "H", "G", "AH", "AG", "HG", "AHG"):
        fl = {"geom_align": "A" in combo, "geom_anchor": "H" in combo, "geom_gate": "G" in combo}
        det[f"ablation_1cm_{combo}"] = {"method": "geometry", "overrides": {"align_max": 0.010, **fl}, "role": "component ablation (1 cm, as in development)"}
        det[f"ablation_1p5cm_{combo}"] = {"method": "geometry", "overrides": {"align_max": 0.015, **fl}, "role": "exploratory component ablation (1.5 cm)"}
    for b in (0.005, 0.010, 0.015, 0.020):
        det[f"bound_{b:.3f}".replace(".", "p")] = {"method": "geometry", "overrides": {"align_max": b}, "role": "alignment-bound sweep"}
    p = {
        "protocol_id": "v2.0",
        "status": "frozen at tag experiment-v2",
        "informed_by_v1": "v2 is designed after seeing v1 results and v2 development diagnostics; new held-out cases address case reuse only",
        "changes_from_v1": [
            "training distribution reaches +-2 cm per axis and +-0.30 s (curriculum below)",
            "combined and combined_no_phase use full geometry with a 1.5 cm alignment bound (env_overrides.align_max)",
            f"actor initialization: {a.actor_init}",
            "checkpoint selection excludes step 0; new tie-breaks (collision rate, residual squared norm, latest)",
            "constant-offset controls and geometry component ablations added as deterministic controllers",
            "records include the full episode return (terminal-step reward added; v1 erratum E2)",
            "12 final conditions (9 v1 structures with fresh draws + 3 extrapolation conditions at +-3 cm)",
        ],
        "env_overrides": stronger,
        "ppo_overrides": v1.get("ppo_overrides") or {},
        "platform": v1["platform"], "policy": v1["policy"],
        "training": tr,
        "selection": {
            "validation_suite": "configs/v2/suites/validation.jsonl",
            "candidates": "first periodic checkpoint at or after 2M, 4M, 6M, 8M and 10M transitions; step 0 excluded (kept as a named untrained control)",
            "rule": ["highest validation success rate (valid resets)", "lowest collision-episode rate",
                     "lowest mean bounded residual squared norm over scored steps", "latest transition count"],
            "both_selected_and_final_evaluated": True,
        },
        "deterministic_controllers": det,
        "constants": {"selected_on": "750 development cases (development + development_feasibility), grid -5..+10 mm in x, y=z=0",
                      "evidence": "results/v2/diagnostics/constants_v2.json",
                      "geometry_1p5cm_x_m": a.const_geometry_1p5cm, "geometry_1cm_x_m": a.const_geometry_1cm,
                      "nominal_x_m": a.const_nominal},
        "evaluation": {
            "deterministic_policy": True, "num_envs": 900,
            "final_suite_seed": 6453026, "validation": {"seed": 6453027, "prefix": "v2val", "strata": VALIDATION_STRATA},
            "development_suite_seed": 6453028,
            "final_conditions": [{"id": i, "v1_structure": v, "position_bound_m": b, "release_offset_s": r,
                                  "relation_to_training": rel, "cases": 200} for i, v, b, r, rel in FINAL_CONDITIONS],
            "groups": {"inner": ["clean", "position_1cm", "timing_early_015", "timing_late_015", "joint_early_1cm_015", "joint_late_1cm_015"],
                       "outer": ["position_2cm", "joint_early_2cm_030", "joint_late_2cm_030"],
                       "extrapolation": ["position_3cm", "joint_early_3cm_045", "joint_late_3cm_045"]},
            "learned_entries": ["selected checkpoint", "final checkpoint", "step-0 (untrained) checkpoint"],
        },
        "analysis": {
            "primary_comparisons": [
                "combined (selected) - geometry_1p5cm",
                "combined (selected) - const_geometry_1p5cm",
                "residual (selected) - nominal",
                "residual (selected) - const_nominal",
                "combined (selected) - combined_no_phase (selected)",
            ],
            "secondary_declared": "the same five comparisons with final checkpoints",
            "exploratory": ["geometry component ablations (1 cm and 1.5 cm) and factorial effects", "alignment-bound sweep",
                            "untrained step-0 vs zero residual", "geometry_1cm and const_geometry_1cm", "per-condition differences"],
            "metric": "episode success over valid resets; also scheduled-case success, drop, collision-episode, timeout and release-timeout rates",
            "uncertainty": "paired two-level bootstrap (10,000 replicates; training seeds within method x shared case IDs), 95% percentile CI; Wilson intervals for single-controller rates",
            "summaries": "per seed, per condition, per group (inner / outer / extrapolation / all) and equal-condition means",
            "multiplicity": "five primary comparisons; Holm-adjusted bootstrap sign p-values reported alongside unadjusted CIs",
        },
        "video_rule": "configs/v2/video_rule.json",
    }
    Path(a.output).write_text(json.dumps(p, indent=1, sort_keys=True) + "\n")
    print(f"wrote {a.output}")


if __name__ == "__main__":
    main()
