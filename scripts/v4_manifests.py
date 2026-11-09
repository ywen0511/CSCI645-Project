#!/usr/bin/env python3
"""Write V4 job manifests (CPU, deterministic) for scripts/v3_jobs.py (the hash-checked runner is reused).

    python3 scripts/v4_manifests.py development       # results/v4/jobs/development.json
    python3 scripts/v4_manifests.py constants         # results/v4/jobs/constants.json (after baseline selection)

Later stages (acceptance, smoke, pilots, formal training, validation, final, mechanisms, repeatability,
traces, videos, verification) are added here as their inputs exist. Every simulator task is a fresh process.
Paths starting with $RUNS resolve against the runner's --runs-root.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/v4/jobs"
SEED_EVAL = 6456501  # evaluation process seed (outside the split RNG namespaces)


def write(name, tasks):
    OUT.mkdir(parents=True, exist_ok=True)
    ids = [t["id"] for t in tasks]
    assert len(ids) == len(set(ids)), "duplicate task ids"
    (OUT / f"{name}.json").write_text(json.dumps({"name": name, "tasks": tasks}, indent=1) + "\n")
    print(f"{name}: {len(tasks)} tasks")


def matrix_task(tid, mp: Path, out: str, extra=(), seed=SEED_EVAL, only=None):
    mx = json.loads(mp.read_text())
    rel = str(mp.relative_to(ROOT))
    ents = [e for e in mx["entries"] if only is None or e["id"] in only]
    argv = ["scripts/eval_matrix.py", "--matrix", rel, "--output", out, "--seed", str(seed), *extra]
    if only is not None:
        argv[3:3] = ["--only", ",".join(e["id"] for e in ents)]
    return {"id": tid, "kind": "isaac", "argv": argv, "inputs": [rel, mx["suite"]],
            "outputs": [f"{out}/{e['id']}.jsonl" for e in ents]}


def development():
    tasks = [matrix_task(f"dev_{p.stem}", p, f"$RUNS/development/{p.stem}")
             for p in sorted((ROOT / "configs/v4/development/matrices").glob("*.json"))]
    write("development", tasks)


def constants():
    p = ROOT / "configs/v4/development/matrices_constant/constant_search.json"
    write("constants", [matrix_task("dev_constant_search", p, "$RUNS/development/constant_search")])


PILOTS = [("combined_robust_history", 901), ("combined_robust_history", 902), ("combined_robust_ff", 901),
          ("residual_robust_history", 901)]
PILOT_TRANSITIONS = 5505024  # 168 PPO iterations of 32,768; 4 x 5.51M + 5 smoke runs (0.98M) = 23.0M <= 24M cap


def pilots():
    sys.path.insert(0, str(ROOT / "src"))
    from csci645_handover import v4_protocol as v4
    tasks, evals = [], []
    for prof, seed in PILOTS:
        proto = json.loads((ROOT / f"configs/v4/pilot/{prof}.json").read_text())
        method = proto["training"]["methods"][0]
        d = f"$RUNS/pilot/{prof}_s{seed}"
        tasks.append({"id": f"pilot_{prof}_s{seed}", "kind": "isaac",
                      "argv": ["scripts/train.py", "--method", method, "--seed", str(seed), "--protocol", f"configs/v4/pilot/{prof}.json",
                               "--run-type", "pilot", "--transitions", str(PILOT_TRANSITIONS), "--checkpoint-every", "1000000",
                               "--output", d],
                      "inputs": [f"configs/v4/pilot/{prof}.json"], "outputs": [f"{d}/checkpoints/final.pt", f"{d}/DONE.json"]})
        ents = [{"id": f"{prof}_s{seed}__{t}", "method": method, "training_seed": seed, "conditions": list(v4.VALIDATION),
                 "checkpoint": f"{prof}_s{seed}/checkpoints/{t}.pt"} for t in ("step_002031616", "step_004030464", "final")]
        mp = ROOT / f"configs/v4/pilot/matrices/{prof}_s{seed}.json"
        mp.parent.mkdir(parents=True, exist_ok=True)
        mp.write_text(json.dumps({"name": f"v4_pilot_{prof}_s{seed}", "suite": "configs/v4/suites/development.jsonl",
                                  "num_envs": 144, "protocol": f"configs/v4/pilot/{prof}.json", "trace_cases": [],
                                  "entries": ents}, indent=1) + "\n")
        evals.append(matrix_task(f"pilot_eval_{prof}_s{seed}", mp, f"$RUNS/pilot_eval/{prof}_s{seed}",
                                 extra=["--checkpoint-root", "$RUNS/pilot"]))
    write("pilots", tasks)
    write("pilot_eval", evals)


# ------------------------------------------------------------------------------------------- formal stages
FROZEN = ROOT / "configs/v4/frozen/training"
FINAL_BATCH = 240
BASELINE_ROLES = ("nominal", "geometry_fixed", "geometry_ema", "geometry_calibrated", "best_constant_geometry")


def runs():
    out = []
    for p in sorted(FROZEN.glob("*.json")):
        prot = json.loads(p.read_text())
        for seed in prot["training"]["seeds"]:
            out.append((p.stem, prot["training"]["methods"][0], seed))
    return out


def train():
    tasks = []
    for prof, method, seed in runs():
        d = f"$RUNS/train/{prof}_s{seed}"
        tasks.append({"id": f"train_{prof}_s{seed}", "kind": "isaac",
                      "argv": ["scripts/train.py", "--method", method, "--seed", str(seed), "--protocol",
                               f"configs/v4/frozen/training/{prof}.json", "--run-type", "final", "--output", d],
                      "inputs": [f"configs/v4/frozen/training/{prof}.json"], "outputs": [f"{d}/checkpoints/final.pt", f"{d}/DONE.json"]})
    write("train", tasks)


def validation():
    tasks = []
    for prof, method, seed in runs():
        mp = ROOT / f"configs/v4/frozen/matrices/validation/{prof}_s{seed}.json"
        for e in json.loads(mp.read_text())["entries"]:
            tasks.append({"id": f"val_{e['id']}", "kind": "isaac",
                          "argv": ["scripts/eval_matrix.py", "--matrix", str(mp.relative_to(ROOT)), "--only", e["id"],
                                   "--checkpoint-root", "$RUNS/train", "--output", f"$RUNS/validation/{prof}_s{seed}/{e['id']}",
                                   "--seed", str(SEED_EVAL)],
                          "inputs": [str(mp.relative_to(ROOT))],
                          "outputs": [f"$RUNS/validation/{prof}_s{seed}/{e['id']}/{e['id']}.jsonl"]})
    write("validation", tasks)


def baseline_matrices():
    """One matrix per executed baseline role; exact aliases are evaluated once and declared."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from v4_dev import REFERENCES, base_overrides, entry_overrides
    sel = json.loads((ROOT / "configs/v4/development/baseline_selection.json").read_text())["roles"]
    trace = json.loads((ROOT / "configs/v4/FINAL_SUITE.json").read_text())["trace_cases"]
    d = ROOT / "configs/v4/final_matrices"
    d.mkdir(parents=True, exist_ok=True)

    def ident(r):
        x = sel[r]
        return json.dumps({"method": x["method"], "ema": x["ema_alpha"], "ref": x["reference"], "align": x["align_max_m"],
                           "const": x.get("constant_residual_m") or [0.0, 0.0, 0.0]}, sort_keys=True)
    first, aliases, out = {}, {}, {}
    for r in BASELINE_ROLES:
        k = ident(r)
        if k in first:
            aliases[r] = first[k]
            continue
        first[k] = r
        x = sel[r]
        ov = entry_overrides(x) if x["method"] != "nominal" else {}
        if any(x.get("constant_residual_m") or []):
            ov["constant_residual_m"] = x["constant_residual_m"]
        ent = {"id": r, "method": x["method"], **({"overrides": ov} if ov else {}), "trace": True}
        mx = {"name": f"v4_final_{r}", "suite": "$DELIVERY/configs/v4/suites/final.jsonl", "num_envs": FINAL_BATCH,
              "protocol": "configs/v2/protocol.json",
              "base_overrides": base_overrides(x["ema_alpha"], REFERENCES[x["reference"]][0]), "trace_cases": trace,
              "entries": [ent]}
        (d / f"baseline_{r}.json").write_text(json.dumps(mx, indent=1) + "\n")
        out[r] = (d / f"baseline_{r}.json", mx)
    (d / "baseline_aliases.json").write_text(json.dumps(aliases, indent=1, sort_keys=True) + "\n")
    return out, aliases


