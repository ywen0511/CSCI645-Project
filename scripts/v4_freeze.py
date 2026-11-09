#!/usr/bin/env python3
"""Freeze the V4 protocol (CPU). Two separate steps with separate manifests, so neither invalidates the other.

    python3 scripts/v4_freeze.py freeze        # pre-final inputs -> configs/v4/FREEZE.json (+ frozen protocols, matrices, plan)
    git commit ...; git tag experiment-v4      # simulator source used for every formal run
    python3 scripts/v4_freeze.py final_suite   # final suite from the frozen generator -> configs/v4/FINAL_SUITE.json

`freeze` requires a clean tree, writes the frozen training protocols (configs/v4/frozen/training/), the validation
matrices (step 0 control + candidates), the analysis plan (configs/v4/analysis_plan.json) and FREEZE.json with the
SHA-256 of every input (source, scripts, configs, suites, selections). `final_suite` refuses to run unless every
FREEZE.json input still has its frozen hash, then writes configs/v4/suites/final.jsonl and FINAL_SUITE.json (suite
hash, generator hash, freeze hash). Re-running `final_suite` reproduces the same bytes and never touches FREEZE.json.
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from csci645_handover import v4_protocol as v4  # noqa: E402

CANDIDATE_TAGS = ["step_002031616", "step_004030464", "step_006029312", "step_008028160", "step_010027008"]
TRACE_FINAL = ["v4-final-mixed_id-0000", "v4-final-mixed_id-0001", "v4-final-grasp_15mm-0000", "v4-final-grasp_10mm-0000",
               "v4-final-mixed_ood-0000", "v4-final-clean-0000"]
INPUT_GLOBS = ["src/csci645_handover/**/*.py", "scripts/train.py", "scripts/eval_matrix.py", "scripts/v3_jobs.py",
               "scripts/cluster/isaac_run.sh", "scripts/v4_*.py", "scripts/closeout_inspect_ckpt.py", "scripts/record_video.py",
               "configs/v2/protocol.json", "configs/v4/suites/development.jsonl", "configs/v4/suites/validation.jsonl",
               "configs/v4/suites/SUITES.json", "configs/v4/development/baseline_grid.json",
               "configs/v4/development/baseline_selection.json", "configs/v4/frozen/**/*.json", "configs/v4/analysis_plan.json",
               "configs/v4/video_rule.json", "configs/v2/frozen/pip-freeze.txt"]


def git(*a):
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True, check=True).stdout.strip()


def plan(sel):
    roles = sel["roles"]
    return {
        "status": "frozen with configs/v4/FREEZE.json",
        "research_question": "Where does a giver-reference controller fail when the true object-to-giver translation is "
                             "unknown, and do calibrated geometry, short observation history or learned residuals improve "
                             "handover in that regime?",
        "seeds": {"training": list(v4.TRAINING_SEEDS), "split": v4.SPLIT_SEEDS, "analysis": v4.ANALYSIS_SEED,
                  "evaluation_process": 6456501, "repeatability_process": [6456601, 6456602, 6456603]},
        "conditions": {"final": v4.ORDER, "validation": list(v4.VALIDATION), "per_condition": v4.SPLIT_COUNTS,
                       "definitions": v4.CONDITIONS, "training_support_labels": v4.TRAINING_LABEL,
                       "training_support": v4.TRAIN_SUPPORT},
        "baselines": {r: {k: roles[r][k] for k in ("candidate_id", "ema_alpha", "reference", "align_max_m")}
                      | ({"constant_residual_m": roles[r]["constant_residual_m"]} if "constant_residual_m" in roles[r] else {})
                      for r in ("nominal", "geometry_fixed", "geometry_ema", "geometry_calibrated", "best_constant_geometry")},
        "common_parent": roles["common_parent"]["candidate_id"],
        "learned_profiles": ["combined_clean_ff", "combined_robust_ff", "combined_robust_history", "combined_robust_repeat",
                             "residual_robust_history"],
        "formal_runs": 25, "transitions_per_run": {"requested": 10_000_000, "realized": 10_027_008,
                                                   "rollout": "1,024 envs x 32 steps = 32,768 per PPO iteration"},
        "checkpoint_candidates": CANDIDATE_TAGS, "untrained_control": "step_000000000 (never eligible)",
        "checkpoint_selection": "scripts/v4_select_checkpoints.py: validation mean success (equal weight per condition) desc, "
                                "unsafe-event rate asc, residual magnitude asc, latest candidate; values rounded to 12 decimals; "
                                "validation records only",
        "success_definition": "V3 evaluator unchanged: the receiver holds the bar independently (giver fingers open, no giver "
                              "contact, no table support, bar above drop height, low relative speed) for 2.0 s within the 8 s "
                              "horizon, without a terminal prohibited collision, drop, release timeout or episode timeout",
        "denominator": "all scheduled cases; invalid resets count as non-success for every method and are reported "
                       "separately; systemic reset failures are investigated before any final analysis",
        "exclusions": "none",
        "primary": {"condition": "mixed_id", "checkpoints": "selected",
                    "contrasts": [["combined_robust_history", "combined_robust_ff"],
                                  ["combined_robust_history", "best_constant_geometry"]],
                    "metric": "success percentage-point difference",
                    "inference": "paired hierarchical bootstrap over training seeds and base-case clusters (one base-case "
                                 "draw shared across conditions), 10,000 draws, seed 6456401; 95% intervals and Bonferroni "
                                 "97.5% intervals for the two primary contrasts; deterministic baselines broadcast, never "
                                 "resampled as seeds",
                    "degenerate_intervals": "a zero-width interval with both arms at 100% (or 0%) is reported as a ceiling "
                                            "(floor) result; no equivalence claim (no equivalence margin is prespecified)"},
        "secondary": "all other comparisons, conditions and the final-checkpoint sensitivity analysis are exploratory",
        "metrics": ["success", "terminal reason (exclusive)", "unsafe events (collision or drop)", "drops", "valid reset rate",
                    "completion time of successes", "release delay", "residual mean/max and saturation", "alignment saturation",
                    "calibration error", "achieved grasp offset"],
        "stopping_rules": "no early stopping; every formal run trains for the full budget; a failed run resumes from its "
                          "latest checkpoint (attempts logged); a run that cannot complete after 3 attempts is reported "
                          "incomplete, never replaced by another seed",
        "final_matrix": {"baselines": 5, "learned_entries": 50, "cases": 2400,
                         "logical_episodes": 55 * 2400, "aliases": "only exact identical configurations (declared in "
                                                                   "configs/v4/final_matrices/baseline_aliases.json)"},
        "mechanisms": {"subset": "first 5 base cases (by base_case_id) of every final condition = 60 cases",
                       "interventions": ["zero residual (= parent)", "constant mean residual fitted on development records only",
                                         "history order reversed [3, 2, 1, 0]", "current frame repeated four times",
                                         "untrained step-0 checkpoints"], "seeds": "every selected history run"},
        "repeatability": {"subset": "the 60-case mechanism subset", "batch_sizes": [1, 20], "process_seeds": [6456601, 6456602, 6456603],
                          "entries": ["geometry_calibrated", "best_constant_geometry", "combined_robust_history selected (all seeds)"]},
        "traces": {"cases": TRACE_FINAL, "how": "separate supplementary batch-6 runs; never replace formal records"},
        "compute_budget_gpu_hours": 100,
        "videos": "configs/v4/video_rule.json",
    }


VIDEO_RULE = {
    "status": "frozen before final evaluation",
    "clips": [
        {"id": "nominal_vs_geometry_vs_learned", "rule": "case v4-final-grasp_15mm-0000 for nominal, geometry_fixed, "
         "geometry_calibrated and combined_robust_history (seed 111, selected)"},
        {"id": "unknown_grasp_boundary", "rule": "geometry_fixed on the first grasp_15mm final case (by case_id) whose outcome "
         "is a failure; if none fails, state that and show v4-final-grasp_15mm-0000"},
        {"id": "noisy_calibration", "rule": "geometry_calibrated on v4-final-mixed_ood-0000"},
        {"id": "failure", "rule": "combined_robust_history (selected) on the first mixed_id final case (seed order 111..555, "
         "then case_id) with a non-success outcome; if none exists, record 'no failure' and add no substitute"},
        {"id": "intervention", "rule": "combined_robust_history seed 111 selected with history order reversed on "
         "v4-final-mixed_id-0000"},
        {"id": "learned_mixed_id", "rule": "combined_robust_history seed 111 selected on v4-final-mixed_id-0001"},
        {"id": "ema_noise", "rule": "geometry_ema on v4-final-noise_2mm-0000"},
        {"id": "clean", "rule": "geometry_calibrated on v4-final-clean-0000"},
    ],
    "montage": "all clips in the order above, labelled with method, seed, case, source commit and checkpoint tag",
    "labels": ["method", "training seed", "case id", "condition", "source commit", "checkpoint tag", "outcome"],
}


def freeze():
    if git("status", "--porcelain", "--untracked-files=no"):
        raise SystemExit("freeze requires a clean committed tree")
    sel = json.loads((ROOT / "configs/v4/development/baseline_selection.json").read_text())
    if "best_constant_geometry" not in sel["roles"]:
        raise SystemExit("constant search selection missing")
    fz = ROOT / "configs/v4/frozen"
    (fz / "training").mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    runs = []
    for p in sorted((ROOT / "configs/v4/training").glob("*.json")):
        d = json.loads(p.read_text())
        d.update(status="frozen", frozen_utc=now, protocol_id=d["protocol_id"].replace("v4-final-", "v4-frozen-"))
        (fz / "training" / p.name).write_text(json.dumps(d, indent=1, sort_keys=True) + "\n")
        for seed in d["training"]["seeds"]:
            runs.append((p.stem, d["training"]["methods"][0], seed))
    vd = fz / "matrices/validation"
    vd.mkdir(parents=True, exist_ok=True)
    for prof, method, seed in runs:
        run = f"{prof}_s{seed}"
        ents = [{"id": f"{run}__step0", "method": method, "training_seed": seed, "role": "untrained_control",
                 "checkpoint": f"{run}/checkpoints/step_000000000.pt"}]
        ents += [{"id": f"{run}__{t}", "method": method, "training_seed": seed, "role": "candidate",
                  "checkpoint": f"{run}/checkpoints/{t}.pt"} for t in CANDIDATE_TAGS]
        (vd / f"{run}.json").write_text(json.dumps({"name": f"v4_validation_{run}", "suite": "configs/v4/suites/validation.jsonl",
            "num_envs": 240, "protocol": f"configs/v4/frozen/training/{prof}.json", "trace_cases": [], "entries": ents}, indent=1) + "\n")
    (ROOT / "configs/v4/analysis_plan.json").write_text(json.dumps(plan(sel), indent=1) + "\n")
    (ROOT / "configs/v4/video_rule.json").write_text(json.dumps(VIDEO_RULE, indent=1) + "\n")
    files = sorted({p for g in INPUT_GLOBS for p in ROOT.glob(g) if p.is_file() and "__pycache__" not in p.parts})
    rec = {"freeze_utc": now, "base_commit": git("rev-parse", "HEAD"), "formal_runs": len(runs),
           "runs": [f"{p}_s{s}" for p, _, s in runs], "inputs": {str(p.relative_to(ROOT)): v4.sha256(p) for p in files},
           "final_suite": "generated after this freeze by `scripts/v4_freeze.py final_suite`; see configs/v4/FINAL_SUITE.json",
           "note": "FREEZE.json lists the pre-final inputs only; it never changes after the experiment-v4 tag."}
    (ROOT / "configs/v4/FREEZE.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(f"frozen {len(files)} inputs, {len(runs)} runs")


def final_suite():
    fz = json.loads((ROOT / "configs/v4/FREEZE.json").read_text())
    bad = [p for p, h in fz["inputs"].items() if v4.sha256(ROOT / p) != h]
    if bad:
        raise SystemExit(f"frozen inputs changed: {bad[:5]}")
    rows = v4.make_cases("final", v4.CONDITIONS, v4.ORDER)
    p = ROOT / "configs/v4/suites/final.jsonl"
    v4.write_jsonl(p, rows)
    (ROOT / "configs/v4/FINAL_SUITE.json").write_text(json.dumps({
        "suite": "configs/v4/suites/final.jsonl", "cases": len(rows), "sha256": v4.sha256(p),
        "generator": "src/csci645_handover/v4_protocol.py", "generator_sha256": v4.sha256(ROOT / "src/csci645_handover/v4_protocol.py"),
        "freeze_sha256": v4.sha256(ROOT / "configs/v4/FREEZE.json"), "split_seed": v4.SPLIT_SEEDS["final"],
        "experiment_tag": "experiment-v4", "trace_cases": TRACE_FINAL}, indent=1) + "\n")
    print(len(rows), v4.sha256(p))


if __name__ == "__main__":
    {"freeze": freeze, "final_suite": final_suite}[sys.argv[1]]()
