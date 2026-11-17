#!/usr/bin/env python3
"""V3 figures from the analysis outputs (CPU; numpy + matplotlib). Every number plotted comes from files under
results/v3/ (summary, selection) or from raw trace files listed on the command line.

    python3 scripts/v3_figures.py --summary results/v3/summary --selection results/v3/selection \
        --output results/v3/figures [--traces <final run dir>/...json ...]

Figures: pipeline (data access), validation learning curves (all runs), severity curves with per-seed points,
paired effects, failure breakdown, and (with --traces) true/raw/estimated trajectories with residual and contact.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

FAMILIES = ["combined_clean_ff", "combined_robust_ff", "combined_robust_history", "residual_robust_history", "combined_robust_repeat"]
BASELINES = ["nominal", "geometry_raw", "geometry_filtered", "geometry_common"]
COLORS = {"combined_clean_ff": "#8c564b", "combined_robust_ff": "#1f77b4", "combined_robust_history": "#d62728",
          "residual_robust_history": "#2ca02c", "combined_robust_repeat": "#9467bd", "nominal": "#7f7f7f",
          "geometry_raw": "#bcbd22", "geometry_filtered": "#17becf", "geometry_common": "#000000",
          "geometry_best_constant": "#000000", "geometry_giver": "#000000"}
SEVERITY = {"bias": [("physical_only", 0), ("bias_2mm", 2), ("bias_5mm", 5), ("bias_10mm", 10)],
            "noise": [("physical_only", 0), ("noise_1mm", 1), ("noise_2mm", 2), ("noise_4mm", 4)],
            "delay": [("physical_only", 0), ("delay_1step", 1), ("delay_2step", 2), ("delay_4step", 4)]}
UNITS = {"bias": "bias amplitude per axis [mm]", "noise": "noise sigma per axis [mm]", "delay": "delay [control steps of 50 ms]"}


def plt_():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.titlesize": 11})
    return plt


def pipeline(out: Path):
    plt = plt_()
    fig, ax = plt.subplots(figsize=(11, 4.6))
    ax.axis("off")
    box = dict(boxstyle="round,pad=0.4", fc="#f2f2f2", ec="#333333")
    hot = dict(boxstyle="round,pad=0.4", fc="#fde0dd", ec="#a50f15")
    acc = dict(boxstyle="round,pad=0.4", fc="#e5f5e0", ec="#006d2c")
    T = [(0.07, 0.80, "PhysX state\n(true object pose,\nrobots, contacts)", box),
         (0.30, 0.80, "translation sensor\ny = x(k-d) + b\n  + sigma*n(seed, k)\n(bias, noise, delay)", hot),
         (0.53, 0.80, "estimator\nEMA (alpha) or giver reference\n(giver TCP - nominal grasp,\nwhile giver holds)", hot),
         (0.77, 0.80, "controller measurements\nestimated position, velocity\n(finite difference of estimate)", hot),
         (0.53, 0.40, "accurate measurements\norientation, joints, TCPs,\nfinger widths, contact forces", acc),
         (0.77, 0.40, "geometry (alignment, anchor,\ncontact-gated release)\n+ policy input (46 or 5x46)", box),
         (0.30, 0.13, "true-state reward (training only)\nindependent 2 s receiver-only\nhold evaluator", acc)]
    for x, y, t, st in T:
        ax.text(x, y, t, ha="center", va="center", fontsize=9.2, bbox=st, transform=ax.transAxes)
    arrows = [((0.135, 0.80), (0.215, 0.80)), ((0.385, 0.80), (0.435, 0.80)), ((0.63, 0.80), (0.68, 0.80)),
              ((0.77, 0.70), (0.77, 0.50)), ((0.62, 0.40), (0.67, 0.40)), ((0.07, 0.70), (0.42, 0.42)), ((0.07, 0.70), (0.25, 0.21))]
    for (x0, y0), (x1, y1) in arrows:
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), xycoords="axes fraction", arrowprops=dict(arrowstyle="->", lw=1.2))
    ax.text(0.98, 0.04, "red: corrupted/estimated translation path; green: accurate or ground-truth paths.\n"
                        "Actor and critic receive the same policy input; no true translation, bias, seed or delay label.",
            ha="right", va="bottom", fontsize=8, transform=ax.transAxes)
    fig.tight_layout()
    fig.savefig(out / "pipeline.png", dpi=160)
    plt.close(fig)


def learning_curves(sel_dir: Path, out: Path):
    plt = plt_()
    fig, axes = plt.subplots(1, len(FAMILIES), figsize=(15, 3.4), sharey=True)
    for ax, fam in zip(axes, FAMILIES):
        for f in sorted(sel_dir.glob(f"{fam}_s*.json")):
            r = json.loads(f.read_text())
            pts = sorted([(0, r["untrained_control"]["success_rate"])] +
                         [(c["transitions"], c["success_rate"]) for c in r["candidates"]])
            x, y = zip(*pts)
            ax.plot(np.array(x) / 1e6, 100 * np.array(y), "-o", ms=3, color=COLORS[fam], alpha=0.8,
                    label=f.stem.split("_s")[-1])
            sel = next(c for c in r["candidates"] if c["tag"] == r["selected"])
            ax.plot(sel["transitions"] / 1e6, 100 * sel["success_rate"], "*", ms=11, color="k")
        ax.set_title(fam.replace("_", " "), fontsize=9)
        ax.set_xlabel("transitions [M]")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7, title="seed", title_fontsize=7)
    axes[0].set_ylabel("validation success [%] (240 cases)")
    fig.suptitle("Validation learning curves of all 23 formal runs (step 0 = untrained control; star = selected)", fontsize=10)
    fig.tight_layout()
    fig.savefig(out / "learning_curves.png", dpi=160)
    plt.close(fig)


def load_counts(summary: Path):
    rows = list(csv.DictReader(open(summary / "per_seed_condition.csv")))
    for r in rows:
        r["success_rate"] = float(r["success_rate"])
    return rows


def severity(summary: Path, out: Path, role="selected"):
    plt = plt_()
    rows = load_counts(summary)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2), sharey=True)
    for ax, (kind, levels) in zip(axes, SEVERITY.items()):
        for fam in FAMILIES + BASELINES:
            r_role = "baseline" if fam in BASELINES else role
            xs, means = [], []
            for cond, lvl in levels:
                vals = [r["success_rate"] for r in rows if r["family"] == fam and r["role"] == r_role and r["condition"] == cond]
                if not vals:
                    continue
                xs.append(lvl)
                means.append(100 * np.mean(vals))
                if fam in FAMILIES:
                    ax.scatter([lvl + 0.08 * (FAMILIES.index(fam) - 2)] * len(vals), 100 * np.array(vals), s=9,
                               color=COLORS[fam], alpha=0.5)
            ls = "--" if fam in BASELINES else "-"
            ax.plot(xs, means, ls, marker="o", ms=3, color=COLORS[fam], label=fam.replace("_", " "))
        ax.set_xlabel(UNITS[kind])
        ax.set_title(f"{kind} severity (final suite, 200 cases per level)")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel(f"success [%] ({role} checkpoints; dots = training seeds)")
    axes[-1].legend(fontsize=7, loc="lower left")
    fig.tight_layout()
    fig.savefig(out / f"severity_{role}.png", dpi=160)
    plt.close(fig)


def effects(summary: Path, out: Path):
    plt = plt_()
    E = json.loads((summary / "paired_effects.json").read_text())
    sets = [("mixed_id",), ("mixed_ood",)]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), sharey=True)
    for ax, role in zip(axes, ("selected", "final")):
        rows = [e for e in E if e["role"] == role and len(e["conditions"]) == 1]
        labels, y = [], 0
        for e in rows:
            lab = f"{e['left'].replace('_', ' ')} − {e['right'].replace('_', ' ')} [{e['conditions'][0]}]"
            ci = e.get("familywise_95_interval") or e
            ax.errorbar(e["difference_pp"], y, xerr=[[e["difference_pp"] - e["ci_low_pp"]], [e["ci_high_pp"] - e["difference_pp"]]],
                        fmt="o", color="#d62728" if e.get("primary") else "#1f77b4", capsize=2)
            if e.get("primary"):
                ax.plot([ci["ci_low_pp"], ci["ci_high_pp"]], [y, y], color="#d62728", lw=4, alpha=0.3)
            ax.scatter(e["per_seed_difference_pp"], [y] * len(e["per_seed_difference_pp"]), s=8, color="k", alpha=0.5, zorder=3)
            labels.append(lab)
            y += 1
        ax.axvline(0, color="k", lw=0.8)
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels, fontsize=7)
        ax.set_xlabel("success difference [pp]")
        ax.set_title(f"{role} checkpoints")
        ax.grid(axis="x", alpha=0.3)
    fig.suptitle("Paired effects: point = mean, bar = 95% CI, red band = 97.5% family-wise (primary), dots = per seed", fontsize=10)
    fig.tight_layout()
    fig.savefig(out / "paired_effects.png", dpi=160)
    plt.close(fig)


def failures(summary: Path, out: Path):
    plt = plt_()
    rows = load_counts(summary)
    fams = BASELINES + FAMILIES
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.2), sharey=True)
    keys = [("terminal_success", "#2ca02c"), ("terminal_drop", "#ff7f0e"), ("terminal_prohibited_collision", "#d62728"),
            ("terminal_release_timeout", "#9467bd"), ("terminal_episode_timeout", "#7f7f7f")]  # exclusive terminal reasons
    for ax, cond in zip(axes, ("mixed_id", "mixed_ood")):
        bottom = np.zeros(len(fams))
        for k, col in keys:
            vals = []
            for f in fams:
                rr = [r for r in rows if r["family"] == f and r["role"] in ("selected", "baseline") and r["condition"] == cond]
                vals.append(np.mean([float(r[k]) / float(r["scheduled"]) for r in rr]) * 100 if rr else 0)
            ax.bar(range(len(fams)), vals, bottom=bottom, color=col, label=k.replace("terminal_", "").replace("_", " "))
            bottom += np.array(vals)
        ax.set_xticks(range(len(fams)))
        ax.set_xticklabels([f.replace("_", "\n") for f in fams], fontsize=7)
        ax.set_title(f"outcomes, {cond} (selected checkpoints; mean over seeds)")
    axes[0].set_ylabel("% of 200 scheduled cases")
    axes[1].legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    fig.savefig(out / "failure_breakdown.png", dpi=160)
    plt.close(fig)


def traces(paths: list[str], out: Path, cases: list[str] | None = None):
    plt = plt_()
    for p in paths:
        tr = json.loads(Path(p).read_text())
        for cid, rows in ([(c, tr[c]) for c in cases if c in tr] if cases else list(tr.items())[:2]):
            rows = [r for r in rows if r.get("mode_scored") or r.get("reason")]
            if not rows or "observed_obj_pos" not in rows[0]:
                continue
            t = np.array([r["t"] for r in rows])
            fig, axs = plt.subplots(3, 1, figsize=(11.5, 7), sharex=True)
            cols = ["#1f77b4", "#d62728", "#2ca02c"]
            for k, lab in enumerate("xyz"):
                true = np.array([r["obj_pos"][k] for r in rows])
                axs[0].plot(t, 1000 * (np.array([r["observed_obj_pos"][k] for r in rows]) - true), ".", ms=3, alpha=0.6,
                            color=cols[k], label=f"raw sensor − true, {lab}")
                axs[0].plot(t, 1000 * (np.array([r["controller_obj_pos"][k] for r in rows]) - true), "-", lw=1.4,
                            color=cols[k], label=f"controller estimate − true, {lab}")
                axs[0].plot(t, 1000 * (true - true[0]), ":", lw=1.0, color=cols[k], label=f"true motion from start, {lab}")
            axs[0].axhline(0, color="k", lw=0.5)
            axs[0].set_ylabel("translation error / motion [mm]")
            axs[0].legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.01, 1.0))
            res = 1000 * np.array([r["residual"] for r in rows])
            for k, lab in enumerate("xyz"):
                axs[1].plot(t, res[:, k], label=f"residual {lab}")
            axs[1].set_ylabel("commanded residual [mm]")
            axs[1].legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.01, 1.0))
            axs[2].plot(t, [r["giver_force"][0] for r in rows], label="giver finger force")
            axs[2].plot(t, [r["recv_force"][0] for r in rows], label="receiver finger force")
            axs[2].plot(t, [r["hold_timer"] for r in rows], label="independent-hold timer [s]")
            axs[2].set_ylabel("force [N] / timer [s]")
            axs[2].set_xlabel("scored time [s]")
            axs[2].legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.01, 1.0))
            fig.suptitle(f"{Path(p).stem}: {cid}", fontsize=10)
            fig.tight_layout()
            fig.savefig(out / f"trace_{Path(p).stem}_{cid}.png", dpi=140)
            plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--summary", default="results/v3/summary")
    ap.add_argument("--selection", default="results/v3/selection")
    ap.add_argument("--output", default="results/v3/figures")
    ap.add_argument("--traces", nargs="*", default=[])
    ap.add_argument("--trace-cases", nargs="*", default=None, help="case IDs to plot from each trace file")
    a = ap.parse_args()
    out = Path(a.output)
    out.mkdir(parents=True, exist_ok=True)
    pipeline(out)
    if Path(a.selection).exists():
        learning_curves(Path(a.selection), out)
    if (Path(a.summary) / "per_seed_condition.csv").exists():
        for role in ("selected", "final"):
            severity(Path(a.summary), out, role)
        effects(Path(a.summary), out)
        failures(Path(a.summary), out)
    traces(a.traces, out, a.trace_cases)
    print("figures:", sorted(p.name for p in out.glob("*.png")))


if __name__ == "__main__":
    main()
