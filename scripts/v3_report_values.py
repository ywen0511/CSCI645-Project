#!/usr/bin/env python3
"""Generate results/v3/report_values.json: every number used by the report/slides, with its source (CPU).

    python3 scripts/v3_report_values.py

Each value: {"value": <raw>, "text": <formatted>, "source": "<file>", "field": "<selector>"}.
Sources: results/v3/summary/{family_condition_summary.json, paired_effects.json, reconciliation.json},
results/v3/selection/selection.json, configs/v3/baseline_selection.json, results/v3/{repeatability,interventions,
mechanisms,pilot}/..., results/v3/acceptance.json, results/v3/compute.json. Markdown tables are generated too
(key prefix "table."), so table cells are never typed by hand.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
V3 = ROOT / "results/v3"
FAMS = ["combined_clean_ff", "combined_robust_ff", "combined_robust_history", "residual_robust_history", "combined_robust_repeat"]
BASE = ["nominal", "geometry_raw", "geometry_filtered", "geometry_common", "geometry_best_constant", "geometry_giver"]
CONDS = ["clean", "physical_only", "bias_2mm", "bias_5mm", "bias_10mm", "noise_1mm", "noise_2mm", "noise_4mm",
         "delay_1step", "delay_2step", "delay_4step", "mixed_id", "mixed_ood"]
NICE = {"combined_clean_ff": "combined, clean-trained FF", "combined_robust_ff": "combined, robust FF",
        "combined_robust_history": "combined, robust history", "residual_robust_history": "residual-only, robust history",
        "combined_robust_repeat": "combined, robust repeated-current", "nominal": "nominal script",
        "geometry_raw": "geometry, raw estimate", "geometry_filtered": "geometry, EMA-filtered",
        "geometry_common": "geometry_common (giver reference)", "geometry_best_constant": "geometry_best_constant",
        "geometry_giver": "geometry_giver"}


def pp(x):
    return f"{x:+.1f}".replace("-", "−")


def main():
    V = {}

    def put(k, value, text, source, field):
        V[k] = {"value": value, "text": text, "source": source, "field": field}

    fs = json.loads((V3 / "summary/family_condition_summary.json").read_text())
    src = "results/v3/summary/family_condition_summary.json"
    S = {(r["family"], r["role"], r["condition"]): r for r in fs}
    for (f, role, c), r in S.items():
        put(f"succ.{f}.{role}.{c}", r["success_rate_mean"], f"{100 * r['success_rate_mean']:.1f}", src, f"{f}/{role}/{c}.success_rate_mean")
        if len(r["success_rate_per_seed"]) > 1:
            put(f"seeds.{f}.{role}.{c}", r["success_rate_per_seed"], " / ".join(f"{100 * x:.1f}" for x in r["success_rate_per_seed"]),
                src, f"{f}/{role}/{c}.success_rate_per_seed")
    E = json.loads((V3 / "summary/paired_effects.json").read_text())
    esrc = "results/v3/summary/paired_effects.json"
    for e in E:
        cs = e["conditions"][0] if len(e["conditions"]) == 1 else "nonclean"
        k = f"eff.{e['left']}-{e['right']}.{e['role']}.{cs}"
        put(k, [e["difference_pp"], e["ci_low_pp"], e["ci_high_pp"]],
            f"{pp(e['difference_pp'])} [{pp(e['ci_low_pp'])}, {pp(e['ci_high_pp'])}]", esrc, k)
        put(k + ".seeds", e["per_seed_difference_pp"], " / ".join(pp(x) for x in e["per_seed_difference_pp"]), esrc, k + ".per_seed")
        if e.get("familywise_95_interval"):
            fw = e["familywise_95_interval"]
            put(k + ".fw", [fw["ci_low_pp"], fw["ci_high_pp"]], f"[{pp(fw['ci_low_pp'])}, {pp(fw['ci_high_pp'])}]", esrc, k + ".familywise_95_interval")
    # main table: rows = baselines + families (selected), columns = conditions
    def row(f, role):
        cells = []
        for c in CONDS:
            r = S.get((f, role, c))
            cells.append(f"{100 * r['success_rate_mean']:.1f}" if r else "–")
        return cells
    hdr = "| controller | " + " | ".join(c.replace("_", " ") for c in CONDS) + " |"
    lines = [hdr, "|" + "---|" * (len(CONDS) + 1)]
    for b in BASE:
        alias = next((r["alias_of"] for (f, ro, c), r in S.items() if f == b and r.get("alias_of")), None)
        lines.append(f"| {NICE[b]}{' (= ' + alias + ')' if alias else ''} | " + " | ".join(row(b, "baseline")) + " |")
    for f in FAMS:
        lines.append(f"| {NICE[f]} (selected) | " + " | ".join(row(f, "selected")) + " |")
    for f in FAMS:
        lines.append(f"| {NICE[f]} (final) | " + " | ".join(row(f, "final")) + " |")
    put("table.main", None, "\n".join(lines), src, "success % per condition (mean over training seeds; 200 cases each)")
    # per-seed table on mixed_id / mixed_ood
    lines = ["| family | role | mixed_id per seed | mixed_ood per seed |", "|---|---|---|---|"]
    for f in FAMS:
        for role in ("selected", "final"):
            a, b = S[(f, role, "mixed_id")], S[(f, role, "mixed_ood")]
            lines.append(f"| {NICE[f]} | {role} | {' / '.join(f'{100 * x:.1f}' for x in a['success_rate_per_seed'])} | "
                         f"{' / '.join(f'{100 * x:.1f}' for x in b['success_rate_per_seed'])} |")
    put("table.seeds", None, "\n".join(lines), src, "per-seed success %")
    # effects table
    lines = ["| comparison | role | cases | difference [pp] (95% CI) | per seed [pp] |", "|---|---|---|---|---|"]
    for e in E:
        cs = e["conditions"][0] if len(e["conditions"]) == 1 else "12 non-clean conditions (equal weight)"
        fw = f"; 97.5%: [{pp(e['familywise_95_interval']['ci_low_pp'])}, {pp(e['familywise_95_interval']['ci_high_pp'])}]" if e.get("familywise_95_interval") else ""
        lines.append(f"| {'**' if e['primary'] else ''}{e['left']} − {e['right']}{'**' if e['primary'] else ''} | {e['role']} | {cs} | "
                     f"{pp(e['difference_pp'])} [{pp(e['ci_low_pp'])}, {pp(e['ci_high_pp'])}]{fw} | "
                     f"{' / '.join(pp(x) for x in e['per_seed_difference_pp'])} |")
    put("table.effects", None, "\n".join(lines), esrc, "all paired effects")
    # failure breakdown on mixed conditions (counts of 200, mean over seeds)
    lines = ["| controller | condition | success | drop | collision | release timeout | episode timeout |", "|---|---|---|---|---|---|---|"]
    for f, role in [(b, "baseline") for b in BASE[:4]] + [(f, "selected") for f in FAMS]:
        for c in ("mixed_id", "mixed_ood"):
            r = S[(f, role, c)]
            lines.append(f"| {NICE[f]} | {c} | {200 * r['success_rate_mean']:.1f} | {r['drop_mean']:.1f} | {r['collision_mean']:.1f} | "
                         f"{r['release_timeout_mean']:.1f} | {r['episode_timeout_mean']:.1f} |")
    put("table.failures", None, "\n".join(lines), src, "outcome counts of 200 (mean over seeds)")
    # baseline selection table
    B = json.loads((ROOT / "configs/v3/baseline_selection.json").read_text())
    lines = ["| role | candidate | EMA alpha | giver ref. | bound [cm] | constant x [mm] | selection success (144 dev cases) |",
             "|---|---|---|---|---|---|---|"]
    for role, s in B["roles"].items():
        lines.append(f"| {role} | {s['candidate_id']} | {s['ema_alpha'] if s['ema_alpha'] is not None else '–'} | "
                     f"{s['giver_reference'] if s['giver_reference'] is not None else '–'} | "
                     f"{100 * s['align_max_m'] if s['align_max_m'] else '–'} | {1000 * s['constant_x_m'] if s['constant_x_m'] is not None else '–'} | "
                     f"{100 * s['selection_success_rate']:.1f}% |")
    put("table.baselines", None, "\n".join(lines), "configs/v3/baseline_selection.json", "roles")
    # development estimator table (all 13 conditions, zero constant, 1.5 cm)
    C = {c["candidate_id"]: c for c in B["candidates"]}
    lines = ["| development candidate (1.5 cm, 0 mm) | " + " | ".join(c.replace("_", " ") for c in CONDS) + " |", "|" + "---|" * (len(CONDS) + 1)]
    for cid in ["nominal", "ema1p0_giver0/geom15_x+00", "ema0p5_giver0/geom15_x+00", "ema0p2_giver0/geom15_x+00",
                "ema1p0_giver1/geom15_x+00", "ema0p5_giver1/geom15_x+00", "ema0p2_giver1/geom15_x+00"]:
        pc = C[cid]["per_condition"]
        lines.append(f"| {cid} | " + " | ".join(f"{pc[c]['success']}" for c in CONDS) + " |")
    put("table.development", None, "\n".join(lines), "configs/v3/baseline_selection.json", "candidates[*].per_condition (successes of 24)")
    sel = json.loads((V3 / "selection/selection.json").read_text())
    lines = ["| run | selected checkpoint | validation success | collision rate |", "|---|---|---|---|"]
    for run, s in sorted(sel.items()):
        lines.append(f"| {run} | {s['selected']} | {100 * s['success_rate']:.1f}% | {100 * s['collision_rate']:.1f}% |")
    put("table.selection", None, "\n".join(lines), "results/v3/selection/selection.json", "per run")
    rec = json.loads((V3 / "summary/reconciliation.json").read_text())
    put("count.final_records", sum(r["recorded"] for r in rec), f"{sum(r['recorded'] for r in rec):,}", "results/v3/summary/reconciliation.json", "sum(recorded)")
    put("count.invalid", sum(r["invalid_resets"] for r in rec), str(sum(r["invalid_resets"] for r in rec)), "results/v3/summary/reconciliation.json", "sum(invalid_resets)")
    idx = json.loads((ROOT / "configs/v3/final_matrix_index.json").read_text())["declared_counts"]
    for k in ("logical_episodes", "executed_episodes", "logical_entries", "executed_entries"):
        put(f"count.{k}", idx[k], f"{idx[k]:,}", "configs/v3/final_matrix_index.json", f"declared_counts.{k}")
    for name in ("repeatability/repeatability.json", "interventions/interventions.json", "mechanisms/mechanisms.json", "compute.json"):
        p = V3 / name
        if p.exists():
            put(f"file.{name}", None, name, f"results/v3/{name}", "(see file)")
    if (V3 / "repeatability/repeatability.json").exists():
        Rp = json.loads((V3 / "repeatability/repeatability.json").read_text())
        for x in Rp["paired_effects"]:
            put(f"rep.eff.b{x['batch']}.{x['process']}", [x["difference_pp"], x["ci_low_pp"], x["ci_high_pp"]],
                f"{pp(x['difference_pp'])} [{pp(x['ci_low_pp'])}, {pp(x['ci_high_pp'])}]", "results/v3/repeatability/repeatability.json",
                f"paired_effects[batch={x['batch']},process={x['process']}]")
        lines = ["| entry | batch | process seed | success /65 | terminal = original | success = original |", "|---|---|---|---|---|---|"]
        for r in Rp["per_run"]:
            lines.append(f"| {r['entry']} | {r['batch']} | {r['process_seed']} | {r['success']} | {r['terminal_equal_original']} | {r['success_equal_original']} |")
        put("table.repeatability", None, "\n".join(lines), "results/v3/repeatability/repeatability.json", "per_run")
        tot = sum(r["terminal_equal_original"] for r in Rp["per_run"])
        n = len(Rp["per_run"]) * Rp["cases"]
        put("rep.terminal_equal", [tot, n], f"{tot:,} of {n:,}", "results/v3/repeatability/repeatability.json", "sum(per_run.terminal_equal_original)")
    if (V3 / "interventions/interventions.json").exists():
        I = json.loads((V3 / "interventions/interventions.json").read_text())
        lines = ["| policy | seed | unmodified /65 | frames permuted /65 | current frame only /65 |", "|---|---|---|---|---|"]
        for r in I["rows"]:
            lines.append(f"| {NICE[r['family']]} | {r['seed']} | {r['unmodified']} | {r['permuted']} | {r['current_only']} |")
        put("table.interventions", None, "\n".join(lines), "results/v3/interventions/interventions.json", "rows")
    if (V3 / "mechanisms/mechanisms.json").exists():
        M = json.loads((V3 / "mechanisms/mechanisms.json").read_text())
        lines = ["| family | seed | mean abs residual [mm] | max abs residual [mm] | align. saturation | x intercept [mm] | x slope on true offset | x slope on sensor bias | R² |",
                 "|---|---|---|---|---|---|---|---|---|"]
        fits = {(f["family"], f["seed"], f["axis"]): f for f in M["fits"]}
        for fam, rows in M["per_seed"].items():
            for r in rows:
                fx = fits[(fam, r["seed"], "x")]
                lines.append(f"| {NICE[fam]} | {r['seed']} | {r['residual_abs_mean_mm']:.2f} | {r['residual_abs_max_mm']:.2f} | "
                             f"{r['align_saturation_frac']:.3f} | {fx['intercept_mm']:+.2f} | {fx['slope_on_true_offset']:+.3f} | "
                             f"{fx['slope_on_sensor_bias']:+.3f} | {fx['r2']:.2f} |" if fx["r2"] is not None else
                             f"| {NICE[fam]} | {r['seed']} | {r['residual_abs_mean_mm']:.2f} | {r['residual_abs_max_mm']:.2f} | {r['align_saturation_frac']:.3f} | – | – | – | – |")
        put("table.mechanisms", None, "\n".join(lines), "results/v3/mechanisms/mechanisms.json", "per_seed + fits(axis x)")
    if (V3 / "compute.json").exists():
        Cm = json.loads((V3 / "compute.json").read_text())
        for k, v in Cm.items():
            if isinstance(v, (int, float)):
                put(f"compute.{k}", v, f"{v:,.1f}" if isinstance(v, float) else f"{v:,}", "results/v3/compute.json", k)
    (V3 / "report_values.json").write_text(json.dumps(V, indent=1, default=float) + "\n")
    print(f"{len(V)} values")


if __name__ == "__main__":
    main()
