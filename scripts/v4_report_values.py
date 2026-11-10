#!/usr/bin/env python3
"""Generate results/v4/report_values.json: every number used by the V4 report/slides, with its source (CPU).

    python3 scripts/v4_report_values.py

Each value: {"value", "text", "source", "field"}. Keys:
  succ.<family>.<role>.<condition>           mean success % (role baseline|selected|final)
  seeds.<family>.<role>.<condition>          per-seed success %
  eff.<left>-<right>.<role>.<condition|nonclean>   difference pp [95% CI]; .fw Bonferroni 97.5%; .seeds per seed
  sel.<run>                                  selected checkpoint tag;  val.<run>.<tag>  validation success %
  mech.*, rep.*, comp.*, acc.*, dev.*, pilot.*, table.*   (see main())
Markdown tables are generated here (prefix "table."), never typed by hand.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from csci645_handover import v4_protocol as v4  # noqa: E402

R4 = ROOT / "results/v4"
FAMS = ["combined_clean_ff", "combined_robust_ff", "combined_robust_history", "combined_robust_repeat", "residual_robust_history"]
BASE = ["nominal", "geometry_fixed", "geometry_ema", "geometry_calibrated", "best_constant_geometry"]
NICE = {"combined_clean_ff": "combined, clean-trained FF", "combined_robust_ff": "combined, robust FF",
        "combined_robust_history": "combined, robust history (4 frames)", "combined_robust_repeat": "combined, repeated current frame",
        "residual_robust_history": "residual-only, robust history", "nominal": "nominal trajectory",
        "geometry_fixed": "fixed-transform geometry (V3)", "geometry_ema": "EMA geometry (α 0.2)",
        "geometry_calibrated": "calibrated geometry (0.5 s)", "best_constant_geometry": "best constant on calibrated"}


def pp(x):
    return f"{x:+.1f}".replace("-", "−")


def pct(x):
    return f"{100 * x:.1f}"


def main():
    V = {}

    def put(k, value, text, source, field):
        V[k] = {"value": value, "text": text, "source": source, "field": field}

    src = "results/v4/summary/family_condition_summary.json"
    S = {(r["family"], r["role"], r["condition"]): r for r in json.loads((ROOT / src).read_text())}
    for (f, role, c), r in S.items():
        put(f"succ.{f}.{role}.{c}", r["success_rate_mean"], pct(r["success_rate_mean"]), src, f"{f}/{role}/{c}.success_rate_mean")
        if len(r["success_rate_per_seed"]) > 1:
            put(f"seeds.{f}.{role}.{c}", r["success_rate_per_seed"], " / ".join(pct(x) for x in r["success_rate_per_seed"]),
                src, f"{f}/{role}/{c}.success_rate_per_seed")
        for k in ("collision", "release_timeout", "drop", "episode_timeout"):
            key = {"collision": "prohibited_collision"}.get(k, k)
            put(f"term.{f}.{role}.{c}.{k}", r["terminal_mean"][key], f"{r['terminal_mean'][key]:.1f}", src,
                f"{f}/{role}/{c}.terminal_mean.{key}")
        if r.get("calibration_error_max_axis_mean_m") is not None:
            put(f"calerr.{f}.{role}.{c}", r["calibration_error_max_axis_mean_m"], f"{1000 * r['calibration_error_max_axis_mean_m']:.1f}",
                src, f"{f}/{role}/{c}.calibration_error_max_axis_mean_m")
        if r.get("residual_saturated_episode_frac") is not None and f in FAMS:
            put(f"sat.{f}.{role}.{c}", r["residual_saturated_episode_frac"], pct(r["residual_saturated_episode_frac"]), src,
                f"{f}/{role}/{c}.residual_saturated_episode_frac")
    esrc = "results/v4/summary/paired_effects.json"
    for e in json.loads((ROOT / esrc).read_text()):
        cs = e["conditions"][0] if len(e["conditions"]) == 1 else "nonclean"
        k = f"eff.{e['left']}-{e['right']}.{e['role']}.{cs}"
        put(k, [e["difference_pp"], e["ci_low_pp"], e["ci_high_pp"]],
            f"{pp(e['difference_pp'])} [{pp(e['ci_low_pp'])}, {pp(e['ci_high_pp'])}]", esrc, k)
        put(k + ".seeds", e["per_seed_difference_pp"], " / ".join(pp(x) for x in e["per_seed_difference_pp"]), esrc, k + ".per_seed")
        put(k + ".degenerate", e["degenerate"], "degenerate (both arms at the same bound)" if e["degenerate"] else "non-degenerate",
            esrc, k + ".degenerate")
        if e.get("bonferroni_97_5"):
            fw = e["bonferroni_97_5"]
            put(k + ".fw", [fw["ci_low_pp"], fw["ci_high_pp"]], f"[{pp(fw['ci_low_pp'])}, {pp(fw['ci_high_pp'])}]", esrc, k + ".bonferroni_97_5")
    rsrc = "results/v4/summary/reconciliation.json"
    tot = json.loads((ROOT / rsrc).read_text())["totals"]
    for k, v in tot.items():
        put(f"count.{k}", v, f"{v:,}", rsrc, f"totals.{k}")
    ssrc = "results/v4/selection/selection.json"
    sel = json.loads((ROOT / ssrc).read_text())
    tags = {}
    for run, s in sel.items():
        put(f"sel.{run}", s["selected"], s["selected"].replace("step_", "").lstrip("0") or "0", ssrc, f"{run}.selected")
        tags[s["selected"]] = tags.get(s["selected"], 0) + 1
        rep = json.loads((ROOT / f"results/v4/selection/{run}.json").read_text())
        for c in rep["candidates"] + [rep["untrained_control"]]:
            put(f"val.{run}.{c['tag']}", c["success_rate"], pct(c["success_rate"]), f"results/v4/selection/{run}.json",
                f"candidates[{c['tag']}].success_rate")
    put("sel.tag_counts", tags, ", ".join(f"{t.replace('step_', '').lstrip('0')}: {n}" for t, n in sorted(tags.items())), ssrc, "count of selected tags")
    msrc = "results/v4/mechanisms/mechanisms.json"
    if (ROOT / msrc).exists():
        M = json.loads((ROOT / msrc).read_text())
        for run, m in M["runs"].items():
            for x, n in m["success"].items():
                put(f"mech.{run}.{x}", n, str(n), msrc, f"runs.{run}.success.{x}")
            for x, a in m["agreement_with_selected"].items():
                put(f"mech.{run}.agree.{x}", a["agree"], f"{a['agree']}/{a['cases']}", msrc, f"runs.{run}.agreement_with_selected.{x}")
            put(f"mech.{run}.const", m["fitted_constant_m"], ", ".join(f"{1000 * x:+.1f}".replace("-", "−") for x in m["fitted_constant_m"]),
                msrc, f"runs.{run}.fitted_constant_m")
        for p, z in M["untrained_controls"].items():
            put(f"mech.zero.{p}", z["success"], str(z["success"]), msrc, f"untrained_controls.{p}.success")
            put(f"mech.zero.{p}.agree", z["agreement_with_parent"]["agree"], f"{z['agreement_with_parent']['agree']}/{z['agreement_with_parent']['cases']}",
                msrc, f"untrained_controls.{p}.agreement_with_parent")
        for k, n in M["parents"].items():
            put(f"mech.parent.{k}", n, str(n), msrc, f"parents.{k}")
    rpsrc = "results/v4/mechanisms/repeatability.json"
    if (ROOT / rpsrc).exists():
        RP = json.loads((ROOT / rpsrc).read_text())
        put("rep.episodes", RP["episodes"], f"{RP['episodes']:,}", rpsrc, "episodes")
        put("rep.agree", RP["agree_with_reference"], f"{RP['agree_with_reference']:,}", rpsrc, "agree_with_reference")
    csrc = "results/v4/compute.json"
    if (ROOT / csrc).exists():
        C = json.loads((ROOT / csrc).read_text())
        put("comp.total", C["total_gpu_hours"], f"{C['total_gpu_hours']:.1f}", csrc, "total_gpu_hours")
        for k, v in C["by_stage"].items():
            put(f"comp.{k}", v["gpu_hours"], f"{v['gpu_hours']:.1f}", csrc, f"by_stage.{k}.gpu_hours")
    asrc = "results/v4/acceptance/acceptance.json"
    A = json.loads((ROOT / asrc).read_text())
    a1 = A["A1_v3_path"]
    put("acc.A1", None, f"{a1['geometry_common']['agree']}/{a1['geometry_common']['cases']} + {a1['policy_s11_selected']['agree']}/{a1['policy_s11_selected']['cases']}", asrc, "A1_v3_path")
    a2 = A["A2_v4_zero_offset"]
    put("acc.A2", None, f"{a2['geometry_common']['agree']}/{a2['geometry_common']['cases']} + {a2['policy_s11_selected']['agree']}/{a2['policy_s11_selected']['cases']}", asrc, "A2_v4_zero_offset")
    a4 = A["A4_layout"]["vs_b72"]
    put("acc.A4", None, ", ".join(f"{v['agree']}/{v['cases']}" for v in a4.values()), asrc, "A4_layout.vs_b72.*.agree")
    put("acc.A4.cal", None, f"{1000 * max(v['max_calibration_diff_m'] for v in a4.values()):.2f}", asrc, "A4_layout.vs_b72.*.max_calibration_diff_m")
    a5 = A["A5_reset_leakage"]["batch16_vs_batch288"]
    put("acc.A5", None, f"{a5['agree']}/{a5['cases']}", asrc, "A5_reset_leakage.batch16_vs_batch288")
    put("acc.A5.cal", None, f"{1000 * a5['max_calibration_diff_m']:.2f}", asrc, "A5_reset_leakage.max_calibration_diff_m")
    a7 = A["A7_zero_residual_equals_parent"]["profiles"]
    put("acc.A7", None, ", ".join(f"{v['agree']}/{v['cases']}" for v in a7.values()) + " (five profiles)", asrc, "A7.profiles.*.agree")
    psrc = "results/v4/pilot/summary.json"
    PL = json.loads((ROOT / psrc).read_text())
    put("pilot.total", PL["total_training_transitions"], f"{PL['total_training_transitions']:,}", psrc, "total_training_transitions")
    # main table: baselines + learned selected + learned final, success % per condition
    hdr = "| controller | " + " | ".join(c.replace("boundary_", "").replace("_", " ") for c in v4.ORDER) + " |"
    lines = [hdr, "|" + "---|" * (len(v4.ORDER) + 1)]
    for b in BASE:
        alias = S[(b, "baseline", "clean")].get("alias_of")
        lines.append(f"| {NICE[b]}{' (= ' + NICE[alias] + ', exact alias)' if alias else ''} | "
                     + " | ".join(pct(S[(b, "baseline", c)]["success_rate_mean"]) for c in v4.ORDER) + " |")
    for role in ("selected", "final"):
        for f in FAMS:
            lines.append(f"| {NICE[f]} ({role}) | " + " | ".join(pct(S[(f, role, c)]["success_rate_mean"]) for c in v4.ORDER) + " |")
    put("table.main", None, "\n".join(lines), src, "success % per condition (learned: mean of 5 training seeds; 200 cases each)")
    lines = ["| family | role | mixed_id per seed (111/222/333/444/555) | grasp_15mm per seed | mixed_ood per seed |", "|---|---|---|---|---|"]
    for f in FAMS:
        for role in ("selected", "final"):
            lines.append(f"| {NICE[f]} | {role} | " + " | ".join(" / ".join(pct(x) for x in S[(f, role, c)]["success_rate_per_seed"])
                                                         for c in ("mixed_id", "grasp_15mm", "mixed_ood")) + " |")
    put("table.seeds", None, "\n".join(lines), src, "per-seed success %")
    lines = ["| condition | " + " | ".join(NICE[b] for b in BASE[:4]) + " |", "|---|" + "---|" * 4]
    for c in v4.ORDER:
        lines.append(f"| {c} | " + " | ".join(f"{S[(b, 'baseline', c)]['terminal_mean']['prohibited_collision']:.0f} / "
                                              f"{S[(b, 'baseline', c)]['terminal_mean']['release_timeout']:.0f}" for b in BASE[:4]) + " |")
    put("table.baseline_failures", None, "\n".join(lines), src, "collision / release-timeout counts of 200 per baseline")
    lines = ["| run | selected | validation success % (2M / 4M / 6M / 8M / 10M) | step 0 |", "|---|---|---|---|"]
    for run in sorted(sel):
        rep = json.loads((ROOT / f"results/v4/selection/{run}.json").read_text())
        cs = {c["tag"]: c["success_rate"] for c in rep["candidates"]}
        lines.append(f"| {run} | {sel[run]['selected'].replace('step_', '').lstrip('0')} | "
                     + " / ".join(pct(cs[t]) for t in sorted(cs)) + f" | {pct(rep['untrained_control']['success_rate'])} |")
    put("table.selection", None, "\n".join(lines), ssrc, "validation success per candidate")
    (R4 / "report_values.json").write_text(json.dumps(V, indent=1, ensure_ascii=False) + "\n")
    print(len(V), "values")


if __name__ == "__main__":
    main()
