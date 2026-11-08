#!/usr/bin/env python3
"""Write v3 job manifests (CPU, deterministic). Each manifest lists every simulator/CPU task of one stage.

    python3 scripts/v3_manifests.py acceptance     # results/v3/jobs/acceptance_{sim,eval,smoke}.json
    python3 scripts/v3_manifests.py development    # results/v3/jobs/development.json (85 fresh-process entries)

Later stages (pilots, formal training, validation, final evaluation, interventions, repeatability, videos)
are added by the same script once their inputs exist. Runs execute with scripts/v3_jobs.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/v3/jobs"
PROFILES = {"combined_clean_ff": "combined", "combined_robust_ff": "combined", "combined_robust_history": "combined",
            "residual_robust_history": "residual", "combined_robust_repeat": "combined"}
SEED_EVAL = 6455501


def write(name, tasks):
    OUT.mkdir(parents=True, exist_ok=True)
    ids = [t["id"] for t in tasks]
    assert len(ids) == len(set(ids)), "duplicate task ids"
    (OUT / f"{name}.json").write_text(json.dumps({"name": name, "tasks": tasks}, indent=1) + "\n")
    print(f"{name}: {len(tasks)} tasks")


def acceptance():
    A = "$RUNS/acceptance"
    sim = [{"id": "acc_sensor", "kind": "isaac", "argv": ["scripts/v3_acceptance.py", "sensor", "--output", f"{A}/sensor.json"],
            "inputs": ["scripts/v3_acceptance.py", "src/csci645_handover/core/observation.py"], "outputs": [f"{A}/sensor.json"]}]
    for c in ("residual", "boundary"):
        sim.append({"id": f"acc_{c}", "kind": "isaac", "argv": ["scripts/v3_acceptance.py", c, "--output", f"{A}/{c}.json"],
                    "inputs": ["scripts/v3_acceptance.py", "src/csci645_handover/tasks/handover_env.py"], "outputs": [f"{A}/{c}.json"]})
    for v in ("archived", "ff_ema1p0_giver0", "ff_ema0p5_giver1", "hist5_ema0p2_giver0", "hist5_ema1p0_giver1"):
        sim.append({"id": f"acc_dependency_{v}", "kind": "isaac",
                    "argv": ["scripts/v3_acceptance.py", "dependency", "--variant", v, "--output", f"{A}/dependency_{v}.json"],
                    "inputs": ["scripts/v3_acceptance.py", "src/csci645_handover/tasks/handover_env.py"],
                    "outputs": [f"{A}/dependency_{v}.json"]})
    write("acceptance_sim", sim)
    ev = []
    for m in ("a1_b1", "a1_b8", "neg_no_receiver", "neg_giver_holds", "neg_table_support", "a3_b1", "a3_b23", "a3_b23rev",
              "a6_sensor0", "a6_archived"):
        mx = json.loads((ROOT / f"configs/v3/acceptance/{m}.json").read_text())
        for e in mx["entries"]:
            ev.append({"id": f"acc_{m}_{e['id']}", "kind": "isaac",
                       "argv": ["scripts/eval_matrix.py", "--matrix", f"configs/v3/acceptance/{m}.json", "--only", e["id"],
                                "--output", f"{A}/{m}/{e['id']}", "--seed", str(SEED_EVAL)],
                       "inputs": [f"configs/v3/acceptance/{m}.json", mx["suite"]],
                       "outputs": [f"{A}/{m}/{e['id']}/{e['id']}.jsonl"]})
    write("acceptance_eval", ev)
    sm = []
    for prof, method in PROFILES.items():
        d = f"$RUNS/smoke/smoke_{prof}_s101"
        sm.append({"id": f"smoke_{prof}", "kind": "isaac",
                   "argv": ["scripts/train.py", "--method", method, "--seed", "101", "--protocol", f"configs/v3/training/{prof}.json",
                            "--run-type", "smoke", "--transitions", "131072", "--checkpoint-every", "65536", "--output", d],
                   "inputs": [f"configs/v3/training/{prof}.json", "scripts/train.py"], "outputs": [f"{d}/checkpoints/final.pt"]})
        sm.append({"id": f"smoke_{prof}_copy", "kind": "shell",
                   "argv": ["rm", "-rf", f"{d}_resume", "&&", "cp", "-r", d, f"{d}_resume"],
                   "inputs": [], "outputs": [f"{d}_resume/checkpoints/latest.pt"]})
        sm.append({"id": f"smoke_{prof}_resume", "kind": "isaac",
                   "argv": ["scripts/train.py", "--method", method, "--seed", "101", "--protocol", f"configs/v3/training/{prof}.json",
                            "--run-type", "smoke", "--transitions", "196608", "--checkpoint-every", "65536",
                            "--resume", f"{d}_resume/checkpoints/latest.pt", "--output", f"{d}_resume"],
                   "inputs": [f"configs/v3/training/{prof}.json"], "outputs": [f"{d}_resume/run_resume.json"]})
        sm.append({"id": f"smoke_{prof}_inspect", "kind": "isaac",
                   "argv": ["scripts/closeout_inspect_ckpt.py", "--before", f"{d}/checkpoints/latest.pt", "--after",
                            f"{d}_resume/checkpoints/final.pt", "--expect-iterations", "6", "--expect-transitions", "196608",
                            "--output", f"{A}/resume_{prof}.json"],
                   "inputs": [], "outputs": [f"{A}/resume_{prof}.json"]})
    for prof in ("combined_robust_ff", "combined_robust_history", "residual_robust_history"):
        mx = json.loads((ROOT / f"configs/v3/acceptance/a2_{prof}.json").read_text())
        for e in mx["entries"]:
            sm.append({"id": f"acc_a2_{prof}_{e['id']}", "kind": "isaac",
                       "argv": ["scripts/eval_matrix.py", "--matrix", f"configs/v3/acceptance/a2_{prof}.json", "--only", e["id"],
                                "--checkpoint-root", "$RUNS/smoke", "--output", f"{A}/a2_{prof}/{e['id']}", "--seed", str(SEED_EVAL)],
                       "inputs": [f"configs/v3/acceptance/a2_{prof}.json"], "outputs": [f"{A}/a2_{prof}/{e['id']}/{e['id']}.jsonl"]})
    for mode, prof in (("stack", "combined_robust_history"), ("repeat_current", "combined_robust_repeat"), ("permuted", "combined_robust_history")):
        sm.append({"id": f"acc_inputs_{mode}", "kind": "isaac",
                   "argv": ["scripts/v3_acceptance.py", "inputs", "--mode", mode, "--checkpoint",
                            f"$RUNS/smoke/smoke_{prof}_s101/checkpoints/final.pt", "--output", f"{A}/inputs_{mode}.json"],
                   "inputs": ["scripts/v3_acceptance.py"], "outputs": [f"{A}/inputs_{mode}.json"]})
    write("acceptance_smoke", sm)


def development():
    tasks = []
    for p in sorted((ROOT / "configs/v3/matrices/development").glob("*.json")):
        mx = json.loads(p.read_text())
        for e in mx["entries"]:
            if e["id"] == "nominal" and p.stem != "ema1p0_giver0":
                continue  # nominal ignores the estimator: run once, alias in the selection table
            tasks.append({"id": f"dev_{p.stem}_{e['id']}", "kind": "isaac",
                          "argv": ["scripts/eval_matrix.py", "--matrix", f"configs/v3/matrices/development/{p.name}", "--only", e["id"],
                                   "--output", f"$RUNS/development/{p.stem}/{e['id']}", "--seed", str(SEED_EVAL)],
                          "inputs": [f"configs/v3/matrices/development/{p.name}", "configs/v3/suites/development.jsonl"],
                          "outputs": [f"$RUNS/development/{p.stem}/{e['id']}/{e['id']}.jsonl"]})
    write("development", tasks)


def cache():
    A = "$RUNS/acceptance"
    write("acceptance_cache", [{"id": "acc_cache_test", "kind": "cpu",
        "argv": ["scripts/v3_cache_test.py", "--isaac-python", "$PY", "--matrix", "configs/v3/acceptance/a1_b8.json", "--entry", "geometry_1p5cm",
                 "--ckpt-matrix", "configs/v3/acceptance/a2_combined_robust_ff.json", "--ckpt-entry", "combined_robust_ff_step0",
                 "--checkpoint-root", "$RUNS/smoke", "--work", f"{A}/cache_test", "--output", f"{A}/cache_test.json"],
        "inputs": ["scripts/v3_cache_test.py"], "outputs": [f"{A}/cache_test.json"]}])


PILOTS = [("combined_robust_ff", 101), ("combined_robust_ff", 102), ("combined_robust_history", 101),
          ("combined_robust_history", 102), ("residual_robust_history", 101), ("residual_robust_history", 102),
          ("combined_robust_repeat", 101), ("combined_clean_ff", 101)]
PILOT_TRANSITIONS = 2752512  # 84 PPO iterations of 32,768; 8 x 2.75M + 1.97M smoke <= 24M cap


def pilots():
    tasks = []
    dev_strata = ["clean", "physical_only", "bias_5mm", "noise_2mm", "delay_2step", "mixed_id"]
    for prof, seed in PILOTS:
        d = f"$RUNS/pilot/{prof}_s{seed}"
        tasks.append({"id": f"pilot_{prof}_s{seed}", "kind": "isaac",
                      "argv": ["scripts/train.py", "--method", PROFILES[prof], "--seed", str(seed), "--protocol",
                               f"configs/v3/pilot/{prof}.json", "--run-type", "pilot", "--transitions", str(PILOT_TRANSITIONS),
                               "--checkpoint-every", "1000000", "--output", d],
                      "inputs": [f"configs/v3/pilot/{prof}.json"], "outputs": [f"{d}/checkpoints/final.pt", f"{d}/DONE.json"]})
        mx = {"name": f"v3_pilot_{prof}_s{seed}", "suite": "configs/v3/suites/development.jsonl", "num_envs": 144,
              "protocol": f"configs/v3/pilot/{prof}.json", "trace_cases": ["v3-development-mixed_id-0000"],
              "entries": [{"id": f"{prof}_s{seed}_final", "method": PROFILES[prof], "training_seed": seed, "trace": True,
                           "checkpoint": f"{prof}_s{seed}/checkpoints/final.pt", "conditions": dev_strata}]}
        mp = ROOT / f"configs/v3/pilot/matrices/{prof}_s{seed}.json"
        mp.parent.mkdir(parents=True, exist_ok=True)
        mp.write_text(json.dumps(mx, indent=1) + "\n")
        e = mx["entries"][0]["id"]
        tasks.append({"id": f"pilot_eval_{prof}_s{seed}", "kind": "isaac",
                      "argv": ["scripts/eval_matrix.py", "--matrix", f"configs/v3/pilot/matrices/{prof}_s{seed}.json",
                               "--checkpoint-root", "$RUNS/pilot", "--output", f"$RUNS/pilot_eval/{prof}_s{seed}", "--seed", str(SEED_EVAL)],
                      "inputs": [f"configs/v3/pilot/matrices/{prof}_s{seed}.json"],
                      "outputs": [f"$RUNS/pilot_eval/{prof}_s{seed}/{e}.jsonl"]})
    write("pilots", [t for t in tasks if t["id"].startswith("pilot_") and not t["id"].startswith("pilot_eval_")])
    write("pilot_eval", [t for t in tasks if t["id"].startswith("pilot_eval_")])  # run after all pilots finished


# ------------------------------------------------------------------------------ formal stages
FROZEN = ROOT / "configs/v3/frozen/training"
CANDIDATE_TAGS = ["step_002031616", "step_004030464", "step_006029312", "step_008028160", "step_010027008"]
FINAL_BATCH = 256
TRACE_FINAL = ["v3-final-mixed_id-0000", "v3-final-mixed_id-0001", "v3-final-mixed_ood-0000", "v3-final-mixed_ood-0001",
               "v3-final-noise_4mm-0000", "v3-final-clean-0000"]


def runs():
    out = []
    for prof, method in PROFILES.items():
        prot = json.loads((FROZEN / f"{prof}.json").read_text())
        for seed in prot["training"]["seeds"]:
            out.append((prof, method, seed))
    return out


def train():
    tasks = []
    for prof, method, seed in runs():
        d = f"$RUNS/train/{prof}_s{seed}"
        tasks.append({"id": f"train_{prof}_s{seed}", "kind": "isaac",
                      "argv": ["scripts/train.py", "--method", method, "--seed", str(seed), "--protocol",
                               f"configs/v3/frozen/training/{prof}.json", "--run-type", "final", "--output", d],
                      "inputs": [f"configs/v3/frozen/training/{prof}.json"], "outputs": [f"{d}/checkpoints/final.pt", f"{d}/DONE.json"]})
    write("train", tasks)


def validation_matrices():
    """Committed before freeze: candidate tags are fixed by the rollout size (first save at/after 2,4,6,8,10M)."""
    d = ROOT / "configs/v3/frozen/matrices/validation"
    d.mkdir(parents=True, exist_ok=True)
    for prof, method, seed in runs():
        ents = [{"id": f"{prof}_s{seed}__step0", "method": method, "training_seed": seed, "role": "untrained_control",
                 "checkpoint": f"{prof}_s{seed}/checkpoints/step_000000000.pt"}]
        ents += [{"id": f"{prof}_s{seed}__{t}", "method": method, "training_seed": seed, "role": "candidate",
                  "checkpoint": f"{prof}_s{seed}/checkpoints/{t}.pt"} for t in CANDIDATE_TAGS]
        (d / f"{prof}_s{seed}.json").write_text(json.dumps({"name": f"v3_validation_{prof}_s{seed}",
            "suite": "configs/v3/suites/validation.jsonl", "num_envs": 240, "protocol": f"configs/v3/frozen/training/{prof}.json",
            "trace_cases": [], "entries": ents}, indent=1) + "\n")


def validation():
    tasks = []
    for prof, method, seed in runs():
        mp = f"configs/v3/frozen/matrices/validation/{prof}_s{seed}.json"
        for e in json.loads((ROOT / mp).read_text())["entries"]:
            tasks.append({"id": f"val_{e['id']}", "kind": "isaac",
                          "argv": ["scripts/eval_matrix.py", "--matrix", mp, "--only", e["id"], "--checkpoint-root", "$RUNS/train",
                                   "--output", f"$RUNS/validation/{prof}_s{seed}/{e['id']}", "--seed", str(SEED_EVAL)],
                          "inputs": [mp], "outputs": [f"$RUNS/validation/{prof}_s{seed}/{e['id']}/{e['id']}.jsonl"]})
    write("validation", tasks)


def baseline_entries():
    sel = json.loads((ROOT / "configs/v3/baseline_selection.json").read_text())["roles"]
    draft = json.loads((ROOT / "configs/v3/protocol.draft.json").read_text())["sensor"]
    out = {}
    for role, s in sel.items():
        if role == "nominal":
            base, ent = {"observation_sensor": {**draft, "ema_alpha": 1.0}, "observation_giver_reference": False}, \
                {"id": role, "method": "nominal", "trace": True}
        else:
            base = {"observation_sensor": {**draft, "ema_alpha": s["ema_alpha"]}, "observation_giver_reference": bool(s["giver_reference"])}
            ov = {"align_max": s["align_max_m"]}
            if s["constant_x_m"]:
                ov["constant_residual_m"] = [s["constant_x_m"], 0.0, 0.0]
            ent = {"id": role, "method": "geometry", "overrides": ov, "trace": True}
        out[role] = (base, ent)
    return out


def final():
    """After checkpoint selection (results/v3/selection/selection.json)."""
    selp = ROOT / "results/v3/selection/selection.json"
    sel = json.loads(selp.read_text())
    d = ROOT / "configs/v3/final_matrices"
    d.mkdir(parents=True, exist_ok=True)
    tasks = []
    selroles = json.loads((ROOT / "configs/v3/baseline_selection.json").read_text())["roles"]
    order = ["nominal", "geometry_common", "geometry_best_constant", "geometry_raw", "geometry_filtered", "geometry_giver"]
    first_of = {}
    aliases = {}
    for role in order:
        cid = selroles[role]["candidate_id"]
        if cid in first_of:
            aliases[role] = first_of[cid]  # identical configuration: evaluated once, recorded as an alias
        else:
            first_of[cid] = role
    (d / "baseline_aliases.json").write_text(json.dumps(aliases, indent=1, sort_keys=True) + "\n")
    for role, (base, ent) in baseline_entries().items():
        if role in aliases:
            continue
        mp = d / f"baseline_{role}.json"
        mp.write_text(json.dumps({"name": f"v3_final_{role}", "suite": "configs/v3/suites/final.jsonl", "num_envs": FINAL_BATCH,
                                  "protocol": "configs/v2/protocol.json", "base_overrides": base, "trace_cases": TRACE_FINAL,
                                  "entries": [ent]}, indent=1) + "\n")
        tasks.append({"id": f"final_{role}", "kind": "isaac", "argv": ["scripts/eval_matrix.py", "--matrix", "$DELIVERY/" + str(mp.relative_to(ROOT)),
                      "--only", role, "--output", f"$RUNS/final/{role}", "--seed", str(SEED_EVAL)],
                      "inputs": [str(mp.relative_to(ROOT))], "outputs": [f"$RUNS/final/{role}/{role}.jsonl"]})
    for prof, method, seed in runs():
        run = f"{prof}_s{seed}"
        ents = [{"id": f"{run}__selected", "method": method, "training_seed": seed, "role": "selected", "trace": True,
                 "checkpoint": f"{run}/checkpoints/{sel[run]['selected']}.pt"},
                {"id": f"{run}__final", "method": method, "training_seed": seed, "role": "final", "trace": True,
                 "checkpoint": f"{run}/checkpoints/final.pt"}]
        mp = d / f"{run}.json"
        mp.write_text(json.dumps({"name": f"v3_final_{run}", "suite": "configs/v3/suites/final.jsonl", "num_envs": FINAL_BATCH,
                                  "protocol": f"configs/v3/frozen/training/{prof}.json", "trace_cases": TRACE_FINAL,
                                  "entries": ents}, indent=1) + "\n")
        for e in ents:
            tasks.append({"id": f"final_{e['id']}", "kind": "isaac",
                          "argv": ["scripts/eval_matrix.py", "--matrix", "$DELIVERY/" + str(mp.relative_to(ROOT)), "--only", e["id"],
                                   "--checkpoint-root", "$RUNS/train", "--output", f"$RUNS/final/{run}/{e['role']}", "--seed", str(SEED_EVAL)],
                          "inputs": [str(mp.relative_to(ROOT))], "outputs": [f"$RUNS/final/{run}/{e['role']}/{e['id']}.jsonl"]})
    write("final", tasks)


def subset65():
    rows = [json.loads(l) for l in (ROOT / "configs/v3/suites/final.jsonl").read_text().splitlines() if l.strip()]
    by = {}
    for r in rows:
        by.setdefault(r["condition"], []).append(r)
    sub = [r for c in sorted(by) for r in sorted(by[c], key=lambda r: r["case_id"])[:5]]
    p = ROOT / "configs/v3/suites/final_subset65.jsonl"
    p.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in sub))
    return "$DELIVERY/configs/v3/suites/final_subset65.jsonl"


def extras():
    """Zero-policy controls, inference-time history interventions and repeatability (after selection)."""
    suite = subset65()
    sel = json.loads((ROOT / "results/v3/selection/selection.json").read_text())
    d = ROOT / "configs/v3/final_matrices/extras"
    d.mkdir(parents=True, exist_ok=True)
    tasks = []
    for prof, method in PROFILES.items():  # zero-policy (step 0) control per distinct profile, seed 11
        run = f"{prof}_s11"
        mp = d / f"zero_{prof}.json"
        mp.write_text(json.dumps({"name": f"v3_zero_{prof}", "suite": suite, "num_envs": 65,
                                  "protocol": f"configs/v3/frozen/training/{prof}.json", "trace_cases": [],
                                  "entries": [{"id": f"{run}__step0", "method": method, "training_seed": 11, "role": "untrained_control",
                                               "checkpoint": f"{run}/checkpoints/step_000000000.pt"}]}, indent=1) + "\n")
        tasks.append({"id": f"zero_{prof}", "kind": "isaac", "argv": ["scripts/eval_matrix.py", "--matrix", "$DELIVERY/" + str(mp.relative_to(ROOT)),
                      "--checkpoint-root", "$RUNS/train", "--output", f"$RUNS/zero_policy/{prof}", "--seed", str(SEED_EVAL)],
                      "inputs": [str(mp.relative_to(ROOT))], "outputs": [f"$RUNS/zero_policy/{prof}/{run}__step0.jsonl"]})
    hist = [(p, s) for p, m, s in runs() if p in ("combined_robust_history", "residual_robust_history")]
    for name, base in (("permuted", {"observation_history_permutation": [4, 2, 0, 3, 1]}),
                       ("current_only", {"observation_history_mode": "repeat_current"})):
        for prof, seed in hist:
            run = f"{prof}_s{seed}"
            mp = d / f"intervention_{name}_{run}.json"
            mp.write_text(json.dumps({"name": f"v3_intervention_{name}_{run}", "suite": suite, "num_envs": 65,
                                      "protocol": f"configs/v3/frozen/training/{prof}.json", "base_overrides": base, "trace_cases": [],
                                      "entries": [{"id": f"{run}__selected__{name}", "method": PROFILES[prof], "training_seed": seed,
                                                   "role": f"intervention_{name}", "allow_config_mismatch": True,
                                                   "intervention": base, "checkpoint": f"{run}/checkpoints/{sel[run]['selected']}.pt"}]},
                                     indent=1) + "\n")
            tasks.append({"id": f"int_{name}_{run}", "kind": "isaac", "argv": ["scripts/eval_matrix.py", "--matrix", "$DELIVERY/" + str(mp.relative_to(ROOT)),
                          "--checkpoint-root", "$RUNS/train", "--output", f"$RUNS/interventions/{name}/{run}", "--seed", str(SEED_EVAL)],
                          "inputs": [str(mp.relative_to(ROOT))], "outputs": [f"$RUNS/interventions/{name}/{run}/{run}__selected__{name}.jsonl"]})
    rep = []
    for role in ("geometry_common", "geometry_best_constant"):
        base, ent = baseline_entries()[role]
        mp = d / f"repeat_{role}.json"
        mp.write_text(json.dumps({"name": f"v3_repeat_{role}", "suite": suite, "num_envs": 23, "protocol": "configs/v2/protocol.json",
                                  "base_overrides": base, "trace_cases": [], "entries": [ent]}, indent=1) + "\n")
        rep.append((role, mp, None))
    for p, m, s in runs():
        if p == "combined_robust_history":
            run = f"{p}_s{s}"
            mp = d / f"repeat_{run}.json"
            mp.write_text(json.dumps({"name": f"v3_repeat_{run}", "suite": suite, "num_envs": 23,
                                      "protocol": f"configs/v3/frozen/training/{p}.json", "trace_cases": [],
                                      "entries": [{"id": f"{run}__selected", "method": m, "training_seed": s, "role": "selected",
                                                   "checkpoint": f"{run}/checkpoints/{sel[run]['selected']}.pt"}]}, indent=1) + "\n")
            rep.append((f"{run}__selected", mp, "$RUNS/train"))
    for eid, mp, ck in rep:
        for ps in (6455601, 6455602, 6455603):
            for b in (1, 23):
                tasks.append({"id": f"rep_{eid}_p{ps}_b{b}", "kind": "isaac",
                              "argv": ["scripts/eval_matrix.py", "--matrix", "$DELIVERY/" + str(mp.relative_to(ROOT)), "--num-envs", str(b),
                                       "--output", f"$RUNS/repeatability/b{b}/p{ps}/{eid}", "--seed", str(ps)]
                                      + (["--checkpoint-root", ck] if ck else []),
                              "inputs": [str(mp.relative_to(ROOT))], "outputs": [f"$RUNS/repeatability/b{b}/p{ps}/{eid}/{eid}.jsonl"]})
    write("extras", tasks)


def verification():
    """Stage 7 (published release): predeclared 65-case replay and a two-iteration resume check, run against
    the EXTRACTED download (--runs-root <extracted dir>); outputs go to replay65/ and resume_check/."""
    d = ROOT / "configs/v3/final_matrices/extras"
    tasks = []
    for mp in sorted(d.glob("repeat_*.json")):
        mx = json.loads(mp.read_text())
        e = mx["entries"][0]["id"]
        ck = ["--checkpoint-root", "$RUNS/formal/train"] if mx["entries"][0].get("checkpoint") else []
        tasks.append({"id": f"replay65_{e}", "kind": "isaac",
                      "argv": ["scripts/eval_matrix.py", "--matrix", "$DELIVERY/" + str(mp.relative_to(ROOT)), "--num-envs", "23",
                               "--output", f"$RUNS/replay65/{e}", "--seed", str(SEED_EVAL)] + ck,
                      "inputs": [str(mp.relative_to(ROOT))], "outputs": [f"$RUNS/replay65/{e}/{e}.jsonl"]})
    sel = json.loads((ROOT / "results/v3/selection/selection.json").read_text())
    rows = [json.loads(l) for l in (ROOT / "configs/v3/suites/final.jsonl").read_text().splitlines() if l.strip()]
    first = {}
    for r in sorted(rows, key=lambda r: r["case_id"]):
        first.setdefault(r["condition"], r)
    sp = ROOT / "configs/v3/suites/final_reload13.jsonl"
    sp.write_text("".join(json.dumps(first[c], sort_keys=True) + "\n" for c in sorted(first)))
    for prof, method in PROFILES.items():  # reload every distinct architecture/estimator profile from the download
        if prof == "combined_robust_history":
            continue  # reloaded by the 65-case replay
        run_ = f"{prof}_s11"
        mp = d / f"reload_{prof}.json"
        mp.write_text(json.dumps({"name": f"v3_reload_{prof}", "suite": "$DELIVERY/configs/v3/suites/final_reload13.jsonl",
                                  "num_envs": 13, "protocol": f"configs/v3/frozen/training/{prof}.json", "trace_cases": [],
                                  "entries": [{"id": f"{run_}__selected", "method": method, "training_seed": 11, "role": "selected",
                                               "checkpoint": f"{run_}/checkpoints/{sel[run_]['selected']}.pt"}]}, indent=1) + "\n")
        tasks.append({"id": f"reload_{prof}", "kind": "isaac",
                      "argv": ["scripts/eval_matrix.py", "--matrix", "$DELIVERY/" + str(mp.relative_to(ROOT)),
                               "--checkpoint-root", "$RUNS/formal/train", "--output", f"$RUNS/reload/{prof}", "--seed", str(SEED_EVAL)],
                      "inputs": [str(mp.relative_to(ROOT))], "outputs": [f"$RUNS/reload/{prof}/{run_}__selected.jsonl"]})
    run = "combined_robust_history_s11"
    src = f"$RUNS/formal/train/{run}/checkpoints/latest.pt"
    out = f"$RUNS/resume_check/{run}"
    tasks.append({"id": "resume_check_train", "kind": "isaac",
                  "argv": ["scripts/train.py", "--method", "combined", "--seed", "11", "--protocol",
                           "configs/v3/frozen/training/combined_robust_history.json", "--run-type", "smoke",
                           "--resume", src, "--transitions", "10092544", "--output", out],
                  "inputs": [], "outputs": [f"{out}/checkpoints/final.pt"]})
    tasks.append({"id": "resume_check_inspect", "kind": "isaac",
                  "argv": ["scripts/closeout_inspect_ckpt.py", "--before", src, "--after", f"{out}/checkpoints/final.pt",
                           "--expect-iterations", "308", "--expect-transitions", "10092544", "--output", f"$RUNS/resume_check/inspect.json"],
                  "inputs": [], "outputs": ["$RUNS/resume_check/inspect.json"]})
    write("verification", tasks)


if __name__ == "__main__":
    for stage in sys.argv[1:]:
        {"acceptance": acceptance, "development": development, "cache": cache, "pilots": pilots,
         "train": train, "validation_matrices": validation_matrices, "validation": validation, "final": final,
         "extras": extras, "verification": verification}[stage]()