def final():
    """After checkpoint selection (results/v4/selection/selection.json)."""
    sel = json.loads((ROOT / "results/v4/selection/selection.json").read_text())
    trace = json.loads((ROOT / "configs/v4/FINAL_SUITE.json").read_text())["trace_cases"]
    d = ROOT / "configs/v4/final_matrices"
    tasks = []
    base, _ = baseline_matrices()
    for r, (mp, mx) in base.items():
        tasks.append({"id": f"final_{r}", "kind": "isaac",
                      "argv": ["scripts/eval_matrix.py", "--matrix", "$DELIVERY/" + str(mp.relative_to(ROOT)), "--only", r,
                               "--output", f"$RUNS/final/{r}", "--seed", str(SEED_EVAL)],
                      "inputs": [str(mp.relative_to(ROOT))], "outputs": [f"$RUNS/final/{r}/{r}.jsonl"]})
    for prof, method, seed in runs():
        run = f"{prof}_s{seed}"
        ents = [{"id": f"{run}__selected", "method": method, "training_seed": seed, "role": "selected", "trace": True,
                 "checkpoint": f"{run}/checkpoints/{sel[run]['selected']}.pt"},
                {"id": f"{run}__final", "method": method, "training_seed": seed, "role": "final", "trace": True,
                 "checkpoint": f"{run}/checkpoints/final.pt"}]
        mp = d / f"{run}.json"
        mp.write_text(json.dumps({"name": f"v4_final_{run}", "suite": "$DELIVERY/configs/v4/suites/final.jsonl",
                                  "num_envs": FINAL_BATCH, "protocol": f"configs/v4/frozen/training/{prof}.json",
                                  "trace_cases": trace, "entries": ents}, indent=1) + "\n")
        for e in ents:
            tasks.append({"id": f"final_{e['id']}", "kind": "isaac",
                          "argv": ["scripts/eval_matrix.py", "--matrix", "$DELIVERY/" + str(mp.relative_to(ROOT)), "--only", e["id"],
                                   "--checkpoint-root", "$RUNS/train", "--output", f"$RUNS/final/{run}/{e['role']}", "--seed", str(SEED_EVAL)],
                          "inputs": [str(mp.relative_to(ROOT))], "outputs": [f"$RUNS/final/{run}/{e['role']}/{e['id']}.jsonl"]})
    write("final", tasks)


