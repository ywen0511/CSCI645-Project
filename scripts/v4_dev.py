#!/usr/bin/env python3
"""V4 development stage (CPU, deterministic): suites, registered baseline grid, matrices, selection.

    python3 scripts/v4_dev.py suites                 # configs/v4/suites/{development,validation}.jsonl (+ SUITES.json)
    python3 scripts/v4_dev.py grid                   # configs/v4/development/baseline_grid.json + grid matrices
    python3 scripts/v4_dev.py select --runs <dev runs>          # configs/v4/development/baseline_selection.json
    python3 scripts/v4_dev.py constants --runs <dev runs>       # constant-residual search matrix (after select)
    python3 scripts/v4_dev.py select_constant --runs <dev runs> # adds best_constant_geometry to the selection

The grid is registered (committed) before any of its evaluations run. The final suite is NOT generated here; it
is produced after the freeze by scripts/v4_freeze.py with the same frozen generator.

Selection rule (development cases only; strata = the six validation conditions, equal weight, 24 cases each,
all scheduled cases in the denominator): success rate desc, unsafe-event rate asc (any prohibited collision or
drop), correction magnitude asc (geometry: mean |alignment correction|; constant search: |c|), mean completion
time of successes asc, candidate ID asc.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from csci645_handover import v4_protocol as v4  # noqa: E402

DEV = ROOT / "configs/v4/development"
SUITES = ROOT / "configs/v4/suites"
SENSOR = {"bias_bound_m": 0.005, "noise_std_m": 0.002, "delay_steps": 2, "max_delay_steps": 8, "ema_alpha": 1.0,
          "clean_probability": 0.25}
ALPHAS = (1.0, 0.5, 0.2)
REFERENCES = {"none": (False, None), "fixed": (True, None), "cal010": (True, 0.1), "cal025": (True, 0.25),
              "cal050": (True, 0.5)}
ALIGN = (0.015, 0.020)
CONSTANTS_X = (-0.010, -0.005, 0.0, 0.005, 0.010)
CONSTANTS_Z = (-0.005, 0.0, 0.005)
HISTORICAL = "ema1p0_fixed_a15"  # the V3 geometry_common configuration, carried unchanged
TRACE_DEV = ["v4-development-mixed_id-0000", "v4-development-grasp_10mm-0000", "v4-development-clean-0000"]


def tag(a: float) -> str:
    return f"ema{a:.1f}".replace(".", "p")


def suites():
    SUITES.mkdir(parents=True, exist_ok=True)
    meta = {"generator": "src/csci645_handover/v4_protocol.py:make_cases", "split_seeds": v4.SPLIT_SEEDS,
            "conditions": v4.CONDITIONS, "order": v4.ORDER, "validation_conditions": list(v4.VALIDATION), "suites": {}}
    for split, conds in (("development", v4.ORDER), ("validation", list(v4.VALIDATION))):
        rows = v4.make_cases(split, v4.CONDITIONS, conds)
        p = SUITES / f"{split}.jsonl"
        v4.write_jsonl(p, rows)
        meta["suites"][split] = {"path": str(p.relative_to(ROOT)), "cases": len(rows), "sha256": v4.sha256(p),
                                 "per_condition": v4.SPLIT_COUNTS[split]}
        print(split, len(rows))
    (SUITES / "SUITES.json").write_text(json.dumps(meta, indent=1, sort_keys=True) + "\n")


def grid_configs():
    out = [{"id": "nominal", "method": "nominal", "ema_alpha": 1.0, "reference": "none", "align_max_m": None}]
    for a in ALPHAS:
        for ref in REFERENCES:
            for al in ALIGN:
                out.append({"id": f"{tag(a)}_{ref}_a{round(al * 1000)}", "method": "geometry", "ema_alpha": a,
                            "reference": ref, "align_max_m": al})
    return out


def base_overrides(alpha: float, giver: bool) -> dict:
    return {"observation_sensor": {**SENSOR, "ema_alpha": alpha}, "observation_giver_reference": giver,
            "grasp_uncertainty": True}


def entry_overrides(cfg: dict) -> dict:
    ov = {}
    if cfg["align_max_m"] is not None:
        ov["align_max"] = cfg["align_max_m"]
    win = REFERENCES[cfg["reference"]][1]
    if win is not None:
        ov["giver_calibration_window_s"] = win
    return ov


def grid():
    DEV.mkdir(parents=True, exist_ok=True)
    cfgs = grid_configs()
    assert len(cfgs) <= 36
    reg = {"status": "registered before evaluation", "max_configurations": 36, "configurations": cfgs,
           "historical_fixed_transform": HISTORICAL, "suite": "configs/v4/suites/development.jsonl",
           "suite_sha256": v4.sha256(SUITES / "development.jsonl"), "selection_strata": list(v4.VALIDATION),
           "rule": __doc__.split("Selection rule")[1].strip(),
           "constant_search": {"x_m": CONSTANTS_X, "y_m": [0.0], "z_m": CONSTANTS_Z, "bound_m": 0.02,
                               "applied_to": "the selected common geometric parent", "count": len(CONSTANTS_X) * len(CONSTANTS_Z)}}
    (DEV / "baseline_grid.json").write_text(json.dumps(reg, indent=1) + "\n")
    groups = {}
    for c in cfgs:
        giver = REFERENCES[c["reference"]][0]
        groups.setdefault((c["ema_alpha"], giver), []).append(c)
    md = DEV / "matrices"
    md.mkdir(exist_ok=True)
    for (a, giver), cs in groups.items():
        name = f"{tag(a)}_giver{int(giver)}"
        ents = [{"id": c["id"], "method": c["method"], **({"overrides": entry_overrides(c)} if entry_overrides(c) else {}),
                 "trace": True} for c in cs]
        mx = {"name": f"v4_dev_{name}", "suite": "configs/v4/suites/development.jsonl", "num_envs": 288,
              "protocol": "configs/v2/protocol.json", "base_overrides": base_overrides(a, giver), "trace_cases": TRACE_DEV,
              "entries": ents}
        (md / f"{name}.json").write_text(json.dumps(mx, indent=1) + "\n")
        print(name, len(ents))


def load_records(runs: Path, entry: str) -> list[dict]:
    hits = list(runs.glob(f"**/{entry}.jsonl"))
    if len(hits) != 1:
        raise SystemExit(f"{entry}: expected one record file, found {len(hits)}")
    return [json.loads(l) for l in hits[0].read_text().splitlines() if l.strip()]


def score(rows: list[dict], magnitude) -> dict:
    by = {}
    for r in rows:
        if r["condition"] in v4.VALIDATION:
            by.setdefault(r["condition"], []).append(r)
    if sorted(by) != sorted(v4.VALIDATION) or any(len(v) != v4.SPLIT_COUNTS["development"] for v in by.values()):
        raise SystemExit("incomplete development strata")
    w = 1.0 / len(by)
    succ = sum(w * sum(r["success"] for r in v) / len(v) for v in by.values())
    unsafe = sum(w * sum(bool(r["collision"]) or r["terminal_reason"] == "drop" for r in v) / len(v) for v in by.values())
    times = [r["completion_time_s"] for v in by.values() for r in v if r["success"]]
    return {"success": succ, "unsafe": unsafe, "magnitude": magnitude(rows),
            "completion_time": sum(times) / len(times) if times else float("inf"),
            "invalid_resets": sum(not r["reset_valid"] for v in by.values() for r in v)}


def key(s: dict, cid: str):
    return (-round(s["success"], 12), round(s["unsafe"], 12), round(s["magnitude"], 12), round(s["completion_time"], 12), cid)


def align_mag(rows):
    vals = [sum(x * x for x in r["align_correction_mean_xyz_m"]) ** 0.5 for r in rows if r["condition"] in v4.VALIDATION]
    return sum(vals) / len(vals)


def select(runs: Path):
    reg = json.loads((DEV / "baseline_grid.json").read_text())
    cfgs = {c["id"]: c for c in reg["configurations"]}
    scores = {cid: score(load_records(runs, cid), align_mag) for cid in cfgs}
    geo = [c for c in cfgs if c != "nominal"]

    def best(ids):
        return min(ids, key=lambda c: key(scores[c], c))

    roles = {"nominal": "nominal", "geometry_fixed": reg["historical_fixed_transform"],
             "geometry_ema": best([c for c in geo if cfgs[c]["reference"] == "none"]),
             "geometry_calibrated": best([c for c in geo if cfgs[c]["reference"].startswith("cal")]),
             "common_parent": best(geo)}
    out = {"status": "selected on development data only", "rule": reg["rule"], "suite_sha256": reg["suite_sha256"],
           "scores": scores, "ranking": sorted(cfgs, key=lambda c: key(scores[c], c)),
           "roles": {r: {"candidate_id": c, **cfgs[c], **{f"selection_{k}": v for k, v in scores[c].items()}}
                     for r, c in roles.items()}}
    (DEV / "baseline_selection.json").write_text(json.dumps(out, indent=1) + "\n")
    for r, c in roles.items():
        s = scores[c]
        print(f"{r:20s} {c:22s} success={s['success']:.4f} unsafe={s['unsafe']:.4f} mag={s['magnitude'] * 1000:.2f}mm")


def constants(runs: Path):
    sel = json.loads((DEV / "baseline_selection.json").read_text())
    parent = sel["roles"]["common_parent"]
    cs = [(x, 0.0, z) for x in CONSTANTS_X for z in CONSTANTS_Z]
    ents = []
    for c in cs:
        cid = f"const_x{c[0] * 1000:+.0f}_z{c[2] * 1000:+.0f}"
        ov = entry_overrides(parent)
        if any(c):
            ov["constant_residual_m"] = list(c)
        ents.append({"id": cid, "method": "geometry", "overrides": ov})
    mx = {"name": "v4_dev_constant_search", "suite": "configs/v4/suites/development.jsonl", "num_envs": 288,
          "protocol": "configs/v2/protocol.json",
          "base_overrides": base_overrides(parent["ema_alpha"], REFERENCES[parent["reference"]][0]),
          "parent": parent["candidate_id"], "trace_cases": [], "entries": ents}
    (DEV / "matrices_constant").mkdir(exist_ok=True)
    (DEV / "matrices_constant/constant_search.json").write_text(json.dumps(mx, indent=1) + "\n")
    print(len(ents), "constant entries on parent", parent["candidate_id"])


def select_constant(runs: Path):
    selp = DEV / "baseline_selection.json"
    sel = json.loads(selp.read_text())
    mx = json.loads((DEV / "matrices_constant/constant_search.json").read_text())
    scores = {}
    for e in mx["entries"]:
        c = e["overrides"].get("constant_residual_m", [0.0, 0.0, 0.0])
        scores[e["id"]] = score(load_records(runs, e["id"]), lambda rows, c=c: sum(x * x for x in c) ** 0.5)
        scores[e["id"]]["constant_m"] = c
    best = min(scores, key=lambda c: key(scores[c], c))
    parent = sel["roles"]["common_parent"]
    sel["constant_search"] = {"parent": parent["candidate_id"], "scores": scores,
                              "ranking": sorted(scores, key=lambda c: key(scores[c], c))}
    sel["roles"]["best_constant_geometry"] = {**{k: v for k, v in parent.items() if not k.startswith("selection_")},
                                              "candidate_id": f"{parent['candidate_id']}+{best}",
                                              "constant_residual_m": scores[best]["constant_m"],
                                              **{f"selection_{k}": v for k, v in scores[best].items() if k != "constant_m"}}
    selp.write_text(json.dumps(sel, indent=1) + "\n")
    print("best constant", best, scores[best])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["suites", "grid", "select", "constants", "select_constant"])
    ap.add_argument("--runs", default=None)
    a = ap.parse_args()
    if a.stage in ("suites", "grid"):
        {"suites": suites, "grid": grid}[a.stage]()
    else:
        {"select": select, "constants": constants, "select_constant": select_constant}[a.stage](Path(a.runs))
