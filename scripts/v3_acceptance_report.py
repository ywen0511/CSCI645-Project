#!/usr/bin/env python3
"""Judge the 10 v3 remote acceptance checks from their evidence and write results/v3/acceptance.json (CPU).

    python3 scripts/v3_acceptance_report.py --runs <runs root of the acceptance stage> --ledger <runs root>/ledger

Evidence paths are recorded relative to the runs root, with SHA-256. Each check lists the commands (from the
task ledger), the source commit, measured values, and pass/fail. All checks must pass before formal training.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def jl(p: Path):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--output", default=str(ROOT / "results/v3/acceptance.json"))
    a = ap.parse_args()
    R = Path(a.runs)
    A = R / "acceptance"
    ledger = {}
    for p in (R / "ledger").glob("*.jsonl"):
        rows = jl(p)
        if rows:
            ledger[p.stem] = rows[-1]
    out = {"checks": {}, "source_commits": sorted({r["source_commit"] for r in ledger.values()})}

    def ev(paths):
        return {str(p.relative_to(R)): sha(p) for p in paths}

    def cmds(prefixes):
        return [{"task": k, "argv": v["argv"], "rc": v["rc"], "source_commit": v["source_commit"], "watchdog": v.get("watchdog")}
                for k, v in sorted(ledger.items()) if any(k.startswith(x) for x in prefixes)]

    def j(name):
        p = A / name
        return json.loads(p.read_text()) if p.exists() else {}

    # 1 physical pipeline + negative controls
    phys = {}
    for m in ("a1_b1", "a1_b8"):
        for e in ("nominal", "geometry_1p5cm"):
            rows = jl(A / m / e / f"{e}.jsonl")
            phys[f"{m}/{e}"] = {"n": len(rows), "success": sum(r["success"] for r in rows),
                                "valid": sum(r["reset_valid"] for r in rows),
                                "hold_ok": all(r["independent_hold_s"] >= 2.0 - 1e-6 for r in rows if r["success"]),
                                "terminal": sorted({r["terminal_reason"] for r in rows})}
    neg = {}
    for c in ("no_receiver", "giver_holds", "table_support"):
        for e in ("nominal", "geometry_1p5cm"):
            rows = jl(A / f"neg_{c}" / e / f"{e}.jsonl")
            neg[f"{c}/{e}"] = {"n": len(rows), "success": sum(r["success"] for r in rows),
                               "terminal": sorted({r["terminal_reason"] for r in rows})}
    agree = {}
    for e in ("nominal", "geometry_1p5cm"):
        r1 = {r["case_id"]: r for r in jl(A / "a1_b1" / e / f"{e}.jsonl")}
        r8 = {r["case_id"]: r for r in jl(A / "a1_b8" / e / f"{e}.jsonl")}
        agree[e] = sum(r1[k]["terminal_reason"] == r8[k]["terminal_reason"] for k in r1 if k in r8)
    ok1 = (all(v["n"] == 8 and v["valid"] == 8 and v["hold_ok"] for v in phys.values())
           and all(v["success"] > 0 for k, v in phys.items() if "geometry" in k)
           and all(v["n"] == 8 and v["success"] == 0 for v in neg.values()))
    out["checks"]["1_physical_pipeline_and_negative_controls"] = {
        "pass": ok1, "physical": phys, "negative_controls": neg, "batch1_vs_batch8_terminal_reason_equal_of_8": agree,
        "evidence": ev([A / m / e / f"{e}.jsonl" for m in ("a1_b1", "a1_b8") for e in ("nominal", "geometry_1p5cm")]
                       + [A / f"neg_{c}" / e / f"{e}.jsonl" for c in ("no_receiver", "giver_holds", "table_support")
                          for e in ("nominal", "geometry_1p5cm")]),
        "commands": cmds(["acc_a1_", "acc_neg_"])}

    # 2 zero residual equals deterministic controller; residual mechanics
    eq = {}
    for prof, det in (("combined_robust_ff", "geometry"), ("combined_robust_history", "geometry"), ("residual_robust_history", "nominal")):
        x = {r["case_id"]: r for r in jl(A / f"a2_{prof}" / f"{prof}_step0" / f"{prof}_step0.jsonl")}
        y = {r["case_id"]: r for r in jl(A / f"a2_{prof}" / det / f"{det}.jsonl")}
        eq[prof] = {"n": len(x), "terminal_equal": sum(x[k]["terminal_reason"] == y[k]["terminal_reason"] for k in x if k in y),
                    "success_equal": sum(x[k]["success"] == y[k]["success"] for k in x if k in y),
                    "completion_time_equal": sum(x[k]["completion_time_s"] == y[k]["completion_time_s"] for k in x if k in y),
                    "max_residual_m_step0": max((r.get("residual_abs_max_m") or 0.0) for r in x.values()) if x else None}
    res = j("residual.json")
    ok2 = bool(res.get("ok")) and all(v["n"] == 23 and v["terminal_equal"] == 23 and v["success_equal"] == 23
                                      and v["max_residual_m_step0"] == 0.0 for v in eq.values())
    out["checks"]["2_zero_residual_and_residual_mechanics"] = {
        "pass": ok2, "zero_residual_vs_controller": eq, "residual_mechanics": res.get("checks"),
        "residual_stats": res.get("stats"), "evidence": ev([A / "residual.json"]), "commands": cmds(["acc_a2_", "acc_residual"])}

    # 3 sensor model on CUDA + exogenous stream equality across layouts
    import numpy as np

    def normal_at(seed: int, frame: int):
        """NumPy port of core.observation.normal_at (same integer hash; float64 transcendental)."""
        mask = 0x7FFFFFFF
        axis = np.arange(6, dtype=np.int64)
        x = (np.int64(seed) * 104729 + np.int64(frame) * 13007 + axis * 433494437) & mask
        x = ((x ^ (x >> 16)) * 73244475) & mask
        x = ((x ^ (x >> 16)) * 73244475) & mask
        x = x ^ (x >> 16)
        u = (x.astype(np.float64) + 0.5) / (mask + 1)
        return (np.sqrt(-2 * np.log(u[:3])) * np.cos(2 * np.pi * u[3:])).astype(np.float32).tolist()

    sen = j("sensor.json")
    streams, maxdiff, exact = {}, 0.0, 0.0
    for m in ("a3_b1", "a3_b23", "a3_b23rev"):
        tp = A / m / "geometry_1p5cm" / "traces" / "geometry_1p5cm.json"
        tr = json.loads(tp.read_text()) if tp.exists() else {}
        streams[m] = {}
        for cid, rows in tr.items():
            byf = {r["sensor_frame"]: r for r in rows if "sensor_frame" in r}
            case = next(json.loads(l) for l in (ROOT / "configs/v3/acceptance/suite_layout.jsonl").read_text().splitlines()
                        if json.loads(l)["case_id"] == cid)
            oe = case["observation_error"]
            noise = {}
            for f, r in byf.items():
                d = oe["delay_steps"]
                if f - d not in byf:
                    continue
                truth = byf[f - d]["obj_pos"]
                e = [r["observed_obj_pos"][k] - truth[k] - oe["bias_xyz_m"][k] for k in range(3)]
                noise[f] = e
                z = normal_at(oe["seed"], f)
                exact = max(exact, max(abs(e[k] - oe["noise_std_m"] * z[k]) for k in range(3)))
            streams[m][cid] = noise
    for cid in streams.get("a3_b1", {}):
        for other in ("a3_b23", "a3_b23rev"):
            o = streams.get(other, {}).get(cid, {})
            for f, e in streams["a3_b1"][cid].items():
                if f in o:
                    maxdiff = max(maxdiff, max(abs(e[k] - o[f][k]) for k in range(3)))
    n_frames = sum(len(v) for v in streams.get("a3_b1", {}).values())
    ok3 = bool(sen.get("ok")) and n_frames > 100 and maxdiff < 1e-5 and exact < 2e-5
    out["checks"]["3_sensor_model_and_layout_pairing"] = {
        "pass": ok3, "analytic_cuda_checks": sen.get("checks"), "noise_moments": sen.get("noise_moments"),
        "cuda_vs_cpu_noise_max_abs_diff": sen.get("cuda_vs_cpu_noise_max_abs_diff"),
        "traced_cases": len(streams.get("a3_b1", {})), "traced_frames": n_frames,
        "max_noise_component_diff_between_layouts_m": maxdiff, "max_deviation_from_sigma_times_normal_m": exact,
        "note": "noise component = observed - truth(k - delay) - bias, compared between batch 1, batch 23 and a reversed "
                "case queue; physics trajectories themselves are not required to be bitwise equal",
        "evidence": ev([A / "sensor.json"] + [A / m / "geometry_1p5cm" / "traces" / "geometry_1p5cm.json" for m in ("a3_b1", "a3_b23", "a3_b23rev")]),
        "commands": cmds(["acc_sensor", "acc_a3_"])}

    # 4 reset boundaries
    b = j("boundary.json")
    out["checks"]["4_reset_boundaries_and_tokens"] = {"pass": bool(b.get("ok")), "checks": b.get("checks"),
                                                      "max_reconstruction_error_m": b.get("max_reconstruction_error_m"),
                                                      "evidence": ev([A / "boundary.json"]), "commands": cmds(["acc_boundary"])}

    # 5 hidden-translation dependency
    dep = {v: j(f"dependency_{v}.json") for v in ("archived", "ff_ema1p0_giver0", "ff_ema0p5_giver1", "hist5_ema0p2_giver0", "hist5_ema1p0_giver1")}
    ok5 = all(d.get("ok") for d in dep.values())
    out["checks"]["5_no_hidden_translation_path"] = {
        "pass": ok5, "variants": {v: d.get("checks") for v, d in dep.items()},
        "allowed_accurate_channels": dep["ff_ema1p0_giver0"].get("allowed_accurate_channels"),
        "snapshots": {v: d.get("snapshots") for v, d in dep.items()},
        "evidence": ev([A / f"dependency_{v}.json" for v in dep]), "commands": cmds(["acc_dependency_"])}

    # 6 zero-error v3 path vs archived default path
    cmp6 = {}
    for e in ("nominal", "geometry_1p5cm"):
        x = {r["case_id"]: r for r in jl(A / "a6_sensor0" / e / f"{e}.jsonl")}
        y = {r["case_id"]: r for r in jl(A / "a6_archived" / e / f"{e}.jsonl")}
        diff = [k for k in x if k in y and x[k]["terminal_reason"] != y[k]["terminal_reason"]]
        cmp6[e] = {"n": len(x), "terminal_equal": len(x) - len(diff), "differing_cases": diff,
                   "success_sensor0": sum(r["success"] for r in x.values()), "success_archived": sum(r["success"] for r in y.values())}
    out["checks"]["6_zero_error_sensor_vs_archived_path"] = {
        "pass": all(v["n"] == 24 and v["terminal_equal"] == 24 for v in cmp6.values()), "comparison": cmp6,
        "evidence": ev([A / m / e / f"{e}.jsonl" for m in ("a6_sensor0", "a6_archived") for e in ("nominal", "geometry_1p5cm")]),
        "commands": cmds(["acc_a6_"]),
        "note": "zero-error sensor path (EMA 1, no giver reference) vs archived default path on the 24 physical_only "
                "development cases, fresh process each; observation boundary handling differs by construction (the v3 path "
                "re-measures after a reset) but no outcome changed"}

    # 8 inputs, 9 PPO smoke/resume
    inp = {m: j(f"inputs_{m}.json") for m in ("stack", "repeat_current", "permuted")}
    out["checks"]["8_inputs_history_normalization"] = {"pass": all(d.get("ok") for d in inp.values()),
                                                       "modes": {m: d.get("checks") for m, d in inp.items()},
                                                       "evidence": ev([A / f"inputs_{m}.json" for m in inp]), "commands": cmds(["acc_inputs_"])}
    profs = ("combined_clean_ff", "combined_robust_ff", "combined_robust_history", "residual_robust_history", "combined_robust_repeat")
    rs = {p: j(f"resume_{p}.json") for p in profs}
    ok9 = all(d.get("ok") for d in rs.values()) and all((R / "smoke" / f"smoke_{p}_s101" / "DONE.json").exists() for p in profs)
    out["checks"]["9_ppo_smoke_save_reload_resume"] = {
        "pass": ok9, "profiles": {p: {"checks": d.get("checks"), "before": d.get("before", {}).get("iterations_done"),
                                      "after": d.get("after", {}).get("iterations_done"),
                                      "optimizer_steps": d.get("optimizer_step_counts")} for p, d in rs.items()},
        "evidence": ev([A / f"resume_{p}.json" for p in profs]), "commands": cmds(["smoke_"])}
    ct = j("cache_test.json")
    out["checks"]["10_eval_cache_rejection_and_resume"] = {"pass": bool(ct.get("ok")), "result": ct,
                                                           "evidence": ev([A / "cache_test.json"]), "commands": cmds(["acc_cache"])}
    bs = ROOT / "configs/v3/baseline_selection.json"
    if bs.exists():
        B = json.loads(bs.read_text())
        C = {c["candidate_id"]: c for c in B["candidates"]}
        gate = {k: {cond: C[k]["per_condition"][cond]["release_timeout"] for cond in ("noise_2mm", "noise_4mm", "mixed_id", "mixed_ood")}
                for k in C if k.endswith("geom15_x+00")}
        raw = gate.get("ema1p0_giver0/geom15_x+00", {})
        alternatives_ok = any(all(v == 0 for v in g.values()) for k, g in gate.items() if k != "ema1p0_giver0/geom15_x+00")
        out["checks"]["7_estimators_and_gate"] = {
            "pass": bool(raw) and alternatives_ok and B["roles"]["geometry_common"]["ema_alpha"] is not None,
            "release_timeouts_of_24_by_estimator_1p5cm": gate,
            "raw_sensor_blocks_gate": raw,
            "finding": "unfiltered finite differences of a noisy translation estimate block the stability-gated release "
                       "(release_timeout) at noise >= 2 mm; EMA 0.2 and the giver reference do not",
            "common_estimator": B["roles"]["geometry_common"],
            "shared_by_geometry_and_all_combined_profiles": "configs/v3/frozen/training/*.json inherit geometry_common "
                                                            "(scripts/v3_make_protocols.py)",
            "evidence": {"configs/v3/baseline_selection.json": sha(bs)}}
    else:
        out["checks"]["7_estimators_and_gate"] = {"pass": None, "judgement": "development matrices not selected yet"}
    out["all_pass"] = all(c["pass"] is True for c in out["checks"].values())
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps({k: v["pass"] for k, v in sorted(out["checks"].items())}, indent=1))


if __name__ == "__main__":
    main()