HISTORY_PROFILES = ("combined_robust_history", "residual_robust_history")


def subset60():
    rows = [json.loads(l) for l in (ROOT / "configs/v4/suites/final.jsonl").read_text().splitlines() if l.strip()]
    sub = [r for r in rows if int(r["base_case_id"][-4:]) < 5]
    assert len(sub) == 60
    p = ROOT / "configs/v4/suites/final_subset60.jsonl"
    p.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in sub))
    return "$DELIVERY/configs/v4/suites/final_subset60.jsonl"


def mech_dev():
    """Stage 1 of mechanisms: selected history policies on the development suite (to fit constant mean residuals)."""
    sel = json.loads((ROOT / "results/v4/selection/selection.json").read_text())
    d = ROOT / "configs/v4/final_matrices/extras"
    d.mkdir(parents=True, exist_ok=True)
    tasks = []
    for prof, method, seed in runs():
        if prof not in HISTORY_PROFILES:
            continue
        run = f"{prof}_s{seed}"
        mp = d / f"devfit_{run}.json"
        mp.write_text(json.dumps({"name": f"v4_devfit_{run}", "suite": "configs/v4/suites/development.jsonl", "num_envs": 288,
                                  "protocol": f"configs/v4/frozen/training/{prof}.json", "trace_cases": [],
                                  "entries": [{"id": f"{run}__selected__dev", "method": method, "training_seed": seed,
                                               "role": "development_fit", "checkpoint": f"{run}/checkpoints/{sel[run]['selected']}.pt"}]},
                                 indent=1) + "\n")
        tasks.append({"id": f"devfit_{run}", "kind": "isaac",
                      "argv": ["scripts/eval_matrix.py", "--matrix", "$DELIVERY/" + str(mp.relative_to(ROOT)), "--checkpoint-root",
                               "$RUNS/train", "--output", f"$RUNS/mechanisms/devfit/{run}", "--seed", str(SEED_EVAL)],
                      "inputs": [str(mp.relative_to(ROOT))], "outputs": [f"$RUNS/mechanisms/devfit/{run}/{run}__selected__dev.jsonl"]})
    write("mech_dev", tasks)


