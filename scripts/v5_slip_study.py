#!/usr/bin/env python3
"""V5 Study B (dynamic in-grasp slip): frozen inputs, runner manifests, freeze and checkpoint selection (CPU).

    python3 scripts/v5_slip_study.py suites       # configs/v5/slip/suites/*.jsonl
    python3 scripts/v5_slip_study.py plan         # configs/v5/slip/analysis_plan.json
    python3 scripts/v5_slip_study.py matrices     # pre-training matrices (baselines, validation, baseline repeat)
    python3 scripts/v5_slip_study.py manifests    # results/v5/jobs/{train,validation,final_baselines,repeat_baselines}.json
    python3 scripts/v5_slip_study.py freeze       # configs/v5/slip/FREEZE.json (before any final evaluation)
    python3 scripts/v5_slip_study.py check        # verify every frozen input
    python3 scripts/v5_slip_study.py select --validation <runs>/validation --checkpoint-root <runs>/train
    python3 scripts/v5_slip_study.py post_selection   # learned final / mechanisms / repeat / V4-regression matrices

Every simulator task is a fresh process run by scripts/v3_jobs.py (hash-checked ledger). Paths starting with
$RUNS resolve against the runner's --runs-root, $DELIVERY against the delivery checkout. The post-selection
matrices are a deterministic function of the frozen generator (this file) and the selection records.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from csci645_handover import v4_protocol as v4  # noqa: E402
from csci645_handover import v5_protocol as v5  # noqa: E402

SL = ROOT / "configs/v5/slip"
JOBS = ROOT / "results/v5/jobs"
PROFILES = ("slip_robust_ff", "slip_robust_history", "slip_robust_repeat")
SEEDS = v5.TRAINING_SEEDS
CANDIDATE_TRANSITIONS = (1015808, 2031616, 3014656, 4030464, 5013504, 6029312, 7012352, 8028160, 9011200, 10027008)
CANDIDATES = tuple(f"step_{t:09d}" for t in CANDIDATE_TRANSITIONS)
FINAL_BATCH = 240
TRACE_CONDITIONS = v5.ORDER
SENSOR = {"bias_bound_m": 0.005, "noise_std_m": 0.002, "delay_steps": 2, "max_delay_steps": 8, "ema_alpha": 0.2,
          "clean_probability": 0.25}
BASES = {"a": {"observation_sensor": SENSOR, "observation_giver_reference": True, "grasp_uncertainty": True},
         "fixed": {"observation_sensor": {**SENSOR, "ema_alpha": 1.0}, "observation_giver_reference": True,
                   "grasp_uncertainty": True},
         "ema": {"observation_sensor": SENSOR, "observation_giver_reference": False, "grasp_uncertainty": True}}
ROLES = ("nominal", "geometry_fixed", "geometry_ema", "geometry_calibrated", "geometry_tracking",
         "best_constant_geometry", "geometry_best")


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def jl_write(p: Path, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))


def jl_read(p: Path):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def put(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1) + "\n")
    return rel(p)


def mech_base(group: str) -> dict:
    return {**BASES[group], "slip_mechanism": dict(v5.SLIP_MECHANISM)}


# ------------------------------------------------------------------------------------------------ suites
def suites():
    val = v5.make_cases("validation", order=list(v5.VALIDATION))
    fin = v5.make_cases("final")
    jl_write(SL / "suites/validation.jsonl", val)
    jl_write(SL / "suites/final.jsonl", fin)
    sub = [r for r in fin if r["condition"] == v5.PRIMARY][:60]
    jl_write(SL / "suites/final_subset60.jsonl", sub)
    v4fin = jl_read(ROOT / "configs/v4/suites/final.jsonl")
    reg = []
    for r in v4fin:  # V4 final cases unchanged; zero slip so the slip-trained policies run with their own config
        reg.append({**r, "slip_xyz_m": [0.0, 0.0, 0.0], "slip_onset_s": 0.0, "slip_duration_s": 0.0, "slip_clamped": False})
    jl_write(SL / "suites/v4_final_noslip.jsonl", reg)
    print(len(val), len(fin), len(sub), len(reg))


# ------------------------------------------------------------------------------------------------ plan
def plan():
    sel = json.loads((SL / "development/baseline_selection.json").read_text())
    p = {
        "status": "PREREGISTERED before any Study B final evaluation; frozen in configs/v5/slip/FREEZE.json and tag "
                  "experiment-v5b. Deviations are recorded in docs/v5/DECISIONS.md and labelled in the report.",
        "study": "V5 Study B - dynamic in-grasp slip after the calibration window",
        "research_question": "When the bar slides in the giver's grip after the 0.5 s calibration window has closed and "
                             "before the receiver grasps, does a learned residual with observation history recover better "
                             "than the same residual without history and than the strongest training-free controller?",
        "mechanism": {"source": "src/csci645_handover/core/slip.py", "parameters": v5.SLIP_MECHANISM,
                      "feasible_cumulative_x_m": list(v5.CUMULATIVE_X), "duration_s": v5.SLIP_DURATION_S,
                      "onset_s": list(v5.ONSET_RANGE_S), "probe": "results/v5/slip/probe/summary.json"},
        "suites": {name: {"path": f"configs/v5/slip/suites/{name}.jsonl", "sha256": sha(SL / f"suites/{name}.jsonl")}
                   for name in ("validation", "final", "final_subset60", "v4_final_noslip")},
        "seeds": {"development": v5.SPLIT_SEEDS["development"], "validation": v5.SPLIT_SEEDS["validation"],
                  "final": v5.SPLIT_SEEDS["final"], "analysis": v5.ANALYSIS_SEED, "evaluation_process": v5.EVAL_SEED,
                  "repeatability_process": v5.REPEAT_SEED, "training": list(SEEDS)},
        "conditions": {c: {k: v for k, v in spec.items()} for c, spec in v5.CONDITIONS.items()},
        "condition_note": "V5_EXECUTION.md lists slip_neg_5; -5 mm is infeasible (probe), so it is slip_neg_2 (-2 mm). "
                          "Slip draws are clamped so start x + slip x stays in the feasible cumulative range.",
        "outcome": "success = terminal_reason == 'success'; every scheduled case is in the denominator; invalid resets "
                   "and invalid slips (realized slip outside 1.5 mm of target in x/z) are failures for every method.",
        "training_free": {"roles": {r: sel["roles"][r]["candidate_id"] for r in ROLES},
                          "selection": "configs/v5/slip/development/baseline_selection.json (development only)"},
        "learned": {"profiles": list(PROFILES), "training_protocols": {p: f"configs/v5/slip/training/{p}.json" for p in PROFILES},
                    "parent": "geometry_calibrated (V4 one-shot 0.5 s calibration, EMA 0.2, bound 25 mm)",
                    "transitions_per_run": 10027008, "seeds": list(SEEDS)},
        "selection": {"candidates": list(CANDIDATES),
                      "rule": "validation suite (clean, static_mixed_id, slip_pos_10, slip_mixed_id; 40 cases each); key: "
                              "1. mean success with equal weight per condition (all scheduled cases; invalid resets/slips "
                              "count as failures), desc; 2. unsafe-event rate (any prohibited collision or drop), asc; "
                              "3. residual magnitude (mean per-episode mean max-axis |residual|), asc; 4. later candidate "
                              "(larger transition count). Values rounded to 12 decimals. Step 0 is an untrained control and "
                              "never eligible. Final outcomes are never read.",
                      "reported": "selected and final (10,027,008 transitions) checkpoints separately"},
        "primary": {
            "condition": v5.PRIMARY, "checkpoints": "selected",
            "contrasts": [{"id": "B1", "left": "slip_robust_history", "right": "slip_robust_ff"},
                          {"id": "B2", "left": "slip_robust_history", "right": "geometry_best"}],
            "interval": "paired hierarchical bootstrap over training seeds and base cases (deterministic controllers "
                        "broadcast over seeds), 10,000 draws, seed 6458401; implementation "
                        "scripts/final_review_audit.py::paired_bootstrap; 95% and Bonferroni 97.5% percentile intervals",
            "decision": "superiority only if the 97.5% lower bound > 0; no equivalence claims"},
        "secondary_exploratory": [
            "every method x every condition (selected and final checkpoints)",
            "slip_robust_repeat - slip_robust_ff (temporal order vs input size), every condition",
            "geometry_tracking - geometry_calibrated (does continuous re-estimation fix stale calibration), every condition",
            "final vs selected checkpoints per learned profile",
            "regression: selected Study B policies on static_mixed_id and on the V4 final suite (configs/v4/suites/final.jsonl "
            "with zero slip) against the published V4 selected policies of the same architecture",
            "B1/B2 on every other condition", "failure taxonomy incl. invalid_slip, receiver contact before grasp, "
            "misalignment at grasp"],
        "mechanisms": {"subset": "configs/v5/slip/suites/final_subset60.jsonl (first 60 slip_mixed_id final cases)",
                       "interventions": ["selected", "reversed history order", "repeated current frame",
                                         "development-fitted constant (mean residual of the selected history policy on the "
                                         "development suite) on the parent"], "policies": "selected slip_robust_history, 5 seeds"},
        "repeatability": {"process_seed": v5.REPEAT_SEED, "entries": "all executed training-free baselines and the selected "
                          "seed-111 checkpoint of each learned profile, full final suite",
                          "metric": "terminal-outcome agreement with the primary process"},
    }
    put(SL / "analysis_plan.json", p)


# ------------------------------------------------------------------------------------------------ matrices
def roles():
    sel = json.loads((SL / "development/baseline_selection.json").read_text())["roles"]
    executed = {}
    alias = {}
    for r in ROLES:
        cid = sel[r]["candidate_id"]
        if cid in executed.values():
            alias[r] = next(k for k, v in executed.items() if v == cid)
        else:
            executed[r] = cid
    return sel, executed, alias


def baseline_entries():
    sel, executed, alias = roles()
    out = {}
    for r, cid in executed.items():
        c = sel[r]
        out.setdefault(c["group"], []).append({"id": r, "method": c["method"], "overrides": c["overrides"], "trace": True,
                                               "role": "baseline", "candidate_id": cid})
    return out, alias


def matrices():
    final = "configs/v5/slip/suites/final.jsonl"
    trace = [f"{v5.PREFIX}-final-{c}-0000" for c in TRACE_CONDITIONS]
    ents, alias = baseline_entries()
    for g, es in ents.items():
        for kind, s in (("final", "final_baselines"), ("repeat", "repeat_baselines")):
            put(SL / f"matrices/{s}/{g}.json", {"name": f"v5_slip_{s}_{g}", "suite": final, "num_envs": FINAL_BATCH,
                                                "protocol": "configs/v2/protocol.json", "base_overrides": mech_base(g),
                                                "trace_cases": trace if kind == "final" else [], "entries": es})
    put(SL / "matrices/final_baselines/aliases.json", {"declared_aliases": alias,
                                                        "note": "an alias role is the same configuration as the role it "
                                                                "points to and is evaluated once"})
    for prof in PROFILES:
        for s in SEEDS:
            run = f"{prof}_s{s}"
            es = [{"id": f"{run}__step_000000000", "method": "combined", "training_seed": s, "role": "untrained_control",
                   "checkpoint": f"{run}/checkpoints/step_000000000.pt"}]
            es += [{"id": f"{run}__{t}", "method": "combined", "training_seed": s, "role": "candidate",
                    "checkpoint": f"{run}/checkpoints/{t}.pt"} for t in CANDIDATES]
            put(SL / f"matrices/validation/{run}.json", {"name": f"v5_slip_val_{run}", "suite": "configs/v5/slip/suites/validation.jsonl",
                                                         "num_envs": 160, "protocol": f"configs/v5/slip/training/{prof}.json",
                                                         "trace_cases": [], "entries": es})
    print({g: [e["id"] for e in es] for g, es in ents.items()}, alias)


def write_manifest(name, tasks):
    ids = [t["id"] for t in tasks]
    assert ids and len(ids) == len(set(ids))
    JOBS.mkdir(parents=True, exist_ok=True)
    (JOBS / f"{name}.json").write_text(json.dumps({"name": name, "tasks": tasks}, indent=1) + "\n")
    print(f"{name}: {len(tasks)} tasks")


def mtask(tid, mp: Path, out, seed, extra=()):
    mx = json.loads(mp.read_text())
    argv = ["scripts/eval_matrix.py", "--matrix", rel(mp), "--output", out, "--seed", str(seed), *extra]
    return {"id": tid, "kind": "isaac", "argv": argv, "inputs": [rel(mp), mx["suite"]],
            "outputs": [f"{out}/{e['id']}.jsonl" for e in mx["entries"]]}


def manifests():
    tr = []
    for prof in PROFILES:
        for s in SEEDS:
            d = f"$RUNS/train/{prof}_s{s}"
            tr.append({"id": f"train_{prof}_s{s}", "kind": "isaac",
                       "argv": ["scripts/train.py", "--method", "combined", "--seed", str(s), "--protocol",
                                f"configs/v5/slip/training/{prof}.json", "--run-type", "final", "--output", d],
                       "inputs": [f"configs/v5/slip/training/{prof}.json"],
                       "outputs": [f"{d}/checkpoints/final.pt", f"{d}/DONE.json"]})
    write_manifest("train", tr)
    write_manifest("validation", [mtask(f"val_{p.stem}", p, f"$RUNS/validation/{p.stem}", v5.EVAL_SEED,
                                        ["--checkpoint-root", "$RUNS/train"])
                                  for p in sorted((SL / "matrices/validation").glob("*.json"))])
    write_manifest("final_baselines", [mtask(f"final_baselines_{p.stem}", p, f"$RUNS/final/baselines", v5.EVAL_SEED)
                                       for p in sorted((SL / "matrices/final_baselines").glob("*.json")) if p.stem != "aliases"])
    write_manifest("repeat_baselines", [mtask(f"repeat_baselines_{p.stem}", p, f"$RUNS/repeat/baselines", v5.REPEAT_SEED)
                                        for p in sorted((SL / "matrices/repeat_baselines").glob("*.json"))])


# ------------------------------------------------------------------------------------------------ freeze
FROZEN_GLOBS = ["configs/v5/slip/suites/*.jsonl", "configs/v5/slip/training/*.json", "configs/v5/slip/analysis_plan.json",
                "configs/v5/slip/development/baseline_selection.json", "configs/v5/slip/development/baseline_grid.json",
                "configs/v5/slip/development/suites/development.jsonl", "configs/v5/slip/matrices/**/*.json",
                "results/v5/jobs/train.json", "results/v5/jobs/validation.json", "results/v5/jobs/final_baselines.json",
                "results/v5/jobs/repeat_baselines.json", "results/v5/slip/probe/summary.json",
                "scripts/v5_slip_study.py", "scripts/v5_slip_analysis.py", "scripts/final_review_audit.py",
                "scripts/eval_matrix.py", "scripts/train.py", "scripts/v3_jobs.py", "configs/v2/protocol.json",
                "src/csci645_handover/**/*.py"]


def frozen_files():
    files = set()
    for g in FROZEN_GLOBS:
        files |= {p for p in ROOT.glob(g) if p.is_file() and "__pycache__" not in p.parts}
    return sorted(files)


def freeze():
    inputs = {rel(p): sha(p) for p in frozen_files()}
    put(SL / "FREEZE.json", {"frozen_before_final_evaluation": True, "study": "V5 Study B",
                             "note": "post-selection matrices are generated by scripts/v5_slip_study.py post_selection "
                                     "(frozen here) from the selection records", "inputs": inputs})
    print(len(inputs), "frozen inputs")


def check():
    frozen = json.loads((SL / "FREEZE.json").read_text())["inputs"]
    bad = [k for k, v in frozen.items() if not (ROOT / k).is_file() or sha(ROOT / k) != v]
    if bad:
        raise SystemExit(f"FAIL: {len(bad)} frozen inputs changed: {bad[:10]}")
    print(f"PASS: {len(frozen)} frozen Study B inputs unchanged")


# ------------------------------------------------------------------------------------------------ selection
def _score(rows):
    conds = list(v5.VALIDATION)
    per = {c: [r for r in rows if r["condition"] == c] for c in conds}
    succ = sum(sum(r["success"] for r in v) / len(v) for v in per.values()) / len(conds)
    unsafe = sum(bool(r["collision"]) or r["terminal_reason"] == "drop" for r in rows) / len(rows)
    resid = sum(r["residual_abs_mean_m"] for r in rows) / len(rows)
    return {"success_rate": succ, "unsafe_rate": unsafe, "residual_magnitude_m": resid,
            "transitions": rows[0]["checkpoint_transitions"], "checkpoint_sha256": rows[0]["checkpoint_sha256"],
            "by_condition": {c: sum(r["success"] for r in v) for c, v in per.items()},
            "invalid_resets": sum(not r["reset_valid"] for r in rows),
            "invalid_slips": sum(r["terminal_reason"] == "invalid_slip" for r in rows)}


def _key(s):
    r = lambda x: round(x, 12)  # noqa: E731
    return (-r(s["success_rate"]), r(s["unsafe_rate"]), r(s["residual_magnitude_m"]), -s["transitions"])


def select(validation: Path, checkpoint_root: Path, output: Path):
    source = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "experiment-v5b^{commit}"], text=True).strip()
    check()
    suite_path = SL / "suites/validation.jsonl"
    cases = jl_read(suite_path)
    by_id = {c["case_id"]: c for c in cases}
    suite_hash = sha(suite_path)
    out, reports = {}, {}
    for mp in sorted((SL / "matrices/validation").glob("*.json")):
        run = mp.stem
        cands, control = [], None
        for e in json.loads(mp.read_text())["entries"]:
            tag = Path(e["checkpoint"]).stem
            rows = jl_read(validation / run / f"{e['id']}.jsonl")
            if {r["case_id"] for r in rows} != set(by_id) or len(rows) != len(cases):
                raise ValueError(f"{run} {tag}: incomplete validation records")
            for r in rows:
                if (r["suite_hash"] != suite_hash or r["source_commit"] != source or r["source_dirty"]
                        or r["checkpoint_sha256"] != sha(checkpoint_root / e["checkpoint"])
                        or r["condition"] != by_id[r["case_id"]]["condition"] or r["training_seed"] != e["training_seed"]
                        or r["terminal_reason"] == "infrastructure_error"):
                    raise ValueError(f"{run} {tag}: provenance mismatch on {r['case_id']}")
            if int(tag.split("_")[1]) != rows[0]["checkpoint_transitions"]:
                raise ValueError(f"{run} {tag}: checkpoint transitions mismatch")
            s = {**_score(rows), "tag": tag, "entry": e["id"]}
            if e["role"] == "untrained_control":
                control = s
            else:
                cands.append(s)
        if sorted(c["tag"] for c in cands) != sorted(CANDIDATES) or control is None:
            raise ValueError(f"{run}: candidates incomplete")
        best = sorted(cands, key=_key)[0]
        reports[run] = {"run": run, "source_commit": source, "suite_sha256": suite_hash, "selected": best["tag"],
                        "candidates": cands, "untrained_control": control}
        out[run] = {"selected": best["tag"], "success_rate": best["success_rate"], "unsafe_rate": best["unsafe_rate"],
                    "residual_magnitude_m": best["residual_magnitude_m"], "checkpoint_sha256": best["checkpoint_sha256"]}
    output.mkdir(parents=True, exist_ok=True)
    for run, rep in reports.items():
        (output / f"{run}.json").write_text(json.dumps(rep, indent=1) + "\n")
    (output / "selection.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: v["selected"] for k, v in out.items()}, indent=1))


# ------------------------------------------------------------------------------------------------ post selection
def post_selection():
    check()
    sel = json.loads((ROOT / "results/v5/slip/selection/selection.json").read_text())
    final = "configs/v5/slip/suites/final.jsonl"
    trace = [f"{v5.PREFIX}-final-{c}-0000" for c in TRACE_CONDITIONS]
    tasks, rep, regr, mdev = [], [], [], []
    d = SL / "matrices_post"
    for prof in PROFILES:
        for s in SEEDS:
            run = f"{prof}_s{s}"
            st = sel[run]["selected"]
            es = [{"id": f"{run}__selected", "method": "combined", "training_seed": s, "role": "selected", "trace": True,
                   "checkpoint": f"{run}/checkpoints/{st}.pt"},
                  {"id": f"{run}__final", "method": "combined", "training_seed": s, "role": "final", "trace": True,
                   "checkpoint": f"{run}/checkpoints/final.pt"}]
            mp = SL / f"matrices_post/final/{run}.json"
            put(mp, {"name": f"v5_slip_final_{run}", "suite": final, "num_envs": FINAL_BATCH,
                     "protocol": f"configs/v5/slip/training/{prof}.json", "trace_cases": trace, "entries": es})
            tasks.append(mtask(f"final_{run}", mp, f"$RUNS/final/{run}", v5.EVAL_SEED, ["--checkpoint-root", "$RUNS/train"]))
            mp = SL / f"matrices_post/regression/{run}.json"
            put(mp, {"name": f"v5_slip_regression_{run}", "suite": "configs/v5/slip/suites/v4_final_noslip.jsonl",
                     "num_envs": FINAL_BATCH, "protocol": f"configs/v5/slip/training/{prof}.json", "trace_cases": [],
                     "entries": [es[0]]})
            regr.append(mtask(f"regression_{run}", mp, f"$RUNS/regression/{run}", v5.EVAL_SEED, ["--checkpoint-root", "$RUNS/train"]))
            if s == SEEDS[0]:
                mp = SL / f"matrices_post/repeat/{run}.json"
                put(mp, {"name": f"v5_slip_repeat_{run}", "suite": final, "num_envs": FINAL_BATCH,
                         "protocol": f"configs/v5/slip/training/{prof}.json", "trace_cases": [], "entries": [es[0]]})
                rep.append(mtask(f"repeat_{run}", mp, f"$RUNS/repeat/{run}", v5.REPEAT_SEED, ["--checkpoint-root", "$RUNS/train"]))
            if prof == "slip_robust_history":
                mp = SL / f"matrices_post/mech_dev/{run}.json"
                put(mp, {"name": f"v5_slip_mechdev_{run}", "suite": "configs/v5/slip/development/suites/development.jsonl",
                         "num_envs": 192, "protocol": f"configs/v5/slip/training/{prof}.json", "trace_cases": [],
                         "entries": [{**es[0], "id": f"{run}__selected__dev", "trace": False}]})
                mdev.append(mtask(f"mechdev_{run}", mp, f"$RUNS/mechanisms/devfit/{run}", v5.EVAL_SEED,
                                  ["--checkpoint-root", "$RUNS/train"]))
    write_manifest("final_learned", tasks)
    write_manifest("regression", regr)
    write_manifest("repeat_learned", rep)
    write_manifest("mech_dev", mdev)


def mechanisms():
    """After mech_dev: subset60 interventions for the selected history policies + the parent (zero residual)."""
    sel = json.loads((ROOT / "results/v5/slip/selection/selection.json").read_text())
    fits = json.loads((ROOT / "results/v5/slip/mechanisms/constant_fits.json").read_text())
    sub = "configs/v5/slip/suites/final_subset60.jsonl"
    prot = "configs/v5/slip/training/slip_robust_history.json"
    tasks = []
    mp = SL / "matrices_post/mechanisms/parent.json"
    put(mp, {"name": "v5_slip_mech_parent", "suite": sub, "num_envs": 60, "protocol": "configs/v2/protocol.json",
             "base_overrides": mech_base("a"), "trace_cases": [],
             "entries": [{"id": "parent_zero_residual", "method": "geometry",
                          "overrides": {"align_max": 0.025, "giver_calibration_window_s": 0.5}}]})
    tasks.append(mtask("mech_parent", mp, "$RUNS/mechanisms/parent", v5.EVAL_SEED))
    for s in SEEDS:
        run = f"slip_robust_history_s{s}"
        ck = f"{run}/checkpoints/{sel[run]['selected']}.pt"
        for name, base in (("selected", {}), ("reversed", {"observation_history_permutation": [3, 2, 1, 0]}),
                           ("current_only", {"observation_history_mode": "repeat_current"})):
            mp = SL / f"matrices_post/mechanisms/{name}_{run}.json"
            put(mp, {"name": f"v5_slip_mech_{name}_{run}", "suite": sub, "num_envs": 60, "protocol": prot,
                     "base_overrides": base, "trace_cases": [],
                     "entries": [{"id": f"{run}__{name}", "method": "combined", "training_seed": s, "checkpoint": ck}]})
            tasks.append(mtask(f"mech_{name}_{run}", mp, f"$RUNS/mechanisms/{name}/{run}", v5.EVAL_SEED,
                               ["--checkpoint-root", "$RUNS/train"]))
        c = fits[run]["constant_m"]
        mp = SL / f"matrices_post/mechanisms/constant_{run}.json"
        put(mp, {"name": f"v5_slip_mech_constant_{run}", "suite": sub, "num_envs": 60, "protocol": "configs/v2/protocol.json",
                 "base_overrides": mech_base("a"), "trace_cases": [],
                 "entries": [{"id": f"{run}__constant", "method": "geometry",
                              "overrides": {"align_max": 0.025, "giver_calibration_window_s": 0.5, "constant_residual_m": c}}]})
        tasks.append(mtask(f"mech_constant_{run}", mp, f"$RUNS/mechanisms/constant/{run}", v5.EVAL_SEED))
    write_manifest("mechanisms", tasks)


def fit_constants(runs: Path):
    """Development-fitted constant per selected history run: mean of its per-episode mean residual on the
    development suite (all valid-reset episodes), clipped to the residual bound."""
    out = {}
    for s in SEEDS:
        run = f"slip_robust_history_s{s}"
        rows = [r for r in jl_read(runs / run / f"{run}__selected__dev.jsonl") if r["reset_valid"]]
        c = [sum(r["residual_mean_xyz_m"][k] for r in rows) / len(rows) for k in range(3)]
        out[run] = {"constant_m": [round(max(-0.02, min(0.02, x)), 9) for x in c], "episodes": len(rows)}
    put(ROOT / "results/v5/slip/mechanisms/constant_fits.json", out)
    print(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["suites", "plan", "matrices", "manifests", "freeze", "check", "select",
                                      "post_selection", "fit_constants", "mechanisms"])
    ap.add_argument("--validation")
    ap.add_argument("--checkpoint-root")
    ap.add_argument("--runs")
    ap.add_argument("--output", default=str(ROOT / "results/v5/slip/selection"))
    a = ap.parse_args()
    if a.stage == "select":
        select(Path(a.validation), Path(a.checkpoint_root), Path(a.output))
    elif a.stage == "fit_constants":
        fit_constants(Path(a.runs))
    else:
        {"suites": suites, "plan": plan, "matrices": matrices, "manifests": manifests, "freeze": freeze, "check": check,
         "post_selection": post_selection, "mechanisms": mechanisms}[a.stage]()


if __name__ == "__main__":
    main()
