#!/usr/bin/env python3
"""V5 Study B development inputs (CPU, deterministic). Development cases only; nothing here is a final result.

    python3 scripts/v5_slip_dev.py probe       # configs/v5/slip/development/probe/*  (feasibility probe, section 3.2)
    python3 scripts/v5_slip_dev.py probe2      # probe round 2 (near-full squeeze)
    python3 scripts/v5_slip_dev.py grid        # development suite + training-free candidate matrices (section 3.3)
    python3 scripts/v5_slip_dev.py select --runs <dir>   # baseline_selection.json (V4 ranking, development only)

The probe evaluates the training-free calibrated parent (V4 geometry_calibrated) under candidate slip-mechanism
parameter sets (runtime entries in one process), checks that a no-slip case is unchanged by enabling the
mechanism (same suite, same layout, mechanism off vs on, traced), and runs the three negative controls with slip.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from csci645_handover import v5_protocol as v5  # noqa: E402

DEV = ROOT / "configs/v5/slip/development"
SENSOR = {"bias_bound_m": 0.005, "noise_std_m": 0.002, "delay_steps": 2, "max_delay_steps": 8, "ema_alpha": 0.2,
          "clean_probability": 0.25}
PARENT_BASE = {"observation_sensor": SENSOR, "observation_giver_reference": True, "grasp_uncertainty": True}
PARENT_ENTRY = {"align_max": 0.025, "giver_calibration_window_s": 0.5}  # V4 geometry_calibrated (ema0p2_cal050_a25)
GAINS = {"finger_stiffness": 2000.0, "kp": 6000.0, "kd": 60.0, "ki": 60000.0, "regrip_s": 0.1, "tolerance_m": 0.0015}
MECHANISMS = {  # candidate parameter sets (relaxed squeeze, force cap); chosen by the probe, not by outcomes
    "M1": {**GAINS, "grip_force_n": 6.0, "force_max_n": 30.0},
    "M2": {**GAINS, "grip_force_n": 12.0, "force_max_n": 45.0},
    "M3": {**GAINS, "grip_force_n": 20.0, "force_max_n": 60.0},
}
# Round 2 (after round 1 showed vertical sag while sliding under a relaxed squeeze; docs/v5/DECISIONS.md):
# near-full / full squeeze (the closed command gives ~17.3 N measured per finger, i.e. grip_force_n ~35) and a
# larger force cap; two gain sets.
GAINS2 = {**GAINS, "kp": 12000.0, "kd": 80.0, "ki": 150000.0}
MECHANISMS_R2 = {
    "M4": {**GAINS2, "grip_force_n": 28.0, "force_max_n": 70.0},
    "M5": {**GAINS2, "grip_force_n": 35.0, "force_max_n": 90.0},
    "M6": {**GAINS, "grip_force_n": 35.0, "force_max_n": 90.0},
}


def jl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    return str(path.relative_to(ROOT))


def put(name: str, mx: dict) -> str:
    p = DEV / "probe" / f"{name}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(mx, indent=1) + "\n")
    return str(p.relative_to(ROOT))


def probe(mechs=None, tag=""):
    mechs = mechs or MECHANISMS
    rows = v5.probe_cases()
    s_all = jl(DEV / "probe/probe_suite.jsonl", rows)
    noslip = [r for r in rows if r["condition"] == "noslip"]
    s_noslip = jl(DEV / "probe/noslip_suite.jsonl", noslip)
    neg = [r for r in rows if r["condition"] in ("x+10_on105", "x+15_on105", "x-5_on105")]
    s_neg = jl(DEV / "probe/negative_suite.jsonl", neg)
    traced = [f"{v5.PREFIX}probe-development-{c}-0000" for c in ("noslip", "x+15_on140", "x-7_on070", "x+5_on105")]
    first = next(iter(mechs))
    base = {**PARENT_BASE, "slip_mechanism": mechs[first]}
    ents = []
    for m, spec in mechs.items():
        ents.append({"id": f"calibrated_{m}", "method": "geometry", "overrides": {**PARENT_ENTRY, "slip_mechanism": spec},
                     "trace": True})
    if not tag:
        ents.append({"id": "nominal_M2", "method": "nominal", "overrides": {"slip_mechanism": MECHANISMS["M2"]}, "trace": False})
    out = {"mechanisms": mechs, "matrices": {}}
    out["matrices"]["mechanisms"] = put(f"mechanisms{tag}", {
        "name": f"v5_probe_mechanisms{tag}", "suite": s_all, "num_envs": len(rows), "protocol": "configs/v2/protocol.json",
        "base_overrides": base, "trace_cases": traced, "entries": ents})
    # no-slip equivalence: identical suite and layout, mechanism off (V4 configuration) vs on
    noslip_ents = [{"id": "geometry_calibrated", "method": "geometry", "overrides": dict(PARENT_ENTRY), "trace": True},
                   {"id": "nominal", "method": "nominal", "overrides": {}, "trace": True}]
    tr = [r["case_id"] for r in noslip]
    if not tag:
        out["matrices"]["noslip_off"] = put("noslip_off", {
            "name": "v5_probe_noslip_off", "suite": s_noslip, "num_envs": len(noslip),
            "protocol": "configs/v2/protocol.json", "base_overrides": PARENT_BASE, "trace_cases": tr,
            "entries": noslip_ents})
    out["matrices"]["noslip_on"] = put(f"noslip_on{tag}", {
        "name": f"v5_probe_noslip_on{tag}", "suite": s_noslip, "num_envs": len(noslip), "protocol": "configs/v2/protocol.json",
        "base_overrides": base, "trace_cases": tr,
        "entries": [{**e, "overrides": {**e["overrides"], "slip_mechanism": mechs[first] if tag else MECHANISMS["M2"]}} for e in noslip_ents]})
    for ctl, extra in (("no_receiver", {}), ("giver_holds", {}), ("table_support", {"table_size_override": [0.06, 0.3, 0.2]})):
        out["matrices"][f"neg_{ctl}"] = put(f"neg_{ctl}{tag}", {
            "name": f"v5_probe_neg_{ctl}{tag}", "suite": s_neg, "num_envs": len(neg), "protocol": "configs/v2/protocol.json",
            "base_overrides": {**base, "negative_control": ctl, **extra}, "trace_cases": [],
            "entries": [{"id": f"calibrated_{m}", "method": "geometry", "overrides": {**PARENT_ENTRY, "slip_mechanism": spec}}
                        for m, spec in mechs.items()]})
    (DEV / f"probe/probe_setup{tag}.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out["matrices"].items()}, indent=1), len(rows), "probe cases")


# ------------------------------------------------------------------------------------------- development grid
TRACKING = [(0.05, 0.025), (0.1, 0.025), (0.2, 0.025), (0.4, 0.025), (0.2, 0.035), (0.4, 0.035)]  # (alpha, bound)
CONSTANTS_X = (-0.004, -0.002, 0.002, 0.004)  # on the calibrated parent; 0 is the parent itself
SENSOR_FIXED = {**SENSOR, "ema_alpha": 1.0}
RULE = ("development cases only; strata = the four V5 validation conditions (clean, static_mixed_id, slip_pos_10, "
        "slip_mixed_id), equal weight, 24 cases each, all scheduled cases in the denominator: success rate desc, "
        "unsafe-event rate asc (any prohibited collision or drop), correction magnitude asc (geometry: mean |alignment "
        "correction|; constant offsets: |c|), mean completion time of successes asc, candidate ID asc (V4 rule).")


def candidates():
    c = [{"id": "nominal", "method": "nominal", "group": "a", "overrides": {}},
         {"id": "geometry_calibrated", "method": "geometry", "group": "a", "overrides": dict(PARENT_ENTRY)},
         {"id": "geometry_fixed", "method": "geometry", "group": "fixed", "overrides": {"align_max": 0.015}},
         {"id": "geometry_ema", "method": "geometry", "group": "ema", "overrides": {"align_max": 0.025}}]
    for a, b in TRACKING:
        c.append({"id": f"tracking_a{int(round(a * 100)):03d}_b{int(round(b * 1000))}", "method": "geometry", "group": "a",
                  "kind": "tracking", "overrides": {"align_max": b, "giver_calibration_window_s": 0.5, "giver_tracking_alpha": a}})
    for x in CONSTANTS_X:
        c.append({"id": f"calibrated_const_x{x * 1000:+.0f}", "method": "geometry", "group": "a", "kind": "constant",
                  "overrides": {**PARENT_ENTRY, "constant_residual_m": [x, 0.0, 0.0]}})
    return c


def grid():
    rows = v5.make_cases("development")
    s = jl(DEV / "suites/development.jsonl", rows)
    mech = v5.SLIP_MECHANISM
    bases = {"a": {**PARENT_BASE, "slip_mechanism": mech},
             "fixed": {**PARENT_BASE, "observation_sensor": SENSOR_FIXED, "slip_mechanism": mech},
             "ema": {**PARENT_BASE, "observation_giver_reference": False, "slip_mechanism": mech}}
    trace = [f"{v5.PREFIX}-development-{c}-0000" for c in ("slip_mixed_id", "slip_pos_10", "clean")]
    cs = candidates()
    out = {}
    for g, base in bases.items():
        ents = [{"id": c["id"], "method": c["method"], "overrides": c["overrides"], "trace": True} for c in cs if c["group"] == g]
        p = DEV / "matrices" / f"dev_{g}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"name": f"v5_slip_dev_{g}", "suite": s, "num_envs": len(rows),
                                 "protocol": "configs/v2/protocol.json", "base_overrides": base, "trace_cases": trace,
                                 "entries": ents}, indent=1) + "\n")
        out[g] = str(p.relative_to(ROOT))
    reg = {"rule": RULE, "suite": s, "suite_sha256": v5.v4.sha256(ROOT / s), "mechanism": mech,
           "cumulative_x_m": list(v5.CUMULATIVE_X), "candidates": cs, "matrices": out}
    (DEV / "baseline_grid.json").write_text(json.dumps(reg, indent=1) + "\n")
    print(json.dumps(out, indent=1), len(rows), "development cases,", len(cs), "candidates")


def _score(rows, magnitude):
    by = {}
    for r in rows:
        if r["condition"] in v5.VALIDATION:
            by.setdefault(r["condition"], []).append(r)
    if sorted(by) != sorted(v5.VALIDATION) or any(len(v) != v5.SPLIT_COUNTS["development"] for v in by.values()):
        raise SystemExit("incomplete development strata")
    w = 1.0 / len(by)
    succ = sum(w * sum(r["success"] for r in v) / len(v) for v in by.values())
    unsafe = sum(w * sum(bool(r["collision"]) or r["terminal_reason"] == "drop" for r in v) / len(v) for v in by.values())
    times = [r["completion_time_s"] for v in by.values() for r in v if r["success"]]
    return {"success": succ, "unsafe": unsafe, "magnitude": magnitude(rows),
            "completion_time": sum(times) / len(times) if times else float("inf"),
            "invalid_resets": sum(not r["reset_valid"] for v in by.values() for r in v),
            "invalid_slips": sum(r["terminal_reason"] == "invalid_slip" for v in by.values() for r in v),
            "per_condition_success": {c: sum(r["success"] for r in v) / len(v) for c, v in sorted(by.items())}}


def _key(s, cid):
    return (-round(s["success"], 12), round(s["unsafe"], 12), round(s["magnitude"], 12), round(s["completion_time"], 12), cid)


def _align_mag(rows):
    vals = [sum(x * x for x in r["align_correction_mean_xyz_m"]) ** 0.5 for r in rows if r["condition"] in v5.VALIDATION]
    return sum(vals) / len(vals)


def select(runs: Path):
    reg = json.loads((DEV / "baseline_grid.json").read_text())
    cs = {c["id"]: c for c in reg["candidates"]}
    scores, all_cond = {}, {}
    for cid, c in cs.items():
        hits = list(runs.glob(f"**/{cid}.jsonl"))
        if len(hits) != 1:
            raise SystemExit(f"{cid}: expected one record file, found {len(hits)}")
        rows = [json.loads(x) for x in hits[0].read_text().splitlines() if x.strip()]
        if {r["suite_hash"] for r in rows} != {reg["suite_sha256"]} or any(r["source_dirty"] for r in rows):
            raise SystemExit(f"{cid}: stale suite or dirty source")
        if c.get("kind") == "constant":
            mag = lambda rows, v=c["overrides"]["constant_residual_m"]: sum(x * x for x in v) ** 0.5  # noqa: E731
        else:
            mag = _align_mag
        scores[cid] = _score(rows, mag)
        by = {}
        for r in rows:
            by.setdefault(r["condition"], []).append(r["success"])
        all_cond[cid] = {k: sum(v) / len(v) for k, v in sorted(by.items())}
    best = lambda ids: min(ids, key=lambda c: _key(scores[c], c))  # noqa: E731
    tracking = best([c for c in cs if cs[c].get("kind") == "tracking"])
    constant = best([c for c in cs if cs[c].get("kind") == "constant"] + ["geometry_calibrated"])
    training_free = [c for c in cs]
    roles = {"nominal": "nominal", "geometry_fixed": "geometry_fixed", "geometry_ema": "geometry_ema",
             "geometry_calibrated": "geometry_calibrated", "geometry_tracking": tracking,
             "best_constant_geometry": constant, "geometry_best": best(training_free)}
    out = {"status": "selected on development data only", "rule": reg["rule"], "suite_sha256": reg["suite_sha256"],
           "scores": scores, "success_by_condition_all_development": all_cond,
           "ranking": sorted(cs, key=lambda c: _key(scores[c], c)),
           "roles": {r: {"candidate_id": c, **cs[c], **{f"selection_{k}": v for k, v in scores[c].items()
                                                        if k != "per_condition_success"}} for r, c in roles.items()}}
    (DEV / "baseline_selection.json").write_text(json.dumps(out, indent=1) + "\n")
    for c in out["ranking"]:
        s = scores[c]
        print(f"{c:28s} succ={s['success']:.4f} unsafe={s['unsafe']:.4f} mag={s['magnitude'] * 1000:.2f}mm "
              f"inv_slip={s['invalid_slips']} {s['per_condition_success']}")
    print({r: c for r, c in roles.items()})


if __name__ == "__main__":
    if sys.argv[1] == "select":
        select(Path(sys.argv[sys.argv.index("--runs") + 1]))
    else:
        {"probe": probe, "probe2": lambda: probe(MECHANISMS_R2, "_r2"), "grid": grid}[sys.argv[1]]()