def extras():
    """Mechanisms (after mech_dev and scripts/v4_fit_constants.py), step-0 controls and repeatability."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from v4_dev import REFERENCES, base_overrides, entry_overrides
    suite = subset60()
    sel = json.loads((ROOT / "results/v4/selection/selection.json").read_text())
    roles = json.loads((ROOT / "configs/v4/development/baseline_selection.json").read_text())["roles"]
    fits = json.loads((ROOT / "results/v4/mechanisms/constant_fits.json").read_text())
    par = roles["common_parent"]
    pbase = base_overrides(par["ema_alpha"], REFERENCES[par["reference"]][0])
    d = ROOT / "configs/v4/final_matrices/extras"
    tasks = []

    def task(tid, mp, out_id, out_dir, ck=True, extra=()):
        tasks.append({"id": tid, "kind": "isaac",
                      "argv": ["scripts/eval_matrix.py", "--matrix", "$DELIVERY/" + str(mp.relative_to(ROOT)),
                               *(["--checkpoint-root", "$RUNS/train"] if ck else []), "--output", out_dir,
                               "--seed", str(SEED_EVAL), *extra],
                      "inputs": [str(mp.relative_to(ROOT))], "outputs": [f"{out_dir}/{out_id}.jsonl"]})

    # zero residual = parents on the subset
    mp = d / "mech_parents.json"
    mp.write_text(json.dumps({"name": "v4_mech_parents", "suite": suite, "num_envs": 60, "protocol": "configs/v2/protocol.json",
                              "base_overrides": pbase, "trace_cases": [],
                              "entries": [{"id": "parent_zero_residual", "method": "geometry", "overrides": entry_overrides(par)},
                                          {"id": "nominal_zero_residual", "method": "nominal"}]}, indent=1) + "\n")
    tasks.append({"id": "mech_parents", "kind": "isaac", "argv": ["scripts/eval_matrix.py", "--matrix", "$DELIVERY/" + str(mp.relative_to(ROOT)),
                  "--output", "$RUNS/mechanisms/parents", "--seed", str(SEED_EVAL)], "inputs": [str(mp.relative_to(ROOT))],
                  "outputs": ["$RUNS/mechanisms/parents/parent_zero_residual.jsonl", "$RUNS/mechanisms/parents/nominal_zero_residual.jsonl"]})
    for prof, method, seed in runs():
        run = f"{prof}_s{seed}"
        if seed == 111:  # untrained step-0 control per profile
            mp = d / f"zero_{prof}.json"
            mp.write_text(json.dumps({"name": f"v4_zero_{prof}", "suite": suite, "num_envs": 60,
                                      "protocol": f"configs/v4/frozen/training/{prof}.json", "trace_cases": [],
                                      "entries": [{"id": f"{run}__step0", "method": method, "training_seed": seed,
                                                   "role": "untrained_control", "checkpoint": f"{run}/checkpoints/step_000000000.pt"}]},
                                     indent=1) + "\n")
            task(f"zero_{prof}", mp, f"{run}__step0", f"$RUNS/mechanisms/zero/{prof}")
        if prof not in HISTORY_PROFILES:
            continue
        ck = f"{run}/checkpoints/{sel[run]['selected']}.pt"
        ents = {"selected": ({}, {"id": f"{run}__selected", "method": method, "training_seed": seed, "checkpoint": ck}),
                "reversed": ({"observation_history_permutation": [3, 2, 1, 0]},
                             {"id": f"{run}__reversed", "method": method, "training_seed": seed, "checkpoint": ck,
                              "allow_config_mismatch": True}),
                "current_only": ({"observation_history_mode": "repeat_current"},
                                 {"id": f"{run}__current_only", "method": method, "training_seed": seed, "checkpoint": ck,
                                  "allow_config_mismatch": True})}
        for name, (base, ent) in ents.items():
            mp = d / f"mech_{name}_{run}.json"
            mp.write_text(json.dumps({"name": f"v4_mech_{name}_{run}", "suite": suite, "num_envs": 60,
                                      "protocol": f"configs/v4/frozen/training/{prof}.json", "base_overrides": base,
                                      "trace_cases": [], "entries": [ent]}, indent=1) + "\n")
            task(f"mech_{name}_{run}", mp, ent["id"], f"$RUNS/mechanisms/{name}/{run}")
        c = fits[run]["constant_residual_m"]
        mp = d / f"mech_constant_{run}.json"
        geo = method == "combined"
        cbase = pbase
        cent = {"id": f"{run}__constant", "method": "geometry" if geo else "nominal",
                **({"overrides": {**entry_overrides(par), "constant_residual_m": c}} if geo else {"overrides": {"constant_residual_m": c}})}
        mp.write_text(json.dumps({"name": f"v4_mech_constant_{run}", "suite": suite, "num_envs": 60, "protocol": "configs/v2/protocol.json",
                                  "base_overrides": cbase, "trace_cases": [], "entries": [cent]}, indent=1) + "\n")
        task(f"mech_constant_{run}", mp, cent["id"], f"$RUNS/mechanisms/constant/{run}", ck=False)
    # repeatability: batch 6 and 20 x three process seeds
    rep = [("geometry_calibrated", None)] + [(f"combined_robust_history_s{s}", s) for s in (111, 222, 333, 444, 555)]
    for eid, seed in rep:
        if seed is None:
            x = roles["geometry_calibrated"]
            mx = {"name": "v4_repeat_geometry_calibrated", "suite": suite, "num_envs": 20, "protocol": "configs/v2/protocol.json",
                  "base_overrides": pbase, "trace_cases": [],
                  "entries": [{"id": "geometry_calibrated", "method": "geometry", "overrides": entry_overrides(x)}]}
            out_id, ckf = "geometry_calibrated", False
        else:
            out_id, ckf = f"{eid}__selected", True
            mx = {"name": f"v4_repeat_{eid}", "suite": suite, "num_envs": 20, "protocol": "configs/v4/frozen/training/combined_robust_history.json",
                  "trace_cases": [], "entries": [{"id": out_id, "method": "combined", "training_seed": seed, "role": "selected",
                                                  "checkpoint": f"{eid}/checkpoints/{sel[eid]['selected']}.pt"}]}
        mp = d / f"repeat_{eid}.json"
        mp.write_text(json.dumps(mx, indent=1) + "\n")
        for ps in (6456601, 6456602, 6456603):
            for b in (6, 20):
                tasks.append({"id": f"rep_{eid}_p{ps}_b{b}", "kind": "isaac",
                              "argv": ["scripts/eval_matrix.py", "--matrix", "$DELIVERY/" + str(mp.relative_to(ROOT)), "--num-envs", str(b),
                                       "--output", f"$RUNS/repeatability/b{b}/p{ps}/{eid}", "--seed", str(ps),
                                       *(["--checkpoint-root", "$RUNS/train"] if ckf else [])],
                              "inputs": [str(mp.relative_to(ROOT))], "outputs": [f"$RUNS/repeatability/b{b}/p{ps}/{eid}/{out_id}.jsonl"]})
    write("extras", tasks)


def traces():
    """Supplementary traces of the six predeclared cases for every executed final entry (batch 6, fresh process each);
    records stay separate from the formal matrix (outputs under $RUNS/traces6/)."""
    fs = json.loads((ROOT / "configs/v4/FINAL_SUITE.json").read_text())
    rows = {json.loads(l)["case_id"]: l for l in (ROOT / "configs/v4/suites/final.jsonl").read_text().splitlines() if l.strip()}
    sp = ROOT / "configs/v4/suites/final_trace6.jsonl"
    sp.write_text("".join(rows[c].rstrip("\n") + "\n" for c in sorted(fs["trace_cases"])))
    d = ROOT / "configs/v4/final_matrices/traces6"
    d.mkdir(parents=True, exist_ok=True)
    tasks = []
    for mp in sorted((ROOT / "configs/v4/final_matrices").glob("*.json")):
        if mp.name == "baseline_aliases.json":
            continue
        m = json.loads(mp.read_text())
        m.update(name=m["name"] + "_traces6", suite="$DELIVERY/configs/v4/suites/final_trace6.jsonl", num_envs=6,
                 trace_cases=sorted(fs["trace_cases"]))
        for e in m["entries"]:
            e["trace"] = True
        out = d / mp.name
        out.write_text(json.dumps(m, indent=1) + "\n")
        for e in m["entries"]:
            ck = ["--checkpoint-root", "$RUNS/train"] if e.get("checkpoint") else []
            tasks.append({"id": f"trace6_{e['id']}", "kind": "isaac",
                          "argv": ["scripts/eval_matrix.py", "--matrix", "$DELIVERY/" + str(out.relative_to(ROOT)), "--only", e["id"],
                                   *ck, "--output", f"$RUNS/traces6/{e['id']}", "--seed", str(SEED_EVAL)],
                          "inputs": [str(out.relative_to(ROOT))], "outputs": [f"$RUNS/traces6/{e['id']}/traces/{e['id']}.json"]})
    write("traces6", tasks)


if __name__ == "__main__":
    for stage in sys.argv[1:]:
        {"development": development, "constants": constants, "pilots": pilots, "train": train,
         "validation": validation, "final": final, "mech_dev": mech_dev, "extras": extras, "traces6": traces}[stage]()
