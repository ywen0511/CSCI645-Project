#!/usr/bin/env python3
"""Select the v3 deterministic baselines from the development matrices (CPU, standard library).

    python3 scripts/v3_select_baselines.py --dev <runs>/development --output configs/v3/baseline_selection.json

Scoring uses only the six validation-like development strata (clean, physical_only, bias_5mm, noise_2mm,
delay_2step, mixed_id), equally weighted (24 cases each), all scheduled cases as the denominator. Ranking key:
success rate desc, collision rate asc, |constant x| asc, EMA alpha desc, alignment bound asc, giver-reference
off before on, candidate ID. Roles:
  geometry_common        best zero-constant candidate over all estimators and both bounds
  geometry_best_constant best candidate over the full grid (all constants)
  geometry_raw           fixed: EMA alpha 1, giver-reference off, 1.5 cm, zero constant
  geometry_filtered      best zero-constant candidate with EMA filtering (alpha < 1) and giver-reference off
  geometry_giver         best zero-constant candidate with giver-reference on
  nominal                original script (no geometry, no residual; estimator-independent, run once)
Every candidate's counts (all 13 development conditions, plus the selection strata) are stored.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STRATA = ["clean", "physical_only", "bias_5mm", "noise_2mm", "delay_2step", "mixed_id"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dev", required=True)
    ap.add_argument("--output", default=str(ROOT / "configs/v3/baseline_selection.json"))
    a = ap.parse_args()
    dev = Path(a.dev)
    suite = [json.loads(l) for l in (ROOT / "configs/v3/suites/development.jsonl").read_text().splitlines() if l.strip()]
    ids = {c["case_id"] for c in suite}
    cands = []
    for mp in sorted((ROOT / "configs/v3/matrices/development").glob("*.json")):
        mx = json.loads(mp.read_text())
        alpha = mx["base_overrides"]["observation_sensor"]["ema_alpha"]
        giver = bool(mx["base_overrides"]["observation_giver_reference"])
        for e in mx["entries"]:
            src = mp.stem if e["id"] != "nominal" else "ema1p0_giver0"
            f = dev / src / e["id"] / f"{e['id']}.jsonl"
            rows = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
            got = [r["case_id"] for r in rows]
            if set(got) != ids or len(got) != len(ids):
                raise SystemExit(f"{f}: incomplete or duplicate development records ({len(got)}/{len(ids)})")
            by = {}
            for r in rows:
                by.setdefault(r["condition"], []).append(r)
            per = {c: {"n": len(v), "success": sum(r["success"] for r in v), "collision": sum(r["collision"] for r in v),
                       "drop": sum(r["drop"] for r in v),
                       "release_timeout": sum(r["terminal_reason"] == "release_timeout" for r in v),
                       "episode_timeout": sum(r["terminal_reason"] == "episode_timeout" for r in v),
                       "invalid_reset": sum(not r["reset_valid"] for r in v)} for c, v in sorted(by.items())}
            sel = [per[c] for c in STRATA]
            succ = sum(p["success"] / p["n"] for p in sel) / len(sel)
            coll = sum(p["collision"] / p["n"] for p in sel) / len(sel)
            ov = e.get("overrides", {})
            x = (ov.get("constant_residual_m") or [0.0])[0]
            cands.append({"candidate_id": f"{mp.stem}/{e['id']}" if e["id"] != "nominal" else "nominal",
                          "method": e["method"], "ema_alpha": alpha if e["method"] != "nominal" else None,
                          "giver_reference": giver if e["method"] != "nominal" else None,
                          "align_max_m": ov.get("align_max"), "constant_x_m": x if e["method"] != "nominal" else None,
                          "selection_success_rate": succ, "selection_collision_rate": coll, "per_condition": per,
                          "records": f"development/{src}/{e['id']}/{e['id']}.jsonl", "records_sha256": sha(f),
                          "source_commit": rows[0].get("source_commit"), "config_hash": rows[0].get("config_hash"),
                          "controller_hash": rows[0].get("controller_hash"),
                          "aliases": [f"{mp.stem}/nominal" for mp in sorted((ROOT / "configs/v3/matrices/development").glob("*.json"))]
                          if e["id"] == "nominal" else []})
    seen, uniq = set(), []
    for c in cands:
        if c["candidate_id"] not in seen:
            seen.add(c["candidate_id"])
            uniq.append(c)
    cands = uniq
    geo = [c for c in cands if c["method"] == "geometry"]

    def key(c):
        return (-c["selection_success_rate"], c["selection_collision_rate"], abs(c["constant_x_m"]), -c["ema_alpha"],
                c["align_max_m"], c["giver_reference"], c["candidate_id"])

    def best(pool, role):
        pool = sorted(pool, key=key)
        if not pool:
            raise SystemExit(f"no candidates for {role}")
        return pool[0]

    zero = [c for c in geo if c["constant_x_m"] == 0.0]
    roles = {
        "geometry_common": best(zero, "geometry_common"),
        "geometry_best_constant": best(geo, "geometry_best_constant"),
        "geometry_raw": best([c for c in zero if c["ema_alpha"] == 1.0 and not c["giver_reference"] and c["align_max_m"] == 0.015], "raw"),
        "geometry_filtered": best([c for c in zero if c["ema_alpha"] < 1.0 and not c["giver_reference"]], "filtered"),
        "geometry_giver": best([c for c in zero if c["giver_reference"]], "giver"),
        "nominal": next(c for c in cands if c["method"] == "nominal"),
    }
    grid_edges = {"constant_x_m": [-0.01, 0.02], "align_max_m": [0.015, 0.02], "ema_alpha": [0.2, 1.0]}
    sel = {}
    for role, c in roles.items():
        s = {"candidate_id": c["candidate_id"], "method": c["method"], "ema_alpha": c["ema_alpha"],
             "giver_reference": c["giver_reference"], "align_max_m": c["align_max_m"], "constant_x_m": c["constant_x_m"],
             "selection_success_rate": c["selection_success_rate"], "selection_collision_rate": c["selection_collision_rate"]}
        s["at_grid_edge"] = [k for k, edge in grid_edges.items() if c.get(k) is not None and c.get(k) in edge]
        sel[role] = s
    aliases = {}
    for r1 in sel:
        for r2 in sel:
            if r1 < r2 and sel[r1]["candidate_id"] == sel[r2]["candidate_id"]:
                aliases.setdefault(r1, []).append(r2)
    out = {"status": "selected on development data only", "selection_strata": STRATA, "weights": "equal (24 cases each)",
           "rule": __doc__.split("Roles:")[0].strip(), "development_suite_sha256": sha(ROOT / "configs/v3/suites/development.jsonl"),
           "roles": sel, "role_aliases": aliases,
           "note": "geometry_filtered is chosen among EMA alpha in {0.5, 0.2} (alpha 1 is no filter; it is geometry_raw "
                   "when the bound is 1.5 cm). The 2 cm bound and the +-2 cm constants share PPO's action scale; the best "
                   "grid point is not a global optimum. Grid-edge selections are flagged in at_grid_edge.",
           "candidates": cands}
    Path(a.output).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({r: {k: v for k, v in s.items() if k in ("candidate_id", "selection_success_rate", "at_grid_edge")}
                      for r, s in sel.items()}, indent=1))


if __name__ == "__main__":
    main()
