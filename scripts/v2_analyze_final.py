#!/usr/bin/env python3
"""v2 final analysis from raw records (CPU only; numpy + matplotlib).

    python3 scripts/v2_analyze_final.py --final <raw>/final/eval --manifest configs/v2/matrices/final/final_manifest.json \
        --selection results/v2/final/selection --train <raw>/final/train --output results/v2/summary

--final holds one sub-folder per final matrix (eval_matrix outputs). --train holds per-run folders with
``train_log.jsonl`` (learning curves; optional). Outputs: ``reconciliation.json``, ``metrics_per_entry.csv``,
``metrics_per_method.csv``, ``comparisons.csv``, ``failure_breakdown.csv``, ``ablation.json``,
``learning_curves.csv``, ``summary.json``, ``tables.md`` and ``figures/``.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from csci645_handover import v2_analysis as va  # noqa: E402

PROT = json.loads((ROOT / "configs/v2/protocol.json").read_text())
CONDS = [c["id"] for c in PROT["evaluation"]["final_conditions"]]
G = dict(PROT["evaluation"]["groups"])
G["in_training"] = G["inner"] + G["outer"]
G["all"] = CONDS
GROUP_ORDER = ["inner", "outer", "in_training", "extrapolation", "all"]
SEEDS = PROT["training"]["seeds"]
METHODS = PROT["training"]["methods"]
ROLES = ["selected", "final", "untrained"]


def cohen_h(p1, p2):
    return 2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p2))


def holm(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, run = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--final", required=True)
    ap.add_argument("--manifest", default=str(ROOT / "configs/v2/matrices/final/final_manifest.json"))
    ap.add_argument("--selection", default=str(ROOT / "results/v2/final/selection"))
    ap.add_argument("--train", default=None)
    ap.add_argument("--output", required=True)
    ap.add_argument("--n-boot", type=int, default=10000)
    ap.add_argument("--no-figures", action="store_true")
    a = ap.parse_args()
    O = Path(a.output)
    O.mkdir(parents=True, exist_ok=True)
    man = json.loads(Path(a.manifest).read_text())
    rec = va.load_records(*[p for p in sorted(Path(a.final).iterdir()) if p.is_dir()])
    suite = [json.loads(x) for x in (ROOT / man["suite"]).read_text().splitlines() if x.strip()]
    ids_all = [c["case_id"] for c in suite]
    ids = {g: [c["case_id"] for c in suite if c["condition"] in G[g]] for g in GROUP_ORDER}
    ids.update({c: [x["case_id"] for x in suite if x["condition"] == c] for c in CONDS})

    # ---------------- reconciliation
    recon = {"expected_total": man["expected_total"], "entries": {}, "problems": []}
    tot = 0
    for eid, n in sorted(man["expected_episodes"].items()):
        rows = rec.get(eid, [])
        got = [r["case_id"] for r in rows]
        d = {"scheduled": n, "recorded": len(rows), "missing": len(set(ids_all) - set(got)),
             "duplicates": len(got) - len(set(got)), "invalid_resets": sum(not r["reset_valid"] for r in rows),
             "infrastructure_errors": sum(r["terminal_reason"] == "infrastructure_error" for r in rows),
             "max_reset_attempts": max((r["reset_attempts"] for r in rows), default=0),
             "retried_resets": sum(r["reset_attempts"] > 1 for r in rows)}
        tot += len(rows)
        if d["recorded"] != n or d["missing"] or d["duplicates"]:
            recon["problems"].append(f"{eid}: {d}")
        recon["entries"][eid] = d
    for dup, src in man["reuse"].items():
        recon["entries"][dup] = {"reused_from": src, **recon["entries"].get(src, {})}
        rec[dup] = rec.get(src, [])
    recon["recorded_total"] = tot
    recon["invalid_resets_total"] = sum(v.get("invalid_resets", 0) for k, v in recon["entries"].items() if "reused_from" not in v)
    recon["infrastructure_errors_total"] = sum(v.get("infrastructure_errors", 0) for k, v in recon["entries"].items() if "reused_from" not in v)
    unexpected = sorted(set(rec) - set(man["expected_episodes"]) - set(man["reuse"]))
    if unexpected:
        recon["problems"].append(f"unexpected record files: {unexpected}")
    (O / "reconciliation.json").write_text(json.dumps(recon, indent=1, sort_keys=True) + "\n")

    # ---------------- per-entry metrics
    per_entry = {}
    rows_csv = []
    for eid, rows in sorted(rec.items()):
        if not rows:
            continue
        s = va.summarize(rows, {g: G[g] for g in GROUP_ORDER})
        per_entry[eid] = s
        for k, d in s.items():
            rows_csv.append({"entry": eid, "condition_or_group": k, **{kk: vv for kk, vv in d.items() if kk != "terminal_reasons"},
                             "terminal_reasons": d["terminal_reasons"]})
    va.write_csv(O / "metrics_per_entry.csv", rows_csv)

    def learned(m, role):
        return [rec[f"{m}_seed{s}__{role}"] for s in SEEDS if rec.get(f"{m}_seed{s}__{role}")]

    method_rows = []
    for m in METHODS:
        for role in ROLES:
            ents = [f"{m}_seed{s}__{role}" for s in SEEDS if f"{m}_seed{s}__{role}" in per_entry]
            for g in GROUP_ORDER + CONDS:
                vals = [per_entry[e][g]["success_rate_valid"] for e in ents if g in per_entry[e]]
                if vals:
                    method_rows.append({"method": m, "role": role, "condition_or_group": g, "seeds": len(vals),
                                        "success_mean": float(np.mean(vals)), "success_sd": float(np.std(vals, ddof=1)) if len(vals) > 1 else None,
                                        "success_per_seed": vals,
                                        "collision_mean": float(np.mean([per_entry[e][g]["n_collision"] / per_entry[e][g]["valid"] for e in ents])),
                                        "drop_mean": float(np.mean([per_entry[e][g]["n_drop"] / per_entry[e][g]["valid"] for e in ents]))})
    va.write_csv(O / "metrics_per_method.csv", method_rows)

    # ---------------- comparisons
    comps = []
    prim = [("combined - geometry_1p5cm", "combined", None, ["geometry_1p5cm"]),
            ("combined - const_geometry_1p5cm", "combined", None, ["const_geometry_1p5cm"]),
            ("residual - nominal", "residual", None, ["nominal"]),
            ("residual - const_nominal", "residual", None, ["const_nominal"]),
            ("combined - combined_no_phase", "combined", "combined_no_phase", None)]
    for role in ("selected", "final"):
        for name, ma, mb, det in prim:
            A = learned(ma, role)
            B = learned(mb, role) if mb else [rec[d] for d in det]
            for g in GROUP_ORDER + CONDS:
                for metric in ("success", "collision"):
                    if metric == "collision" and g in CONDS:
                        continue
                    r = va.paired(A, B, ids[g], key=metric, n_boot=a.n_boot)
                    comps.append({"analysis": "primary" if role == "selected" else "secondary_final_checkpoint",
                                  "comparison": name, "role": role, "cases": g, "metric": metric,
                                  "cohen_h": cohen_h(r["mean_a"], r["mean_b"]) if metric == "success" else None,
                                  **{k: v for k, v in r.items() if k != "resampling"}})
    expl = [("untrained combined - geometry_1p5cm", learned("combined", "untrained"), [rec["geometry_1p5cm"]]),
            ("selected combined - untrained combined", learned("combined", "selected"), learned("combined", "untrained")),
            ("final combined - untrained combined", learned("combined", "final"), learned("combined", "untrained")),
            ("selected residual - untrained residual", learned("residual", "selected"), learned("residual", "untrained")),
            ("geometry_1p5cm - geometry_1cm", [rec["geometry_1p5cm"]], [rec["geometry_1cm"]]),
            ("const_geometry_1p5cm - geometry_1p5cm", [rec["const_geometry_1p5cm"]], [rec["geometry_1p5cm"]]),
            ("const_nominal - nominal", [rec["const_nominal"]], [rec["nominal"]]),
            ("const_geometry_1cm - geometry_1cm", [rec["const_geometry_1cm"]], [rec["geometry_1cm"]]),
            ("geometry_1p5cm - nominal", [rec["geometry_1p5cm"]], [rec["nominal"]])]
    for name, A, B in expl:
        if not A or not B:
            continue
        for g in GROUP_ORDER:
            r = va.paired(A, B, ids[g], key="success", n_boot=a.n_boot)
            comps.append({"analysis": "exploratory", "comparison": name, "role": "-", "cases": g, "metric": "success",
                          "cohen_h": cohen_h(r["mean_a"], r["mean_b"]), **{k: v for k, v in r.items() if k != "resampling"}})
    for role in ("selected", "final"):
        pv = {c["comparison"]: c["p_two_sided_sign"] for c in comps
              if c["role"] == role and c["cases"] == "all" and c["metric"] == "success" and c["analysis"] != "exploratory"}
        adj = holm(pv)
        for c in comps:
            if c["role"] == role and c["cases"] == "all" and c["metric"] == "success" and c["comparison"] in adj:
                c["p_holm"] = adj[c["comparison"]]
    va.write_csv(O / "comparisons.csv", comps)

    # ---------------- residual behaviour of learned entries (signed means, state dependence, failure location)
    beh = []
    for eid, rows in sorted(rec.items()):
        if not rows or not rows[0].get("checkpoint_sha256") or "__" not in eid:
            continue
        v = [r for r in rows if r["reset_valid"]]
        res = np.array([r["residual_mean_xyz_m"] for r in v]) * 1000
        off = np.array([r["requested_offset_xyz_m"] for r in v]) * 1000
        fx = [r["requested_offset_xyz_m"][0] * 1000 for r in v if not r["success"]]
        beh.append({"entry": eid, "mean_signed_residual_xyz_mm": [float(x) for x in res.mean(0)],
                    "across_case_std_xyz_mm": [float(x) for x in res.std(0)],
                    "slope_res_x_vs_offset_x": float(np.polyfit(off[:, 0], res[:, 0], 1)[0]) if res[:, 0].std() > 0 else 0.0,
                    "corr_res_x_vs_offset_x": float(np.corrcoef(off[:, 0], res[:, 0])[0, 1]) if res[:, 0].std() > 0 else 0.0,
                    "rms_residual_mm": 1000 * float(np.sqrt(np.mean([r["residual_sq_norm_mean_m2"] for r in v]))),
                    "failures": len(fx), "failures_with_object_x_offset_above_20mm": sum(x > 20 for x in fx)})
    va.write_csv(O / "residual_behaviour.csv", beh)

    # ---------------- failure breakdown
    fb = []
    for eid, rows in sorted(rec.items()):
        for g in GROUP_ORDER:
            rs = [r for r in rows if r["condition"] in G[g]]
            cnt = collections.Counter(r["terminal_reason"] for r in rs)
            flags = {"flag_misaligned": sum(r["flag_misaligned_at_grasp"] for r in rs),
                     "flag_premature_release": sum(r["flag_premature_release"] for r in rs)}
            fb.append({"entry": eid, "group": g, "n": len(rs), **dict(cnt), **flags})
    va.write_csv(O / "failure_breakdown.csv", fb)

    # ---------------- ablations
    abl = {}
    combos = ["none", "A", "H", "G", "AH", "AG", "HG", "AHG"]
    for tag in ("1cm", "1p5cm"):
        if all(f"ablation_{tag}_{c}" in rec for c in combos):
            abl[tag] = {}
            for g in GROUP_ORDER:
                y = {c: va.outcome_matrix([rec[f"ablation_{tag}_{c}"]], ids[g])[0] for c in combos}
                eff = va.factorial_effects(y)
                rng = np.random.default_rng(645)
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
                abl[tag][g] = eff
    (O / "ablation.json").write_text(json.dumps(abl, indent=1, sort_keys=True) + "\n")

    # ---------------- learning curves
    lc = []
    if a.train:
        for m in METHODS:
            for s in SEEDS:
                f = Path(a.train) / f"{m}_seed{s}" / "train_log.jsonl"
                if not f.exists():
                    continue
                for x in f.read_text().splitlines():
                    if x.strip():
                        r = json.loads(x)
                        lc.append({"run": f"{m}_seed{s}", "method": m, "seed": s, "iteration": r["iteration"],
                                   "transitions": r["transitions"], "scored_transitions": r.get("scored_transitions"),
                                   "mean_step_reward": r["mean_step_reward"], "episodes": r["episodes"],
                                   "train_success": r.get("train_success"), "train_drop": r.get("train_drop"),
                                   "train_collision": r.get("train_collision"), "action_std": r.get("action_std")})
        va.write_csv(O / "learning_curves.csv", lc)
    sel_dir = Path(a.selection)
    selection = {p.stem: json.loads(p.read_text()) for p in sorted(sel_dir.glob("*_seed*.json"))} if sel_dir.exists() else {}

    S = {"reconciliation": {k: v for k, v in recon.items() if k != "entries"}, "per_entry": per_entry, "residual_behaviour": beh,
         "comparisons": comps, "ablation": abl, "selection": {k: v["selected"] for k, v in selection.items()}}
    (O / "summary.json").write_text(json.dumps(S, indent=1, sort_keys=True, default=float) + "\n")
    tables(O, recon, per_entry, method_rows, comps, abl, selection, rec, beh)
    if not a.no_figures:
        figures(O, per_entry, method_rows, lc, abl)
    print((O / "tables.md").read_text()[:3000])


def tables(O, recon, per_entry, method_rows, comps, abl, selection, rec, beh=()):
    L = ["# v2 final results — generated tables", "",
         f"Final suite `configs/v2/suites/final.jsonl`: {len(CONDS)} conditions x 200 cases. Success in % of valid resets. "
         f"Groups: inner = {', '.join(G['inner'])}; outer = {', '.join(G['outer'])}; extrapolation = {', '.join(G['extrapolation'])}.", "",
         "## Reconciliation", "",
         f"- Expected episodes (manifest): {recon['expected_total']}; recorded: {recon['recorded_total']}; "
         f"invalid resets: {recon['invalid_resets_total']}; infrastructure errors: {recon['infrastructure_errors_total']}.",
         f"- Reused (identical configuration, not re-run): " + (", ".join(f"`{k}` = `{v['reused_from']}`" for k, v in recon["entries"].items() if "reused_from" in v) or "none"),
         f"- Problems: {recon['problems'] or 'none'}", ""]
    hdr = "| controller | " + " | ".join(GROUP_ORDER) + " | drops | collision eps | timeouts | release timeouts |"
    sep = "|---" * (len(GROUP_ORDER) + 5) + "|"
    L += ["## Deterministic controllers", "", hdr, sep]
    for eid in PROT["deterministic_controllers"]:
        e = per_entry.get(eid)
        if not e or eid.startswith("ablation") or eid.startswith("bound"):
            continue
        L.append(f"| {eid} | " + " | ".join(va.pct(e[g]["success_rate_valid"]) for g in GROUP_ORDER) +
                 f" | {e['all']['n_drop']} | {e['all']['n_collision']} | {e['all']['n_episode_timeout']} | {e['all']['n_release_timeout']} |")
    L += ["", "## Learned policies (mean over 3 seeds; per-seed values in metrics_per_method.csv)", "",
          "| method | checkpoint | " + " | ".join(GROUP_ORDER) + " |", "|---" * (len(GROUP_ORDER) + 2) + "|"]
    mr = {(r["method"], r["role"], r["condition_or_group"]): r for r in method_rows}
    for m in METHODS:
        for role in ROLES:
            cells = []
            for g in GROUP_ORDER:
                r = mr.get((m, role, g))
                cells.append("–" if not r else f"{100 * r['success_mean']:.1f} ({100 * (r['success_sd'] or 0):.1f})")
            L.append(f"| {m} | {role} | " + " | ".join(cells) + " |")
    L += ["", "(sd over seeds in parentheses)", "", "## Per-condition success", "",
          "| condition | relation | nominal | geometry 1 cm | geometry 1.5 cm | geo 1.5 + const | nominal + const | residual sel | combined sel | no-phase sel | combined final |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    rel = {c["id"]: c["relation_to_training"] for c in PROT["evaluation"]["final_conditions"]}
    for c in CONDS:
        def det(e):
            return va.pct(per_entry[e][c]["success_rate_valid"]) if e in per_entry else "–"

        def lm(m, role):
            r = mr.get((m, role, c))
            return "–" if not r else f"{100 * r['success_mean']:.1f}"
        L.append(f"| {c} | {rel[c].split(' ')[0]} | {det('nominal')} | {det('geometry_1cm')} | {det('geometry_1p5cm')} | "
                 f"{det('const_geometry_1p5cm')} | {det('const_nominal')} | {lm('residual', 'selected')} | {lm('combined', 'selected')} | "
                 f"{lm('combined_no_phase', 'selected')} | {lm('combined', 'final')} |")
    L += ["", "## Comparisons (percentage points; 95% CI from the seed x case paired bootstrap)", "",
          "| analysis | comparison | cases | A | B | A - B | 95% CI | Cohen h | Holm p |", "|---|---|---|---|---|---|---|---|---|"]
    for c in comps:
        if c["metric"] != "success" or c["cases"] not in GROUP_ORDER:
            continue
        hp = f"{c['p_holm']:.3f}" if c.get("p_holm") is not None else ""
        L.append(f"| {c['analysis']} | {c['comparison']} | {c['cases']} | {100 * c['mean_a']:.1f} | {100 * c['mean_b']:.1f} | "
                 f"{100 * c['diff']:+.1f} | [{100 * c['ci_low']:+.1f}, {100 * c['ci_high']:+.1f}] | {c['cohen_h']:+.2f} | {hp} |")
    L += ["", "Collision-episode rate differences (pp):", "", "| analysis | comparison | cases | A - B | 95% CI |", "|---|---|---|---|---|"]
    for c in comps:
        if c["metric"] == "collision" and c["cases"] in ("all", "extrapolation"):
            L.append(f"| {c['analysis']} | {c['comparison']} | {c['cases']} | {100 * c['diff']:+.1f} | [{100 * c['ci_low']:+.1f}, {100 * c['ci_high']:+.1f}] |")
    L += ["", "## Geometry component ablations and alignment bounds (held-out)", ""]
    for tag in ("1cm", "1p5cm"):
        L += [f"**Alignment bound {tag.replace('p', '.')}** — success %", "", "| combination | " + " | ".join(GROUP_ORDER) + " |",
              "|---" * (len(GROUP_ORDER) + 1) + "|"]
        for combo in ("none", "A", "H", "G", "AH", "AG", "HG", "AHG"):
            e = per_entry.get(f"ablation_{tag}_{combo}")
            if e:
                L.append(f"| {combo} | " + " | ".join(va.pct(e[g]["success_rate_valid"]) for g in GROUP_ORDER) + " |")
        if tag in abl:
            L += ["", "| effect | " + " | ".join(GROUP_ORDER) + " |", "|---" * (len(GROUP_ORDER) + 1) + "|"]
            for k in ("effect_A", "effect_H", "effect_G", "effect_AH", "effect_AG", "effect_HG", "effect_AHG"):
                L.append(f"| {k[7:]} | " + " | ".join(
                    f"{100 * abl[tag][g][k]['estimate']:+.1f} [{100 * abl[tag][g][k]['ci_low']:+.1f}, {100 * abl[tag][g][k]['ci_high']:+.1f}]"
                    for g in GROUP_ORDER) + " |")
        L.append("")
    L += ["| alignment bound | " + " | ".join(GROUP_ORDER) + " |", "|---" * (len(GROUP_ORDER) + 1) + "|"]
    for b in ("bound_0p005", "bound_0p010", "bound_0p015", "bound_0p020"):
        e = per_entry.get(b)
        if e:
            L.append(f"| {b[6:].replace('p', '.')} m | " + " | ".join(va.pct(e[g]["success_rate_valid"]) for g in GROUP_ORDER) + " |")
    if beh:
        L += ["", "## Residual behaviour of learned policies (held-out, episode means over scored steps)", "",
              "| entry | mean signed residual x/y/z [mm] | across-case std x/y/z [mm] | slope x vs object x | corr | RMS [mm] | failures (object x > +20 mm) |",
              "|---|---|---|---|---|---|---|"]
        for b in beh:
            if b["entry"].endswith("__untrained"):
                continue
            L.append(f"| {b['entry']} | {' / '.join(f'{v:+.2f}' for v in b['mean_signed_residual_xyz_mm'])} | "
                     f"{' / '.join(f'{v:.2f}' for v in b['across_case_std_xyz_mm'])} | {b['slope_res_x_vs_offset_x']:+.3f} | "
                     f"{b['corr_res_x_vs_offset_x']:+.2f} | {b['rms_residual_mm']:.2f} | {b['failures']} ({b['failures_with_object_x_offset_above_20mm']}) |")
    if selection:
        L += ["", "## Checkpoint selection (validation, 400 cases)", "",
              "| run | candidates (success % / collision % / RMS residual mm) | selected | tied on success |", "|---|---|---|---|"]
        for rid, v in sorted(selection.items()):
            cs = "; ".join(f"{c['tag'].replace('step_', '')}: {100 * c['success_rate']:.1f}/{100 * c['collision_rate']:.1f}/"
                           f"{1000 * math.sqrt(c['residual_sq_norm_mean_m2']):.2f}" for c in v["candidates"])
            L.append(f"| {rid} | {cs} | {v['selected']['tag']} | {len(v['ties_on_success'])} |")
    (O / "tables.md").write_text("\n".join(L) + "\n")


def figures(O, per_entry, method_rows, lc, abl):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    F = O / "figures"
    F.mkdir(exist_ok=True)
    mr = {(r["method"], r["role"], r["condition_or_group"]): r for r in method_rows}
    fig, ax = plt.subplots(figsize=(11, 3.8))
    series = [("nominal", None), ("geometry_1p5cm", None), ("const_geometry_1p5cm", None), ("residual", "selected"),
              ("combined", "selected"), ("combined", "final")]
    w = 0.13
    xs = np.arange(len(CONDS))
    for j, (k, role) in enumerate(series):
        if role:
            vals = [100 * mr[(k, role, c)]["success_mean"] if (k, role, c) in mr else np.nan for c in CONDS]
            lab = f"{k} ({role})"
        else:
            vals = [100 * per_entry[k][c]["success_rate_valid"] if k in per_entry else np.nan for c in CONDS]
            lab = k
        ax.bar(xs + (j - 2.5) * w, vals, w, label=lab)
    ax.set_xticks(xs, CONDS, rotation=30, ha="right", fontsize=7)
    ax.set_ylabel("success [%]"); ax.set_ylim(0, 105); ax.grid(axis="y", alpha=0.3); ax.legend(fontsize=7, ncol=3)
    ax.axvline(8.5, color="k", lw=0.6, ls="--")
    fig.tight_layout(); fig.savefig(F / "success_by_condition.png", dpi=150); plt.close(fig)
    if lc:
        fig, axs = plt.subplots(1, 2, figsize=(10, 3.4))
        win = 10  # iterations (~2 episode lengths); all environments start together, so per-iteration values burst
        colors = {"residual": "tab:red", "combined": "tab:purple", "combined_no_phase": "tab:green"}
        styles = {11: "-", 22: "--", 33: ":"}
        for run in sorted({r["run"] for r in lc}):
            pts = [r for r in lc if r["run"] == run]
            m, sd = pts[0]["method"], pts[0]["seed"]
            xs, rew, suc = [], [], []
            for i in range(0, len(pts) - win + 1, win):
                w = pts[i:i + win]
                xs.append(w[-1]["transitions"] / 1e6)
                rew.append(float(np.mean([p["mean_step_reward"] for p in w])))
                ep = sum(p["episodes"] for p in w)
                suc.append(sum((p["train_success"] or 0) for p in w) / ep if ep else np.nan)
            kw = dict(color=colors.get(m), ls=styles.get(sd, "-"), lw=1.0, label=run)
            axs[0].plot(xs, rew, **kw)
            axs[1].plot(xs, suc, **kw)
        axs[0].set_xlabel("transitions [M]"); axs[0].set_ylabel(f"mean step reward ({win}-iteration windows)")
        axs[1].set_xlabel("transitions [M]"); axs[1].set_ylabel("training-episode success (stochastic policy)")
        for x in axs:
            x.grid(alpha=0.3)
            for f in (0.1, 0.3, 0.5):
                x.axvline(10 * f, color="k", lw=0.4, ls=":")
        axs[1].legend(fontsize=6)
        fig.tight_layout(); fig.savefig(F / "learning_curves.png", dpi=150); plt.close(fig)
    combos = ["none", "A", "H", "G", "AH", "AG", "HG", "AHG"]
    for tag in ("1cm", "1p5cm"):
        if not all(f"ablation_{tag}_{c}" in per_entry for c in combos):
            continue
        fig, ax = plt.subplots(figsize=(7, 3.2))
        w = 0.25
        for j, g in enumerate(("inner", "outer", "extrapolation")):
            ax.bar(np.arange(8) + (j - 1) * w, [100 * per_entry[f"ablation_{tag}_{c}"][g]["success_rate_valid"] for c in combos], w, label=g)
        ax.set_xticks(np.arange(8), combos); ax.set_ylim(0, 105); ax.set_ylabel("success [%]"); ax.legend(fontsize=8)
        ax.set_title(f"Held-out geometry components, alignment bound {tag.replace('p', '.')}"); ax.grid(axis="y", alpha=0.3)
        fig.tight_layout(); fig.savefig(F / f"ablation_{tag}.png", dpi=150); plt.close(fig)
    bs = [("bound_0p005", 0.5), ("bound_0p010", 1.0), ("bound_0p015", 1.5), ("bound_0p020", 2.0)]
    if all(b in per_entry for b, _ in bs):
        fig, ax = plt.subplots(figsize=(4.8, 3.2))
        for g in ("inner", "outer", "extrapolation"):
            ax.plot([v for _, v in bs], [100 * per_entry[b][g]["success_rate_valid"] for b, _ in bs], marker="o", label=g)
        ax.set_xlabel("alignment bound [cm]"); ax.set_ylabel("success [%]"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
        fig.tight_layout(); fig.savefig(F / "alignment_bound.png", dpi=150); plt.close(fig)


if __name__ == "__main__":
    main()
