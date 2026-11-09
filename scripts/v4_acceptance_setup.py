#!/usr/bin/env python3
"""Write the V4 acceptance suites, matrices and job manifests (CPU, deterministic; after baseline selection).

    python3 scripts/v4_acceptance_setup.py      # configs/v4/acceptance/*, results/v4/jobs/acceptance_{eval,smoke}.json

Checks (judged by scripts/v4_acceptance_report.py):
  A1 v3_path      V3's 65-case final subset (suite v3) under the V4 code with the V4 options off: geometry_common
                  and the V3 combined_robust_history_s11 selected checkpoint must equal the published V3 records.
  A2 v4_zero      the same 65 cases in V4 format (zero in-grasp offset) with grasp_uncertainty on: same equality.
  A3 negative     no receiver / giver keeps holding / table support, on grasp_10mm and grasp_15mm development cases
                  with the common parent: no success may occur (success needs an independent 2 s receiver hold).
  A4 layout       72 development cases (mixed_id, grasp_15mm, noise_2mm) at batch 1, 8, 72 and 72 in reverse order:
                  identical sensor specs, requested offsets and calibration estimates per case; outcome agreement.
  A5 leakage      the full 288-case development suite at batch 16 (18 consecutive episodes per env) vs the batch-288
                  development records of the same parent: per-case agreement of outcomes and calibration.
  A6 privileged   the parent on 48 traced cases with the debug perturbation of privileged-only tensors on vs off:
                  identical controller traces and outcomes.
  Smoke stage: smoke training of all five profiles, interrupted resume + checkpoint inspection, zero-residual
  (step-0) checkpoints equal the parent (A7), a smoke policy with privileged perturbation on vs off (A8), and the
  evaluation-resume/tamper test (A9, scripts/v3_cache_test.py on a V4 matrix).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from csci645_handover import v4_protocol as v4  # noqa: E402
from v4_dev import SENSOR, REFERENCES, base_overrides, entry_overrides  # noqa: E402
from v4_manifests import SEED_EVAL, write  # noqa: E402
from v4_protocols import PROFILES  # noqa: E402

A = ROOT / "configs/v4/acceptance"
V3_SUB = ROOT / "configs/v3/suites/final_subset65.jsonl"
V3_SEL = json.loads((ROOT / "results/v3/selection/selection.json").read_text())["combined_robust_history_s11"]["selected"]
V3_GEO = {"observation_sensor": {**SENSOR, "ema_alpha": 1.0}, "observation_giver_reference": True}


def jl(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def put(name, mx):
    (A / f"{name}.json").write_text(json.dumps(mx, indent=1) + "\n")
    return A / f"{name}.json"


def suite(name, rows):
    v4.write_jsonl(A / name, rows)
    return f"configs/v4/acceptance/{name}"


def main():
    A.mkdir(parents=True, exist_ok=True)
    sel = json.loads((ROOT / "configs/v4/development/baseline_selection.json").read_text())["roles"]
    par = sel["common_parent"]
    pbase = base_overrides(par["ema_alpha"], REFERENCES[par["reference"]][0])
    pent = {"id": "parent", "method": "geometry", "overrides": entry_overrides(par), "trace": True}
    dev = jl(ROOT / "configs/v4/suites/development.jsonl")
    mx = {}
    # A1/A2: V3 equality
    sub3 = jl(V3_SUB)
    s4 = suite("v3subset65_v4fmt.jsonl", [{**r, "suite_version": 4, "grasp_offset_xyz_m": [0.0, 0.0, 0.0]} for r in sub3])
    v3ck = {"id": "v3_combined_robust_history_s11__selected", "method": "combined", "training_seed": 11,
            "checkpoint": f"combined_robust_history_s11/checkpoints/{V3_SEL}.pt"}
    mx["a1_v3path_geometry"] = put("a1_v3path_geometry", {"name": "v4acc_a1_geometry", "suite": str(V3_SUB.relative_to(ROOT)),
        "num_envs": 23, "protocol": "configs/v2/protocol.json", "base_overrides": V3_GEO, "trace_cases": [],
        "entries": [{"id": "geometry_common", "method": "geometry", "overrides": {"align_max": 0.015}}]})
    mx["a1_v3path_policy"] = put("a1_v3path_policy", {"name": "v4acc_a1_policy", "suite": str(V3_SUB.relative_to(ROOT)),
        "num_envs": 23, "protocol": "configs/v3/frozen/training/combined_robust_history.json", "trace_cases": [], "entries": [v3ck]})
    mx["a2_v4zero_geometry"] = put("a2_v4zero_geometry", {"name": "v4acc_a2_geometry", "suite": s4, "num_envs": 23,
        "protocol": "configs/v2/protocol.json", "base_overrides": {**V3_GEO, "grasp_uncertainty": True}, "trace_cases": [],
        "entries": [{"id": "geometry_common", "method": "geometry", "overrides": {"align_max": 0.015}}]})
    mx["a2_v4zero_policy"] = put("a2_v4zero_policy", {"name": "v4acc_a2_policy", "suite": s4, "num_envs": 23,
        "protocol": "configs/v3/frozen/training/combined_robust_history.json", "base_overrides": {"grasp_uncertainty": True},
        "trace_cases": [], "entries": [{**v3ck, "allow_config_mismatch": True}]})
    # A3 negative controls
    neg = suite("negative_cases.jsonl", [r for r in dev if r["condition"] in ("grasp_10mm", "grasp_15mm")
                                         and int(r["case_id"][-4:]) < 8])
    for ctl, extra in (("no_receiver", {}), ("giver_holds", {}), ("table_support", {"table_size_override": [0.06, 0.3, 0.2]})):
        mx[f"a3_neg_{ctl}"] = put(f"a3_neg_{ctl}", {"name": f"v4acc_neg_{ctl}", "suite": neg, "num_envs": 16,
            "protocol": "configs/v2/protocol.json", "base_overrides": {**pbase, "negative_control": ctl, **extra},
            "trace_cases": [], "entries": [{"id": "nominal", "method": "nominal"}, {**pent, "trace": False}]})
    # A4 layout
    lay = [r for r in dev if r["condition"] in ("mixed_id", "grasp_15mm", "noise_2mm")]
    sl = suite("layout.jsonl", lay)
    slr = suite("layout_rev.jsonl", list(reversed(lay)))
    for tag_, n, s in (("b1", 1, sl), ("b8", 8, sl), ("b72", 72, sl), ("b72rev", 72, slr)):
        mx[f"a4_layout_{tag_}"] = put(f"a4_layout_{tag_}", {"name": f"v4acc_layout_{tag_}", "suite": s, "num_envs": n,
            "protocol": "configs/v2/protocol.json", "base_overrides": pbase, "trace_cases": [], "entries": [{**pent, "trace": False}]})
    # A5 leakage
    mx["a5_leak_b16"] = put("a5_leak_b16", {"name": "v4acc_leak_b16", "suite": "configs/v4/suites/development.jsonl",
        "num_envs": 16, "protocol": "configs/v2/protocol.json", "base_overrides": pbase, "trace_cases": [],
        "entries": [{**pent, "trace": False}]})
    # A6 privileged perturbation (parent)
    priv = [r for r in dev if r["condition"] in ("mixed_id", "grasp_15mm") and int(r["case_id"][-4:]) < 24]
    sp = suite("privileged.jsonl", priv)
    ids = [r["case_id"] for r in priv]
    for flag in (False, True):
        t = "on" if flag else "off"
        mx[f"a6_priv_{t}"] = put(f"a6_priv_{t}", {"name": f"v4acc_priv_{t}", "suite": sp, "num_envs": len(priv),
            "protocol": "configs/v2/protocol.json", "base_overrides": {**pbase, "debug_perturb_privileged": flag},
            "trace_cases": ids, "entries": [pent]})
    tasks = []
    for name, p in mx.items():
        extra = ["--checkpoint-root", "$RUNS/v3x/formal/train"] if "policy" in name else []
        tasks.append({"id": f"acc_{name}", "kind": "isaac",
                      "argv": ["scripts/eval_matrix.py", "--matrix", str(p.relative_to(ROOT)), "--output",
                               f"$RUNS/acceptance/{name}", "--seed", str(SEED_EVAL), *extra],
                      "inputs": [str(p.relative_to(ROOT))],
                      "outputs": [f"$RUNS/acceptance/{name}/{e['id']}.jsonl" for e in json.loads(p.read_text())["entries"]]})
    write("acceptance_eval", tasks)

    # ---- smoke stage (after training protocols exist)
    sm = []
    zero = suite("zero_residual.jsonl", [r for r in dev if r["condition"] in ("mixed_id", "grasp_15mm", "noise_2mm")])
    for prof, cfg in PROFILES.items():
        d = f"$RUNS/smoke/smoke_{prof}_s101"
        proto = f"configs/v4/pilot/{prof}.json"
        sm.append({"id": f"smoke_{prof}", "kind": "isaac",
                   "argv": ["scripts/train.py", "--method", cfg["method"], "--seed", "101", "--protocol", proto, "--run-type", "smoke",
                            "--transitions", "131072", "--checkpoint-every", "65536", "--output", d],
                   "inputs": [proto, "scripts/train.py"], "outputs": [f"{d}/checkpoints/final.pt"]})
        sm.append({"id": f"smoke_{prof}_copy", "kind": "shell",
                   "argv": ["rm", "-rf", f"{d}_resume", "&&", "cp", "-r", d, f"{d}_resume"], "inputs": [],
                   "outputs": [f"{d}_resume/checkpoints/latest.pt"]})
        sm.append({"id": f"smoke_{prof}_resume", "kind": "isaac",
                   "argv": ["scripts/train.py", "--method", cfg["method"], "--seed", "101", "--protocol", proto, "--run-type", "smoke",
                            "--transitions", "196608", "--checkpoint-every", "65536", "--resume", f"{d}_resume/checkpoints/latest.pt",
                            "--output", f"{d}_resume"], "inputs": [proto], "outputs": [f"{d}_resume/run_resume.json"]})
        sm.append({"id": f"smoke_{prof}_inspect", "kind": "isaac",
                   "argv": ["scripts/closeout_inspect_ckpt.py", "--before", f"{d}/checkpoints/latest.pt", "--after",
                            f"{d}_resume/checkpoints/final.pt", "--expect-iterations", "6", "--expect-transitions", "196608",
                            "--output", f"$RUNS/acceptance/resume_{prof}.json"], "inputs": [], "outputs": [f"$RUNS/acceptance/resume_{prof}.json"]})
        # A7 zero residual: untrained (zero-mean) checkpoint vs its parent
        ents = [{"id": f"{prof}_step0", "method": cfg["method"], "training_seed": 101, "checkpoint": f"smoke_{prof}_s101/checkpoints/step_000000000.pt"},
                {"id": f"{prof}_final", "method": cfg["method"], "training_seed": 101, "checkpoint": f"smoke_{prof}_s101/checkpoints/final.pt"}]
        p = put(f"a7_zero_{prof}", {"name": f"v4acc_zero_{prof}", "suite": zero, "num_envs": 72, "protocol": proto,
                                    "trace_cases": [], "entries": ents})
        sm.append({"id": f"acc_a7_zero_{prof}", "kind": "isaac",
                   "argv": ["scripts/eval_matrix.py", "--matrix", str(p.relative_to(ROOT)), "--checkpoint-root", "$RUNS/smoke",
                            "--output", f"$RUNS/acceptance/a7_zero_{prof}", "--seed", str(SEED_EVAL)],
                   "inputs": [str(p.relative_to(ROOT))], "outputs": [f"$RUNS/acceptance/a7_zero_{prof}/{e['id']}.jsonl" for e in ents]})
    # parent references for A7: nominal (residual profiles) and the parent on the same 72 cases
    p = put("a7_parents", {"name": "v4acc_a7_parents", "suite": zero, "num_envs": 72, "protocol": "configs/v2/protocol.json",
                           "base_overrides": pbase, "trace_cases": [],
                           "entries": [{"id": "nominal", "method": "nominal"}, {**pent, "trace": False}]})
    sm.append({"id": "acc_a7_parents", "kind": "isaac", "argv": ["scripts/eval_matrix.py", "--matrix", str(p.relative_to(ROOT)),
               "--output", "$RUNS/acceptance/a7_parents", "--seed", str(SEED_EVAL)], "inputs": [str(p.relative_to(ROOT))],
               "outputs": ["$RUNS/acceptance/a7_parents/nominal.jsonl", "$RUNS/acceptance/a7_parents/parent.jsonl"]})
    # A8 privileged perturbation with a smoke history policy
    for flag in (False, True):
        t = "on" if flag else "off"
        p = put(f"a8_priv_policy_{t}", {"name": f"v4acc_priv_policy_{t}", "suite": sp, "num_envs": len(priv),
            "protocol": "configs/v4/pilot/combined_robust_history.json", "base_overrides": {"debug_perturb_privileged": flag},
            "trace_cases": ids, "entries": [{"id": "history_smoke_final", "method": "combined", "training_seed": 101, "trace": True,
                                             "allow_config_mismatch": flag,
                                             "checkpoint": "smoke_combined_robust_history_s101/checkpoints/final.pt"}]})
        sm.append({"id": f"acc_a8_priv_policy_{t}", "kind": "isaac",
                   "argv": ["scripts/eval_matrix.py", "--matrix", str(p.relative_to(ROOT)), "--checkpoint-root", "$RUNS/smoke",
                            "--output", f"$RUNS/acceptance/a8_priv_policy_{t}", "--seed", str(SEED_EVAL)],
                   "inputs": [str(p.relative_to(ROOT))], "outputs": [f"$RUNS/acceptance/a8_priv_policy_{t}/history_smoke_final.jsonl"]})
    # A9 evaluation resume / stale-record rejection
    sm.append({"id": "acc_a9_cache", "kind": "cpu",
               "argv": ["scripts/v3_cache_test.py", "--isaac-python", "$PY", "--matrix", "configs/v4/acceptance/a4_layout_b8.json",
                        "--entry", "parent", "--ckpt-matrix", "configs/v4/acceptance/a7_zero_combined_robust_ff.json",
                        "--ckpt-entry", "combined_robust_ff_step0", "--checkpoint-root", "$RUNS/smoke",
                        "--work", "$RUNS/acceptance/a9_cache", "--output", "$RUNS/acceptance/a9_cache.json"],
               "inputs": ["scripts/v3_cache_test.py"], "outputs": ["$RUNS/acceptance/a9_cache.json"]})
    write("acceptance_smoke", sm)


if __name__ == "__main__":
    main()
