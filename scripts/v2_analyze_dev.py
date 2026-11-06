#!/usr/bin/env python3
"""Stage 2/3 development analysis: residual diagnostics, constant-offset search, geometry ablations, bounds.

    python3 scripts/v2_analyze_dev.py --dev results/v2/raw/dev --output results/v2/dev_summary

--dev holds the eval_matrix outputs ``controls/``, ``learned/``, ``geometry/``. Writes ``summary.json``,
CSV tables, ``tables.md``, ``constants.json`` (selected development constants) and figures. numpy + matplotlib.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from csci645_handover import v2_analysis as va  # noqa: E402

DIAG = json.loads((ROOT / "configs/v2/diagnostics.json").read_text())
CONDS = ["clean", "position_in", "timing_early_in", "timing_late_in", "joint_early_in", "joint_late_in",
         "position_stress", "joint_early_stress", "joint_late_stress"]
GROUPS = {"non_stress": CONDS[:6], "stress": CONDS[6:], "all": CONDS}
SEEDS = (11, 22, 33)


def fmt_x(x):
    return f"{'+' if x >= 0 else '-'}{abs(round(x * 1000)):03d}mm"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dev", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--n-boot", type=int, default=10000)
    ap.add_argument("--no-figures", action="store_true")
    a = ap.parse_args()
    D, O = Path(a.dev), Path(a.output)
    O.mkdir(parents=True, exist_ok=True)
    rec = va.load_records(D / "controls", D / "learned", D / "geometry")
    suite = [json.loads(x) for x in (ROOT / DIAG["suite"]["path"]).read_text().splitlines() if x.strip()]
    ids_all = [c["case_id"] for c in suite]
    ids = {"all": ids_all, "stress": [c["case_id"] for c in suite if "stress" in c["condition"]],
           "non_stress": [c["case_id"] for c in suite if "stress" not in c["condition"]]}
    S: dict = {"suite_sha256": DIAG["suite"]["sha256"], "entries": {}, "problems": []}
    for k, rows in sorted(rec.items()):
        got = {r["case_id"] for r in rows}
        if got != set(ids_all):
            S["problems"].append(f"{k}: {len(got)} of {len(ids_all)} cases")
        if {r["suite_hash"] for r in rows} != {DIAG["suite"]["sha256"]}:
            S["problems"].append(f"{k}: suite hash mismatch")
        S["entries"][k] = va.summarize(rows, GROUPS)

    cs = DIAG["constant_offset_search"]
    zero_of = {"geometry_1cm": "geometry_zero", "nominal": "nominal", "geometry_1p5cm": "geom_bound_0p015"}
    const_entry = {}
    S["constant_search"] = {}
    for base, zid in zero_of.items():
        scores = []
        for x in cs["grid_x_m"]:
            eid = zid if x == 0.0 else f"const_{base}_x{fmt_x(x)}"
            if eid not in rec:
                continue
            rs = rec[eid]
            stress = [r for r in rs if "stress" in r["condition"]]
            scores.append({"x_m": x, "entry": eid, "reused_zero_entry": x == 0.0,
                           "success": sum(r["success"] for r in rs), "n": len(rs),
                           "collision_episodes": sum(r["collision"] for r in rs),
                           "drops": sum(r["drop"] for r in rs),
                           "success_stress": sum(r["success"] for r in stress), "n_stress": len(stress)})
        if not scores:
            continue
        sel = va.select_constant(scores)
        S["constant_search"][base] = {"scores": scores, "selected": sel}
        const_entry[base] = sel["entry"]
    (O / "constants.json").write_text(json.dumps(
        {b: {"x_m": v["selected"]["x_m"], "entry": v["selected"]["entry"], "rule": cs["selection_rule"]}
         for b, v in S["constant_search"].items()}, indent=1) + "\n")

    def ent(prefix):
        return [rec[f"{prefix}_s{s}"] for s in SEEDS if f"{prefix}_s{s}" in rec]

    comps = []
    plan = [
        ("combined_init - geometry_zero", ent("combined_init"), [rec.get("geometry_zero")]),
        ("combined_final - geometry_zero", ent("combined_final"), [rec.get("geometry_zero")]),
        ("combined_final - geometry_const", ent("combined_final"), [rec.get(const_entry.get("geometry_1cm"))]),
        ("combined_final - combined_init", ent("combined_final"), ent("combined_init")),
        ("geometry_const - geometry_zero", [rec.get(const_entry.get("geometry_1cm"))], [rec.get("geometry_zero")]),
        ("residual_init - nominal", ent("residual_init"), [rec.get("nominal")]),
        ("residual_final - nominal", ent("residual_final"), [rec.get("nominal")]),
        ("residual_final - nominal_const", ent("residual_final"), [rec.get(const_entry.get("nominal"))]),
        ("residual_final - residual_init", ent("residual_final"), ent("residual_init")),
        ("nominal_const - nominal", [rec.get(const_entry.get("nominal"))], [rec.get("nominal")]),
        ("combined_no_phase_final - combined_final [exploratory]", ent("combined_no_phase_final"), ent("combined_final")),
    ]
    for name, A, B in plan:
        if not A or not B or any(x is None for x in A + B):
            continue
        for g in ("all", "stress", "non_stress"):
            for metric in ("success", "collision"):
                r = va.paired(A, B, ids[g], key=metric, n_boot=a.n_boot)
                comps.append({"comparison": name, "cases": g, **{k: v for k, v in r.items() if k != "resampling"}})
    S["comparisons"] = comps
    va.write_csv(O / "comparisons.csv", comps)

    # residual behaviour of learned checkpoints
    beh = []
    for k, rows in sorted(rec.items()):
        if not rows[0].get("checkpoint_sha256"):
            continue
        valid = [r for r in rows if r["reset_valid"]]
        res = np.array([r["residual_mean_xyz_m"] for r in valid])
        off = np.array([r["requested_offset_xyz_m"] for r in valid])
        row = {"entry": k, "checkpoint_sha256": rows[0]["checkpoint_sha256"][:12],
               "transitions": rows[0].get("checkpoint_transitions"),
               "mean_signed_residual_xyz_mm": [float(v) * 1000 for v in res.mean(0)],
               "across_case_std_xyz_mm": [float(v) * 1000 for v in res.std(0)],
               "mean_abs_residual_mm": 1000 * float(np.mean([r["residual_abs_mean_m"] for r in valid])),
               "rms_residual_mm": 1000 * float(np.sqrt(np.mean([r["residual_sq_norm_mean_m2"] for r in valid]))),
               "exec_minus_candidate_mm": 1000 * float(np.mean([r["exec_minus_candidate_mean_m"] for r in valid])),
               "workspace_clip_mm": 1000 * float(np.mean([r["workspace_clip_mean_m"] for r in valid]))}
        for ax, nm in enumerate("xyz"):
            if off[:, ax].std() > 0:
                slope, icpt = np.polyfit(off[:, ax], res[:, ax], 1)
                row[f"slope_res_{nm}_vs_offset_{nm}"] = float(slope)
                row[f"corr_res_{nm}_vs_offset_{nm}"] = float(np.corrcoef(off[:, ax], res[:, ax])[0, 1])
        beh.append(row)
    S["residual_behaviour"] = beh
    va.write_csv(O / "residual_behaviour.csv", beh)

    # geometry ablation + reproduction checks
    def same(a_id, b_id):
        if a_id not in rec or b_id not in rec:
            return None
        A = {r["case_id"]: r for r in rec[a_id]}
        B = {r["case_id"]: r for r in rec[b_id]}
        diff = [c for c in A if c in B and (A[c]["terminal_reason"] != B[c]["terminal_reason"])]
        tdiff = [c for c in A if c in B and A[c]["terminal_reason"] == B[c]["terminal_reason"] == "success"
                 and abs(A[c]["completion_time_s"] - B[c]["completion_time_s"]) > 1e-6]
        return {"a": a_id, "b": b_id, "cases": len(A), "terminal_reason_differs": len(diff),
                "completion_time_differs": len(tdiff), "examples": diff[:5]}
    S["reproduction"] = [x for x in (same("geom_AHG", "geometry_zero"), same("geom_none", "nominal"),
                                     same("geom_bound_0p010", "geometry_zero")) if x]
    combos = DIAG["geometry_ablation"]["combinations"]
    if all(f"geom_{c}" in rec for c in combos):
        S["factorial"] = {}
        rng = np.random.default_rng(645)
        for g in ("all", "stress", "non_stress"):
            y = {c: va.outcome_matrix([rec[f"geom_{c}"]], ids[g])[0] for c in combos}
            eff = va.factorial_effects(y)
            boots = {k: [] for k in eff if k.startswith("effect_")}
            n = len(ids[g])
            for _ in range(2000):
                idx = rng.integers(0, n, n)
                e = va.factorial_effects({c: v[idx] for c, v in y.items()})
                for k in boots:
                    boots[k].append(e[k])
            for k, v in boots.items():
                lo, hi = np.quantile(v, [0.025, 0.975])
                eff[k] = {"estimate": eff[k], "ci_low": float(lo), "ci_high": float(hi)}
            S["factorial"][g] = eff
    (O / "summary.json").write_text(json.dumps(S, indent=1, sort_keys=True, default=float) + "\n")

    # --------- tables.md
    L = ["# v2 development diagnostics — generated tables", "",
         f"Suite `{DIAG['suite']['path']}` (sha256 `{DIAG['suite']['sha256'][:16]}…`), 450 cases, 50 per condition. "
         "Development evidence only. Success in % of valid resets (all resets were valid unless noted).", ""]
    if S["problems"]:
        L += ["**Problems:** " + "; ".join(S["problems"]), ""]

    def row(eid, label=None):
        e = S["entries"].get(eid)
        if not e:
            return None
        cells = [label or eid] + [va.pct(e[g]["success_rate_valid"]) for g in ("non_stress", "stress", "all")]
        cells += [str(e["all"]["n_drop"]), str(e["all"]["n_collision"]), str(e["all"]["n_episode_timeout"]),
                  str(e["all"]["n_release_timeout"]), str(e["all"]["n_invalid_reset"])]
        return "| " + " | ".join(cells) + " |"
    hdr = ["| controller | non-stress (300) | stress (150) | all (450) | drops | collision eps | timeouts | release timeouts | invalid resets |",
           "|---|---|---|---|---|---|---|---|---|"]
    L += ["## Controls", ""] + hdr
    order = ["nominal", "geometry_zero"]
    for b in ("geometry_1cm", "nominal"):
        if b in const_entry:
            order.append(const_entry[b])
    for p in ("combined_init", "combined_final", "residual_init", "residual_final", "combined_no_phase_final"):
        order += [f"{p}_s{s}" for s in SEEDS]
    for eid in order:
        r = row(eid, eid + (" (selected constant)" if eid in const_entry.values() and eid.startswith("const") else ""))
        if r:
            L.append(r)
    L += ["", "## Constant-offset search (x only, y = z = 0)", ""]
    for base, v in S["constant_search"].items():
        L += [f"**{base}** — selected x = {1000 * v['selected']['x_m']:+.0f} mm", "",
              "| x [mm] | success / 450 | stress success / 150 | collision eps | drops |", "|---|---|---|---|---|"]
        for s in v["scores"]:
            mark = " **(selected)**" if s is v["selected"] or s == v["selected"] else ""
            L.append(f"| {1000 * s['x_m']:+.0f}{mark} | {s['success']} | {s['success_stress']} | "
                     f"{s['collision_episodes']} | {s['drops']} |")
        L.append("")
    L += ["## Paired differences (percentage points; 95% CI, seed x case bootstrap)", "",
          "| comparison | cases | metric | A | B | A - B | 95% CI |", "|---|---|---|---|---|---|---|"]
    for c in comps:
        L.append(f"| {c['comparison']} | {c['cases']} | {c['metric']} | {100 * c['mean_a']:.1f} | {100 * c['mean_b']:.1f} | "
                 f"{100 * c['diff']:+.1f} | [{100 * c['ci_low']:+.1f}, {100 * c['ci_high']:+.1f}] |")
    L += ["", "## Residual behaviour of archived v1 checkpoints (valid episodes, means over scored steps)", "",
          "| entry | mean signed residual x/y/z [mm] | across-case std x/y/z [mm] | RMS [mm] | slope res_x vs offset_x | corr | exec - cand [mm] |",
          "|---|---|---|---|---|---|---|"]
    for b in beh:
        L.append(f"| {b['entry']} | {' / '.join(f'{v:+.2f}' for v in b['mean_signed_residual_xyz_mm'])} | "
                 f"{' / '.join(f'{v:.2f}' for v in b['across_case_std_xyz_mm'])} | {b['rms_residual_mm']:.2f} | "
                 f"{b.get('slope_res_x_vs_offset_x', float('nan')):+.3f} | {b.get('corr_res_x_vs_offset_x', float('nan')):+.2f} | "
                 f"{b['exec_minus_candidate_mm']:.2f} |")
    L += ["", "## Geometry component ablation (residual = 0, alignment bound 1 cm)", ""] + hdr
    for c in combos:
        r = row(f"geom_{c}", c)
        if r:
            L.append(r)
    if S.get("reproduction"):
        L += ["", "Reproduction checks (same process, same cases):", ""]
        for x in S["reproduction"]:
            L.append(f"- `{x['a']}` vs `{x['b']}`: terminal reason differs in {x['terminal_reason_differs']}/{x['cases']} "
                     f"cases; completion time differs in {x['completion_time_differs']} successful cases.")
    if S.get("factorial"):
        L += ["", "Factorial effects on success (percentage points, 2^3 contrasts; 95% CI over cases):", "",
              "| effect | all | stress | non-stress |", "|---|---|---|---|"]
        for k in ("effect_A", "effect_H", "effect_G", "effect_AH", "effect_AG", "effect_HG", "effect_AHG"):
            cells = []
            for g in ("all", "stress", "non_stress"):
                e = S["factorial"][g][k]
                cells.append(f"{100 * e['estimate']:+.1f} [{100 * e['ci_low']:+.1f}, {100 * e['ci_high']:+.1f}]")
            L.append(f"| {k.replace('effect_', '')} | " + " | ".join(cells) + " |")
        L += ["", "Conditional effects on stress cases (pp):", ""]
        for k, v in S["factorial"]["stress"]["conditional_effects"].items():
            L.append(f"- {k}: {100 * v:+.1f}")
    L += ["", "## Alignment-bound sensitivity (full geometry, residual = 0)", ""] + hdr
    for b in DIAG["geometry_ablation"]["alignment_bounds_m"]:
        r = row(f"geom_bound_{b:.3f}".replace(".", "p"), f"{100 * b:.1f} cm")
        if r:
            L.append(r)
    (O / "tables.md").write_text("\n".join(L) + "\n")
    print("\n".join(L[:12]))
    if S["problems"]:
        print("PROBLEMS:", S["problems"])
    if not a.no_figures:
        figures(rec, S, O, const_entry)


def figures(rec, S, O, const_entry):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    F = O / "figures"
    F.mkdir(exist_ok=True)
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.4))
    for base, v in S["constant_search"].items():
        xs = [1000 * s["x_m"] for s in v["scores"]]
        axs[0].plot(xs, [100 * s["success"] / s["n"] for s in v["scores"]], marker="o", label=base)
        axs[1].plot(xs, [100 * s["success_stress"] / s["n_stress"] for s in v["scores"]], marker="o", label=base)
    for ax, t in zip(axs, ("all 450 development cases", "150 stress cases")):
        ax.set_xlabel("constant x offset [mm]"); ax.set_ylabel("success [%]"); ax.set_title(t); ax.grid(alpha=0.3)
    axs[0].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(F / "constant_offset_sensitivity.png", dpi=150); plt.close(fig)

    learned = [k for k in rec if rec[k][0].get("checkpoint_sha256")]
    if learned:
        fig, axs = plt.subplots(1, 3, figsize=(11, 3.4), sharey=True)
        for k in sorted(learned):
            if not (k.startswith("combined_final") or k.startswith("residual_final") or k.startswith("combined_init")):
                continue
            rows = [r for r in rec[k] if r["reset_valid"]]
            off = np.array([r["requested_offset_xyz_m"] for r in rows]) * 1000
            res = np.array([r["residual_mean_xyz_m"] for r in rows]) * 1000
            for ax_i in range(3):
                axs[ax_i].scatter(off[:, ax_i], res[:, ax_i], s=4, alpha=0.5, label=k)
        for i, nm in enumerate("xyz"):
            axs[i].set_xlabel(f"requested object offset {nm} [mm]"); axs[i].grid(alpha=0.3)
            axs[i].axhline(0, color="k", lw=0.5)
        axs[0].set_ylabel("episode-mean signed residual [mm]")
        axs[2].legend(fontsize=6, markerscale=3)
        fig.tight_layout(); fig.savefig(F / "signed_residual_vs_offset.png", dpi=150); plt.close(fig)

    combos = ["none", "A", "H", "G", "AH", "AG", "HG", "AHG"]
    if all(f"geom_{c}" in S["entries"] for c in combos):
        fig, ax = plt.subplots(figsize=(7, 3.2))
        w = 0.38
        xs = np.arange(len(combos))
        for j, g in enumerate(("non_stress", "stress")):
            ax.bar(xs + (j - 0.5) * w, [100 * S["entries"][f"geom_{c}"][g]["success_rate_valid"] for c in combos], w, label=g)
        ax.set_xticks(xs, combos); ax.set_ylabel("success [%]"); ax.set_ylim(0, 105); ax.legend(fontsize=8)
        ax.set_title("Geometry components (A alignment, H anchor, G release gate)"); ax.grid(axis="y", alpha=0.3)
        fig.tight_layout(); fig.savefig(F / "geometry_ablation.png", dpi=150); plt.close(fig)
    b_ids = [(b, f"geom_bound_{b:.3f}".replace(".", "p")) for b in (0.005, 0.010, 0.015, 0.020)]
    if all(i in S["entries"] for _, i in b_ids):
        fig, ax = plt.subplots(figsize=(4.6, 3.2))
        for g in ("non_stress", "stress"):
            ax.plot([100 * b for b, _ in b_ids], [100 * S["entries"][i][g]["success_rate_valid"] for _, i in b_ids],
                    marker="o", label=g)
        ax.set_xlabel("alignment bound [cm]"); ax.set_ylabel("success [%]"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
        fig.tight_layout(); fig.savefig(F / "alignment_bound.png", dpi=150); plt.close(fig)


if __name__ == "__main__":
    main()
