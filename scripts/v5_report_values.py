#!/usr/bin/env python3
"""Generate results/v5/report_values.json: every measured number used by the V5 report and slides, with its
source file and field (CPU, standard library).

    python3 scripts/v5_report_values.py

Each value: {"value", "text", "source", "field"}. Markdown tables are generated here (keys "table.*"), never typed
by hand. Keys (selection):
  a.<A1|A2>[.ci95|.ci975|.decision]          Study A primary contrasts
  a.succ.<config>.<condition>                  Study A success %
  a.main.<condition>.<factor>                  Study A exploratory main effects
  b.<B1|B2>[.ci95|.ci975|.decision]          Study B primary contrasts
  b.succ.<method>.<baseline|selected|final>.<condition>, b.seeds.<...>   Study B success % (per seed)
  b.c.<contrast id>.<condition>               exploratory contrasts (95% CI)
  b.sel.<run>, b.rep.<entry>, b.regr.*, b.mech.*, b.dev.*, b.probe.*, b.pilot.*, comp.*
  a.ema.*, b.sens.<condition>.<B1|B2|kept>[.ci95|.ci975]   v5.0.1 additions (EMA identity; post hoc sensitivity)
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V: dict = {}


def put(k, value, text, source, field):
    if k in V:
        raise SystemExit(f"duplicate key {k}")
    V[k] = {"value": value, "text": text, "source": source, "field": field}


def pp(x):
    return f"{x:+.1f}".replace("-", "−")


def ci(c):
    return f"[{pp(c[0])}, {pp(c[1])}]"


def load(rel):
    return json.loads((ROOT / rel).read_text())


def table(header, rows):
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(r) + " |" for r in rows])


NICE = {"nominal": "nominal", "geometry_fixed": "fixed-transform geometry", "geometry_ema": "EMA geometry",
        "geometry_calibrated": "one-shot calibrated geometry (parent)", "best_constant_geometry": "calibrated + constant",
        "geometry_tracking": "tracking geometry (= geometry_best)", "geometry_best": "geometry_best",
        "slip_robust_ff": "learned feed-forward", "slip_robust_history": "learned 4-frame history",
        "slip_robust_repeat": "learned repeated current frame"}


def study_a():
    src = "results/v5/calibration/summary.json"
    S = load(src)
    for p in S["primary"]:
        k = f"a.{p['id']}"
        put(k, p["difference_pp"], f"{pp(p['difference_pp'])} pp", src, f"primary[{p['id']}].difference_pp")
        put(k + ".ci95", p["ci95"], ci(p["ci95"]), src, f"primary[{p['id']}].ci95")
        put(k + ".ci975", p["ci97.5"], ci(p["ci97.5"]), src, f"primary[{p['id']}].ci97.5")
        put(k + ".decision", p["supports_calibration_only_improvement"],
            "supported" if p["supports_calibration_only_improvement"] else "not established", src,
            f"primary[{p['id']}].supports_calibration_only_improvement")
    for c in S["cells"]:
        put(f"a.succ.{c['config']}.{c['condition']}", c["success_pct"], f"{c['success_pct']:.1f}", src,
            f"cells[{c['config']},{c['condition']}].success_pct")
    for m in S["secondary_exploratory"]["main_effects"]:
        k = f"a.main.{m['condition']}.{m['factor']}"
        put(k, [m["difference_pp"], *m["ci95"]], f"{pp(m['difference_pp'])} pp {ci(m['ci95'])}", src, f"main_effects[{m['condition']},{m['factor']}]")
    for r in S["repeatability"]:
        put(f"a.rep.{r['config']}", r["matching_terminal_outcomes"], f"{r['matching_terminal_outcomes']:,}/{r['cases']:,}", src,
            f"repeatability[{r['config']}]")
    conds = ["clean", "grasp_10mm", "grasp_15mm", "mixed_id", "mixed_ood", "boundary_x_minus_7"]
    cfgs = list(dict.fromkeys(c["config"] for c in S["cells"]))
    cell = {(c["config"], c["condition"]): c["success_pct"] for c in S["cells"]}
    rows = []
    for k in cfgs:
        ema, ref, b = k.split("_")
        rows.append([f"`{k}`", "calibrated 0.5 s" if ref == "cal050" else "fixed", "0.2" if ema == "ema0p2" else "1.0",
                     f"{b[1:]} mm"] + [f"{cell[(k, c)]:.1f}" for c in conds])
    put("table.a.cells", None, table(["Configuration", "Reference", "EMA α", "Bound"] + [c.replace("_", " ") for c in conds], rows),
        src, "cells")
    t = load("results/v5/calibration/taxonomy/taxonomy.json")
    tx = {(c["entry"], c["condition"]): c for c in t["cells"]}
    rows = []
    for k in ("ema0p2_fixed_a25", "ema0p2_cal050_a25"):
        for c in ("mixed_id", "grasp_15mm"):
            x = tx[(k, c)]
            p = x["terminal_reason_pct"]
            rows.append([f"`{k}`", c.replace("_", " "), f"{p['success']:.1f}", f"{p['prohibited_collision']:.1f}",
                         f"{p['invalid_reset']:.1f}", f"{x['misaligned_at_grasp_pct']:.1f}"])
    put("table.a.taxonomy", None, table(["Configuration", "Condition", "Success", "Collision", "Invalid reset",
                                         "Misaligned at grasp"], rows), "results/v5/calibration/taxonomy/taxonomy.json", "cells")


def study_b():
    src = "results/v5/slip/analysis/summary.json"
    if not (ROOT / src).exists():
        return
    S = load(src)
    for p in S["primary"]:
        k = f"b.{p['id']}"
        put(k, p["difference_pp"], f"{pp(p['difference_pp'])} pp", src, f"primary[{p['id']}].difference_pp")
        put(k + ".ci95", p["ci95"], ci(p["ci95"]), src, f"primary[{p['id']}].ci95")
        put(k + ".ci975", p["ci97.5"], ci(p["ci97.5"]), src, f"primary[{p['id']}].ci97.5")
        put(k + ".decision", p["superiority_established"], "established" if p["superiority_established"] else "not established",
            src, f"primary[{p['id']}].superiority_established")
    conds = list(dict.fromkeys(c["condition"] for c in S["cells"]))
    for c in S["cells"]:
        k = f"b.succ.{c['method']}.{c['checkpoints']}.{c['condition']}"
        put(k, c["success_pct"], f"{c['success_pct']:.1f}", src, f"cells[{c['method']},{c['checkpoints']},{c['condition']}].success_pct")
        if len(c["per_seed_success_pct"]) > 1:
            put(k.replace("b.succ.", "b.seeds."), c["per_seed_success_pct"], " / ".join(f"{x:.1f}" for x in c["per_seed_success_pct"]),
                src, f"cells[...].per_seed_success_pct")
    for c in S["secondary_exploratory"]["contrasts"]:
        k = f"b.c.{c['id']}.{c['condition']}" + (f".{c['left'].split(':')[0]}" if c["id"] == "final_minus_selected" else "")
        put(k, [c["difference_pp"], *c["ci95"]], f"{pp(c['difference_pp'])} pp {ci(c['ci95'])}", src, f"contrasts[{c['id']},{c['condition']}]")
    for r in S["repeatability"]:
        put(f"b.rep.{r['entry']}", r["matching_terminal_outcomes"], f"{r['matching_terminal_outcomes']:,}/{r['cases']:,}", src,
            f"repeatability[{r['entry']}]")
    by = {(c["method"], c["checkpoints"], c["condition"]): c for c in S["cells"]}
    rows = []
    order = [("nominal", "baseline"), ("geometry_fixed", "baseline"), ("geometry_ema", "baseline"),
             ("geometry_calibrated", "baseline"), ("best_constant_geometry", "baseline"), ("geometry_tracking", "baseline"),
             ("slip_robust_ff", "selected"), ("slip_robust_history", "selected"), ("slip_robust_repeat", "selected"),
             ("slip_robust_ff", "final"), ("slip_robust_history", "final"), ("slip_robust_repeat", "final")]
    for m, k in order:
        rows.append([NICE[m] + ("" if k == "baseline" else f" ({k})")] + [f"{by[(m, k, c)]['success_pct']:.1f}" for c in conds])
    put("table.b.cells", None, table(["Method"] + [c.replace("_", " ") for c in conds], rows), src, "cells")
    rows = []
    pc = S["primary"][0]["condition"]
    tx = {(t["method"], t["checkpoints"], t["condition"]): t for t in S["taxonomy"]}
    for m, k in order[:9]:
        t = tx[(m, k, pc)]
        p = t["terminal_reason_pct"]
        f = t["flags_among_failed_counts"]
        s = t.get("slip", {})
        rows.append([NICE[m], f"{p['success']:.1f}", f"{p['prohibited_collision']:.1f}", f"{p['drop']:.1f}",
                     f"{p['release_timeout'] + p['episode_timeout']:.1f}", f"{p['invalid_reset']:.1f}", f"{p['invalid_slip']:.1f}",
                     f"{t['misaligned_at_grasp_pct']:.1f}", f"{s.get('receiver_contact_before_grasp', 0)}"])
    put("table.b.taxonomy", None, table(["Method", "Success", "Collision", "Drop", "Timeout", "Invalid reset", "Invalid slip",
                                         "Misaligned at grasp", "Receiver contact before grasp (episodes)"], rows), src,
        f"taxonomy[*,{pc}]")
    rows = [[f"`{r['entry']}`", f"{r['matching_terminal_outcomes']:,}/{r['cases']:,}"] for r in S["repeatability"]]
    put("table.b.repeat", None, table(["Entry", "Matching terminal outcomes"], rows), src, "repeatability")
    rg = S.get("regression_exploratory")
    if rg:
        rc = {(c["method"], c["condition"]): c for c in rg["cells"]}
        rconds = list(dict.fromkeys(c["condition"] for c in rg["cells"]))
        rows = []
        for m in ("slip_robust_ff", "slip_robust_history", "slip_robust_repeat"):
            rows.append([NICE[m] + " (V5, slip-trained)"] + [f"{rc[(m, c)]['success_pct']:.1f}" for c in rconds])
            rows.append([NICE[m].replace("learned", "V4") + " (V4 published)"] + [f"{rc[(m, c)]['v4_selected_success_pct']:.1f}" for c in rconds])
        put("table.b.regression", None, table(["Policy (selected)"] + [c.replace("_", " ") for c in rconds], rows), src, "regression_exploratory")
        for c in rg["contrasts"]:
            put(f"b.regr.{c['left']}.{c['condition']}", [c["difference_pp"], *c["ci95"]], f"{pp(c['difference_pp'])} pp {ci(c['ci95'])}",
                src, f"regression[{c['left']},{c['condition']}]")
    mech = S.get("mechanisms")
    if mech:
        put("b.mech.parent", mech["parent_zero_residual_successes"], f"{mech['parent_zero_residual_successes']}/{mech['cases']}", src,
            "mechanisms.parent_zero_residual_successes")
        rows = []
        for run, r in mech["runs"].items():
            rows.append([f"`{run}`"] + [f"{r[k]['successes']}/{mech['cases']} ({r[k]['outcome_agreement_with_selected']})"
                                        for k in ("selected", "reversed", "current_only", "constant")])
            for k in ("selected", "reversed", "current_only", "constant"):
                put(f"b.mech.{run}.{k}", r[k]["successes"], f"{r[k]['successes']}/{mech['cases']}", src, f"mechanisms.runs[{run}].{k}")
        put("table.b.mech", None, table(["Selected history run", "Selected", "History reversed", "Current frame repeated",
                                         "Development-fitted constant"], rows), src, "mechanisms")
    sel = load("results/v5/slip/selection/selection.json")
    rows = []
    for run, s in sorted(sel.items()):
        put(f"b.sel.{run}", s["selected"], s["selected"].replace("step_", "").lstrip("0") + " transitions", "results/v5/slip/selection/selection.json", run)
        rows.append([f"`{run}`", f"{int(s['selected'].split('_')[1]):,}", f"{100 * s['success_rate']:.1f}"])
    put("table.b.selection", None, table(["Run", "Selected checkpoint (transitions)", "Validation success (%)"], rows),
        "results/v5/slip/selection/selection.json", "*")


def development():
    src = "configs/v5/slip/development/baseline_selection.json"
    S = load(src)
    rows = []
    for cid in S["ranking"][:14]:
        s = S["scores"][cid]
        rows.append([f"`{cid}`", f"{100 * s['success']:.1f}", f"{100 * s['unsafe']:.1f}", f"{1000 * s['magnitude']:.1f}",
                     f"{1000 * s['total_correction']:.1f}"] + [f"{100 * v:.1f}" for v in s["per_condition_success"].values()])
        put(f"b.dev.{cid}", s["success"], f"{100 * s['success']:.1f}", src, f"scores[{cid}].success")
    conds = list(next(iter(S["scores"].values()))["per_condition_success"])
    put("table.b.dev", None, table(["Candidate (development)", "Strata success", "Unsafe", "Family magnitude (mm)",
                                    "Total correction (mm)"] + [c.replace("_", " ") for c in conds], rows), src, "ranking/scores")
    for r, x in S["roles"].items():
        put(f"b.role.{r}", x["candidate_id"], f"`{x['candidate_id']}`", src, f"roles[{r}].candidate_id")
    P = load("results/v5/slip/probe/summary.json")
    m6 = P["rounds"]["r2"]["per_mechanism"]["M6"]["targets"]
    rows = [[t.replace("x", "") + " mm", f"{c['slip_valid']}/{c['slip_scheduled']}", f"{c['error_mm_median']:.2f}",
             f"{c['realized_z_mm_median']:+.2f}", f"{c['force_abs_max_n']:.0f}", "yes" if c.get("accepted") else "no"]
            for t, c in sorted(m6.items(), key=lambda kv: float(kv[0][1:]) if kv[0] != "noslip" else -99) if t != "noslip"]
    put("table.b.probe", None, table(["Slide target", "Valid slips", "Median error (mm)", "Median vertical drift (mm)",
                                      "Peak force (N)", "Probe acceptance (start 0)"], rows), "results/v5/slip/probe/summary.json", "rounds.r2.M6")
    for name in ("summary_r2",):
        pl = load(f"results/v5/slip/pilot/{name}.json")["pilots"]
        for run, p in pl.items():
            put(f"b.pilot.{run}.first", p["first10"]["train_success_rate"], f"{100 * p['first10']['train_success_rate']:.1f}",
                f"results/v5/slip/pilot/{name}.json", f"pilots[{run}].first10.train_success_rate")
            put(f"b.pilot.{run}.last", p["last10"]["train_success_rate"], f"{100 * p['last10']['train_success_rate']:.1f}",
                f"results/v5/slip/pilot/{name}.json", f"pilots[{run}].last10.train_success_rate")


def addenda():
    """v5.0.1 additions (CPU, after v5.0.0): EMA field-by-field identity and the post hoc invalid-slip sensitivity."""
    src = "results/v5/calibration/ema_identity/summary.json"
    E = load(src)
    if not E["all_record_fields_identical_except_identifiers"] or E["trace_fields_outside_estimator_differing"]:
        raise SystemExit("EMA identity no longer holds; rewrite the report text")
    put("a.ema.pairs", E["paired_episodes"], f"{E['paired_episodes']:,}", src, "paired_episodes")
    tr = [t for p in E["pairs"] for t in p["traces"].values()]
    if len({json.dumps(t, sort_keys=True) for t in tr}) != 1:
        raise SystemExit("EMA trace comparison differs between pairs")
    t = tr[0]
    put("a.ema.trace.samples", t["samples"], str(t["samples"]), src, "pairs[*].traces[*].samples")
    for k in ("settling", "after_giver_release"):
        put(f"a.ema.trace.{k}", t["controller_estimate_differs_by_phase"][k], str(t["controller_estimate_differs_by_phase"][k]),
            src, f"pairs[*].traces[*].controller_estimate_differs_by_phase.{k}")
    put("a.ema.trace.pexec", E["trace_executed_command_differences"], str(E["trace_executed_command_differences"]), src,
        "trace_executed_command_differences")
    src = "results/v5/slip/sensitivity/summary.json"
    S = load(src)
    for r in S["conditions"]:
        put(f"b.sens.{r['condition']}.kept", r["kept_base_cases"], f"{r['kept_base_cases']}/{r['base_cases']}", src,
            f"conditions[{r['condition']}].kept_base_cases")
        for c in r["contrasts"]:
            s = c["valid_slip_cases"]
            k = f"b.sens.{r['condition']}.{c['id']}"
            put(k, s["difference_pp"], f"{pp(s['difference_pp'])} pp", src, f"conditions[{r['condition']}].{c['id']}.difference_pp")
            put(k + ".ci95", s["ci95"], ci(s["ci95"]), src, f"conditions[{r['condition']}].{c['id']}.ci95")
            put(k + ".ci975", s["ci97.5"], ci(s["ci97.5"]), src, f"conditions[{r['condition']}].{c['id']}.ci97.5")


def compute():
    src = "results/v5/compute.json"
    if not (ROOT / src).exists():
        return
    C = load(src)
    put("comp.total", C["total_gpu_hours"], f"{C['total_gpu_hours']:.2f}", src, "total_gpu_hours")
    rows = [[k.replace("_", " "), str(v["jobs"]), f"{v['gpu_hours']:.2f}", str(v["failed_or_killed_jobs"])] for k, v in C["by_stage"].items()]
    put("table.comp", None, table(["Stage", "Jobs", "GPU-hours", "Failed/killed jobs"], rows), src, "by_stage")


def main():
    study_a()
    study_b()
    development()
    addenda()
    compute()
    out = ROOT / "results/v5/report_values.json"
    out.write_text(json.dumps(V, indent=1, ensure_ascii=False) + "\n")
    print(len(V), "values")


if __name__ == "__main__":
    main()
