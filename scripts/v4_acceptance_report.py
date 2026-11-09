#!/usr/bin/env python3
"""Judge the V4 acceptance runs (CPU, standard library only).

    python3 -I scripts/v4_acceptance_report.py --acc <acceptance runs root> --dev <development runs root> \
        --output results/v4/acceptance/acceptance.json

Each check reports its measurements, a pass flag and the exact rule. Hard rules (must hold exactly): A1 V3 path
equals published V3 outcomes/specs/hashes; A2 zero-offset V4 path equals published V3 outcomes; A3 no success
under any negative control; A6/A8 privileged perturbation changes no controller quantity or outcome; A7 a
zero-mean (step-0) residual reproduces its parent's outcomes; resume checks ok; A9 cache test ok; A4/A5 the
exogenous case parameters (sensor spec, requested grasp offset) are identical per case across layouts.
Measured (reported, threshold stated): A4/A5 outcome agreement across batch layouts and calibration-estimate
differences (PhysX trajectories may differ with batch layout; the threshold is >= 95% agreement and every
disagreement is listed).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER_TRACE = ("p_exec", "p_cand", "residual", "raw_action", "align_corr", "released", "release_cmd_time",
                    "finger_cmd_giver", "finger_cmd_recv", "controller_obj_pos", "estimated_obj_pos", "observed_obj_pos",
                    "stable", "anchored", "t", "mode")
PRIVILEGED = ("grasp_offset_achieved_xyz_m",)


def jl(p: Path) -> dict:
    return {json.loads(l)["case_id"]: json.loads(l) for l in p.read_text().splitlines() if l.strip()}


def same_outcomes(a: dict, b: dict) -> dict:
    common = sorted(set(a) & set(b))
    diff = [c for c in common if a[c]["terminal_reason"] != b[c]["terminal_reason"]]
    return {"cases": len(common), "missing": sorted(set(a) ^ set(b)), "agree": len(common) - len(diff),
            "disagreements": [{"case": c, "a": a[c]["terminal_reason"], "b": b[c]["terminal_reason"]} for c in diff]}


def cal_diff(a: dict, b: dict) -> float:
    m = 0.0
    for c in set(a) & set(b):
        x, y = a[c].get("calibration_offset_world_m"), b[c].get("calibration_offset_world_m")
        if x and y:
            m = max(m, max(abs(u - v) for u, v in zip(x, y)))
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--acc", required=True)
    ap.add_argument("--dev", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    A, D = Path(a.acc), Path(a.dev)
    sel = json.loads((ROOT / "configs/v4/development/baseline_selection.json").read_text())["roles"]
    parent_id = sel["common_parent"]["candidate_id"]
    idx = {(e["family"], e["role"], e["seed"]): e["records"] for e in json.loads((ROOT / "configs/v3/final_matrix_index.json").read_text())["entries"]}
    out = {}

    # A1 / A2
    pub_g = jl(A / "v3x" / idx[("geometry_common", "baseline", None)])
    pub_p = jl(A / "v3x" / idx[("combined_robust_history", "selected", 11)])
    for chk, gdir, pdir in (("A1_v3_path", "a1_v3path_geometry", "a1_v3path_policy"), ("A2_v4_zero_offset", "a2_v4zero_geometry", "a2_v4zero_policy")):
        g = jl(A / gdir / "geometry_common.jsonl")
        p = jl(A / pdir / "v3_combined_robust_history_s11__selected.jsonl")
        so_g, so_p = same_outcomes(g, {c: pub_g[c] for c in g}), same_outcomes(p, {c: pub_p[c] for c in p})
        r = {"geometry_common": so_g, "policy_s11_selected": so_p,
             "observation_error_equal": all(g[c]["observation_error"] == pub_g[c]["observation_error"] for c in g),
             "checkpoint_sha256_equal": all(p[c]["checkpoint_sha256"] == pub_p[c]["checkpoint_sha256"] for c in p)}
        if chk.startswith("A1"):
            r["config_hash_equal_to_v3"] = all(g[c]["config_hash"] == pub_g[c]["config_hash"] for c in g) and \
                all(p[c]["config_hash"] == pub_p[c]["config_hash"] for c in p)
        r["pass"] = (so_g["cases"] == so_g["agree"] == 65 and so_p["cases"] == so_p["agree"] == 65 and r["observation_error_equal"]
                     and r["checkpoint_sha256_equal"] and r.get("config_hash_equal_to_v3", True))
        out[chk] = r

    # A3 negative controls
    neg = {}
    for ctl in ("no_receiver", "giver_holds", "table_support"):
        for e in ("nominal", "parent"):
            rows = jl(A / f"a3_neg_{ctl}" / f"{e}.jsonl")
            neg[f"{ctl}/{e}"] = {"cases": len(rows), "success": sum(r["success"] for r in rows.values()),
                                 "terminal": sorted({r["terminal_reason"] for r in rows.values()}),
                                 "invalid_resets": sum(not r["reset_valid"] for r in rows.values())}
    out["A3_negative_controls"] = {"runs": neg, "pass": all(v["success"] == 0 and v["cases"] == 16 for v in neg.values())}

    # A4 layout
    lay = {t: jl(A / f"a4_layout_{t}" / "parent.jsonl") for t in ("b1", "b8", "b72", "b72rev")}
    base = lay["b72"]
    exo = all(lay[t][c]["observation_error"] == base[c]["observation_error"] and
              lay[t][c]["grasp_offset_requested_xyz_m"] == base[c]["grasp_offset_requested_xyz_m"] for t in lay for c in base)
    cmp_ = {t: {**same_outcomes(lay[t], base), "max_calibration_diff_m": cal_diff(lay[t], base)} for t in ("b1", "b8", "b72rev")}
    out["A4_layout"] = {"exogenous_parameters_identical": exo, "vs_b72": cmp_,
                        "pass": exo and all(v["cases"] == 72 and v["agree"] >= 0.95 * 72 for v in cmp_.values())}

    # A5 leakage: 18 consecutive episodes per env vs one episode per env
    hits = list(D.glob(f"**/{parent_id}.jsonl"))
    ref = jl(hits[0])
    leak = jl(A / "a5_leak_b16" / "parent.jsonl")
    s5 = same_outcomes(leak, ref)
    exo5 = all(leak[c]["observation_error"] == ref[c]["observation_error"] and
               leak[c]["grasp_offset_requested_xyz_m"] == ref[c]["grasp_offset_requested_xyz_m"] for c in leak)
    out["A5_reset_leakage"] = {"batch16_vs_batch288": {**s5, "max_calibration_diff_m": cal_diff(leak, ref)},
                               "exogenous_parameters_identical": exo5,
                               "invalid_resets": sum(not r["reset_valid"] for r in leak.values()),
                               "pass": exo5 and s5["cases"] == 288 and s5["agree"] >= 0.95 * 288}

    # A6 / A8 privileged perturbation
    def priv(d_off, d_on, entry):
        off, on = jl(A / d_off / f"{entry}.jsonl"), jl(A / d_on / f"{entry}.jsonl")
        t_off = json.loads((A / d_off / "traces" / f"{entry}.json").read_text())
        t_on = json.loads((A / d_on / "traces" / f"{entry}.json").read_text())
        bad_trace, steps, perturbed = [], 0, 0
        for c in t_off:
            ro, rn = t_off[c], t_on.get(c, [])
            if len(ro) != len(rn):
                bad_trace.append({"case": c, "len": [len(ro), len(rn)]})
                continue
            for x, y in zip(ro, rn):
                steps += 1
                if x.get("grasp_offset_true") != y.get("grasp_offset_true"):
                    perturbed += 1
                for k in CONTROLLER_TRACE:
                    if x.get(k) != y.get(k):
                        bad_trace.append({"case": c, "field": k})
                        break
        rec_bad = [c for c in off if {k: v for k, v in off[c].items() if k not in PRIVILEGED + ("config_hash", "controller_hash", "config_mismatch", "source_commit")}
                   != {k: v for k, v in on[c].items() if k not in PRIVILEGED + ("config_hash", "controller_hash", "config_mismatch", "source_commit")}]
        return {"cases": len(off), "traced_cases": len(t_off), "trace_steps": steps, "steps_with_perturbed_privileged_tensor": perturbed,
                "controller_trace_differences": bad_trace[:20], "record_differences": rec_bad[:20],
                "pass": not bad_trace and not rec_bad and perturbed > 0 and len(t_off) == len(off)}
    out["A6_privileged_parent"] = priv("a6_priv_off", "a6_priv_on", "parent")
    out["A8_privileged_policy"] = priv("a8_priv_policy_off", "a8_priv_policy_on", "history_smoke_final")

    # A7 zero residual reproduces its parent; resume; cache
    par = {"geometry": jl(A / "a7_parents" / "parent.jsonl"), "nominal": jl(A / "a7_parents" / "nominal.jsonl")}
    z, rs = {}, {}
    for f in sorted(A.glob("a7_zero_*")):
        prof = f.name[len("a7_zero_"):]
        step0 = jl(f / f"{prof}_step0.jsonl")
        ref_ = par["nominal" if prof.startswith("residual") else "geometry"]
        s = same_outcomes(step0, ref_)
        s["completion_time_equal"] = all(step0[c].get("completion_time_s") == ref_[c].get("completion_time_s") for c in step0)
        s["residual_abs_max_m"] = max(r["residual_abs_max_m"] for r in step0.values())
        z[prof] = s
        r = json.loads((A / f"resume_{prof}.json").read_text())
        rs[prof] = {"ok": r.get("ok"), "checks": r.get("checks")}
    out["A7_zero_residual_equals_parent"] = {"profiles": z, "pass": len(z) == 5 and all(
        v["cases"] == 72 == v["agree"] and v["residual_abs_max_m"] == 0.0 for v in z.values())}
    out["resume_smoke"] = {"profiles": rs, "pass": len(rs) == 5 and all(v["ok"] for v in rs.values())}
    cache = json.loads((A / "a9_cache.json").read_text())
    out["A9_eval_resume_and_tamper"] = {"result": cache, "pass": bool(cache.get("ok"))}
    out["all_pass"] = all(v["pass"] for v in out.values() if isinstance(v, dict) and "pass" in v)
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v["pass"] for k, v in out.items() if isinstance(v, dict)}, indent=1), "all_pass", out["all_pass"])


if __name__ == "__main__":
    main()
