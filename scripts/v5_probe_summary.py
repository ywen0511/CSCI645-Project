#!/usr/bin/env python3
"""Summarize the V5 slip feasibility probe (development only; CPU).

    python3 scripts/v5_probe_summary.py --runs runs/v5/probe --out results/v5/slip/probe/summary.json

Per mechanism candidate and slip target (pooled over onsets and base cases): scheduled / valid slips (realized
displacement within tolerance of the target in x and z), realized x/z, slip error, maximum regulated force,
minimum giver finger force while sliding, receiver contact before the nominal grasp time, drops, and terminal
reasons. Acceptance (V5_EXECUTION.md 3.2): a target is kept for a mechanism if >= 95% of its probe episodes
realize a valid slip and the mechanism causes no drop and no receiver contact before t_grasp at that target;
the no-slip control must be unchanged and the negative controls must not succeed.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics

ROUNDS = {"r1": ("mechanisms", ("M1", "M2", "M3"), ""), "r2": ("mechanisms_r2", ("M4", "M5", "M6"), "_r2")}
NEG = ("no_receiver", "giver_holds", "table_support")


def load(p: Path):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def target_of(cond: str) -> str:
    return cond.split("_on")[0]


def summarize(rows):
    by = defaultdict(list)
    for r in rows:
        by[target_of(r["condition"])].append(r)
    out = {}
    for t, rs in sorted(by.items()):
        act = [r for r in rs if r["slip_active"]]
        errs = [r["slip_error_m"] for r in act if r["slip_error_m"] is not None]
        real = [r["slip_realized_xyz_m"] for r in act if r["slip_realized_xyz_m"]]
        gmins = [r["giver_force_min_during_slip_n"] for r in act if r["giver_force_min_during_slip_n"] is not None]
        valid = sum(r["slip_valid"] is True for r in act)
        cell = {"episodes": len(rs), "slip_scheduled": len(act), "slip_valid": valid,
                "valid_fraction": valid / len(act) if act else None,
                "realized_x_mm_median": 1000 * statistics.median(x[0] for x in real) if real else None,
                "realized_z_mm_median": 1000 * statistics.median(x[2] for x in real) if real else None,
                "error_mm_median": 1000 * statistics.median(errs) if errs else None,
                "error_mm_max": 1000 * max(errs) if errs else None,
                "force_abs_max_n": max(r["slip_force_abs_max_n"] for r in rs),
                "giver_force_min_n": min(gmins) if gmins else None,
                "receiver_contact_before_grasp": sum(bool(r["receiver_contact_before_grasp"]) for r in rs),
                "drops": sum(r["terminal_reason"] == "drop" for r in rs),
                "terminal_reasons": dict(Counter(r["terminal_reason"] for r in rs))}
        if act:
            cell["accepted"] = (valid >= 0.95 * len(act) and cell["drops"] == 0
                                and cell["receiver_contact_before_grasp"] == 0)
        out[t] = cell
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    runs = Path(a.runs)
    res = {"scope": "development probe only (v5slipprobe cases); not a final result", "rounds": {}}
    for rnd, (mdir, mechs, tag) in ROUNDS.items():
        setup = json.loads(Path(f"configs/v5/slip/development/probe/probe_setup{tag}.json").read_text())
        r = {"mechanisms": setup["mechanisms"], "per_mechanism": {}, "negative_controls": {}}
        for m in mechs:
            rows = load(runs / mdir / f"calibrated_{m}.jsonl")
            src = {x["source_commit"] for x in rows}
            r["per_mechanism"][m] = {"source_commits": sorted(src), "targets": summarize(rows),
                                     "kept_targets": sorted(t for t, c in summarize(rows).items() if c.get("accepted"))}
            for ctl in NEG:
                neg = load(runs / f"neg_{ctl}{tag}" / f"calibrated_{m}.jsonl")
                r["negative_controls"].setdefault(ctl, {})[m] = {
                    "episodes": len(neg), "successes": sum(x["success"] for x in neg),
                    "terminal_reasons": dict(Counter(x["terminal_reason"] for x in neg))}
        res["rounds"][rnd] = r
    # no-slip equivalence (round 1): mechanism off (V4 configuration) vs on, same suite and layout
    eq = {}
    for e in ("geometry_calibrated", "nominal"):
        off = {x["case_id"]: x for x in load(runs / "noslip_off" / f"{e}.jsonl")}
        for tag in ("", "_r2"):
            on = {x["case_id"]: x for x in load(runs / f"noslip_on{tag}" / f"{e}.jsonl")}
            ta = json.loads((runs / "noslip_off/traces" / f"{e}.json").read_text())
            tb = json.loads((runs / f"noslip_on{tag}/traces" / f"{e}.json").read_text())
            samples = mism = 0
            for cid in ta:
                if len(ta[cid]) != len(tb[cid]):
                    mism += 1
                for ra, rb in zip(ta[cid], tb[cid]):
                    for k in ("obj_pos", "recv_tcp", "giver_tcp", "p_exec"):
                        samples += 1
                        mism += ra[k] != rb[k]
            eq[f"{e}{tag or '_r1'}"] = {
                "cases": len(off), "same_terminal_reasons": all(off[c]["terminal_reason"] == on[c]["terminal_reason"] for c in off),
                "off_config_hash": next(iter(off.values()))["config_hash"], "trace_position_samples": samples,
                "trace_position_mismatches": mism}
    res["noslip_equivalence"] = eq
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    for rnd, r in res["rounds"].items():
        for m, v in r["per_mechanism"].items():
            print(rnd, m, "kept", v["kept_targets"])
    print(json.dumps(eq, indent=1))


if __name__ == "__main__":
    main()
