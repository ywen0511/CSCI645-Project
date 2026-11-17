#!/usr/bin/env python3
"""V4 figures from generated summaries and raw records (CPU; numpy + matplotlib).

    python3 scripts/v4_figures.py --summary results/v4/summary --runs <runs root> --output results/v4/figures

Figures (PNG, 200 dpi, deterministic): severity_selected / severity_final (success by condition; baselines and
learned families in separate panels), paired_effects (primary + key secondary contrasts, selected checkpoints,
mixed_id), failure_breakdown (exclusive terminal reasons), grasp_offsets (requested vs achieved in-grasp offset;
calibration error), learning_curves (formal training logs), traces (estimate error over time for the six
supplementary trace cases, when present). Colors are fixed per entity (never by rank).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from csci645_handover import v4_protocol as v4  # noqa: E402

plt.rcParams.update({"svg.hashsalt": "v4", "font.size": 8, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "axes.labelcolor": "#0b0b0b", "xtick.color": "#52514e",
                     "ytick.color": "#52514e", "axes.grid": True, "grid.color": "#e4e3df", "grid.linewidth": 0.6,
                     "legend.frameon": False, "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
# fixed entity -> color (reference categorical order; nominal neutral)
COLOR = {"geometry_calibrated": "#2a78d6", "geometry_fixed": "#eb6834", "geometry_ema": "#1baf7a", "nominal": "#8a8984",
         "combined_robust_history": "#6250d6", "combined_robust_ff": "#e87ba4", "combined_clean_ff": "#eda100",
         "combined_robust_repeat": "#008300", "residual_robust_history": "#e34948"}
LABEL = {"geometry_calibrated": "calibrated geometry (= best constant)", "geometry_fixed": "fixed-transform geometry (V3)",
         "geometry_ema": "EMA geometry", "nominal": "nominal", "combined_robust_history": "robust history (4 frames)",
         "combined_robust_ff": "robust feed-forward", "combined_clean_ff": "clean feed-forward",
         "combined_robust_repeat": "repeated current frame", "residual_robust_history": "residual-only history"}
BASES = ["nominal", "geometry_fixed", "geometry_ema", "geometry_calibrated"]
LEARNED = ["combined_clean_ff", "combined_robust_ff", "combined_robust_history", "combined_robust_repeat", "residual_robust_history"]
SHORT = {c: c.replace("boundary_", "").replace("_", " ") for c in v4.ORDER}


def save(fig, path):
    fig.savefig(path, dpi=200, metadata={"Software": None})
    plt.close(fig)


def severity(summary, role, out):
    by = {(r["family"], r["role"], r["condition"]): r for r in summary}
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
    x = np.arange(len(v4.ORDER))
    for ax, fams, title in ((axes[0], BASES, "Deterministic baselines"), (axes[1], LEARNED, f"Learned ({role} checkpoints, mean of 5 seeds)")):
        n = len(fams)
        for k, f in enumerate(fams):
            r = "baseline" if f in BASES else role
            y = [100 * by[(f, r, c)]["success_rate_mean"] for c in v4.ORDER]
            off = (k - (n - 1) / 2) * 0.13
            ax.plot(x + off, y, "o", ms=4.2, color=COLOR[f], mec="#fcfcfb", mew=0.8, label=LABEL[f])
            if f not in BASES:
                lo = [100 * min(by[(f, r, c)]["success_rate_per_seed"]) for c in v4.ORDER]
                hi = [100 * max(by[(f, r, c)]["success_rate_per_seed"]) for c in v4.ORDER]
                ax.vlines(x + off, lo, hi, color=COLOR[f], lw=1.2, alpha=0.8)
        ax.set_xticks(x, [SHORT[c] for c in v4.ORDER], rotation=40, ha="right")
        ax.set_title(title, loc="left", fontsize=8.5)
        ax.set_ylim(-3, 103)
        ax.legend(loc="lower left", fontsize=6.5, ncol=1)
    axes[0].set_ylabel("success (% of 200 cases)")
    fig.tight_layout()
    save(fig, out)


def effects(eff, out):
    keep = [("combined_robust_history", "combined_robust_ff"), ("combined_robust_history", "best_constant_geometry"),
            ("combined_robust_ff", "combined_clean_ff"), ("combined_robust_history", "combined_robust_repeat"),
            ("residual_robust_history", "nominal"), ("geometry_calibrated", "geometry_fixed"), ("geometry_ema", "geometry_fixed"),
            ("geometry_calibrated", "geometry_ema")]
    rows = []
    for l, r in keep:
        for cond in ("mixed_id", "grasp_15mm", "mixed_ood"):
            e = next((x for x in eff if x["left"] == l and x["right"] == r and x["role"] == "selected" and x["conditions"] == [cond]), None)
            if e:
                rows.append((f"{l} − {r}  [{cond}]", e))
    fig, ax = plt.subplots(figsize=(7.2, 0.24 * len(rows) + 0.9))
    for i, (name, e) in enumerate(rows):
        y = len(rows) - 1 - i
        prim = e.get("primary")
        ax.hlines(y, e["ci_low_pp"], e["ci_high_pp"], color="#2a78d6" if prim else "#52514e", lw=2 if prim else 1.2)
        if prim:
            fw = e["bonferroni_97_5"]
            ax.hlines(y, fw["ci_low_pp"], fw["ci_high_pp"], color="#2a78d6", lw=0.8, alpha=0.5)
        ax.plot(e["difference_pp"], y, "o", ms=4.5, color="#2a78d6" if prim else "#0b0b0b")
    ax.axvline(0, color="#8a8984", lw=0.8)
    ax.set_yticks(range(len(rows)), [n for n, _ in reversed(rows)], fontsize=6.3)
    ax.set_xlabel("success difference (pp), 95% CI")
    ax.set_title("Selected checkpoints; blue = primary (thin: Bonferroni 97.5%)", loc="right", fontsize=7.5)
    fig.tight_layout()
    save(fig, out)


def failures(summary, out):
    by = {(r["family"], r["role"], r["condition"]): r for r in summary}
    reasons = [("success", "#2a78d6"), ("prohibited_collision", "#e34948"), ("release_timeout", "#eda100"),
               ("drop", "#6250d6"), ("episode_timeout", "#8a8984")]
    conds = ["grasp_15mm", "mixed_id", "mixed_ood"]
    ents = [(f, "baseline") for f in BASES] + [(f, "selected") for f in LEARNED]
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.8), sharey=True)
    for ax, c in zip(axes, conds):
        left = np.zeros(len(ents))
        for reason, col in reasons:
            v = np.array([by[(f, r, c)]["terminal_mean"][reason] for f, r in ents])
            ax.barh(range(len(ents)), v, left=left, color=col, edgecolor="#fcfcfb", lw=1, label=reason.replace("_", " "))
            left += v
        ax.set_title(c, loc="left", fontsize=8.5)
        ax.set_xlim(0, 200)
        ax.invert_yaxis()
    axes[0].set_yticks(range(len(ents)), [LABEL[f] + ("" if r == "baseline" else " (sel.)") for f, r in ents], fontsize=6.5)
    axes[1].set_xlabel("cases (of 200; learned = mean over seeds); exclusive terminal reason")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=5, fontsize=7, bbox_to_anchor=(0.6, 0.0))
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    save(fig, out)


def grasp_offsets(runs, index, out):
    e = next(x for x in index["entries"] if x["family"] == "geometry_calibrated")
    rows = [json.loads(l) for l in (runs / e["records"]).read_text().splitlines() if l.strip()]
    rows = [r for r in rows if r["reset_valid"] and r["condition"] != "clean"]
    req = np.array([r["grasp_offset_requested_xyz_m"] for r in rows]) * 1000
    ach = np.array([r["grasp_offset_achieved_xyz_m"] for r in rows]) * 1000
    cal = np.array([r["calibration_offset_world_m"] for r in rows]) * 1000
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.1))
    for ax, k, name in ((axes[0], 0, "x (bar axis)"), (axes[1], 2, "z (vertical)")):
        ax.plot(req[:, k], ach[:, k], "o", ms=2.2, color="#2a78d6", alpha=0.45, mew=0)
        lim = [min(req[:, k].min(), ach[:, k].min()) - 1, max(req[:, k].max(), ach[:, k].max()) + 1]
        ax.plot(lim, lim, color="#8a8984", lw=0.8)
        ax.set_xlabel(f"requested {name} offset (mm)")
        ax.set_ylabel("achieved after settling (mm)")
    err = np.abs(cal - ach).max(axis=1)
    noise = np.array([r["observation_error"]["noise_std_m"] > 0 or any(r["observation_error"]["bias_xyz_m"]) for r in rows])
    axes[2].hist([err[~noise], err[noise]], bins=40, color=["#2a78d6", "#eb6834"], label=["no sensor error", "biased/noisy sensor"],
                 stacked=True, edgecolor="#fcfcfb", lw=0.4)
    axes[2].set_xlabel("calibration error, max axis (mm)")
    axes[2].set_ylabel("cases (calibrated geometry, final suite)")
    axes[2].legend(fontsize=6.5)
    fig.tight_layout()
    save(fig, out)


def learning_curves(train, out):
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.1))
    for f in LEARNED:
        logs = []
        for d in sorted(train.glob(f"{f}_s*")):
            p = d / "train_log.jsonl"
            if p.exists():
                logs.append([json.loads(l) for l in p.read_text().splitlines() if l.strip()])
        if not logs:
            continue
        n = min(len(l) for l in logs)
        win = 10
        t = np.array([r["transitions"] for r in logs[0][:n]]) / 1e6
        succ = np.array([[r["train_success"] / max(1, r["episodes"]) for r in l[:n]] for l in logs])
        std = np.array([[np.mean(r["action_std"]) for r in l[:n]] for l in logs])
        sm = lambda a: np.convolve(a, np.ones(win) / win, mode="valid")  # noqa: E731
        axes[0].plot(t[win - 1:], 100 * sm(succ.mean(0)), color=COLOR[f], lw=1.5, label=LABEL[f])
        axes[1].plot(t, std.mean(0), color=COLOR[f], lw=1.5, label=LABEL[f])
    axes[0].set_ylabel("training success (%, mean of 5 seeds)")
    axes[1].set_ylabel("policy action std (normalized)")
    for ax in axes:
        ax.set_xlabel("transitions (millions)")
        for xv in (2, 4, 6, 8, 10):
            ax.axvline(xv, color="#e4e3df", lw=0.8, zorder=0)
    axes[1].legend(fontsize=6.5)
    fig.tight_layout()
    save(fig, out)


def traces(runs, out_dir):
    out = []
    tdir = runs / "traces6"
    if not tdir.exists():
        return out
    for case in ("v4-final-grasp_15mm-0000", "v4-final-mixed_id-0000"):
        fig, axes = plt.subplots(1, 2, figsize=(10, 2.8), sharey=True)
        for ax, ent in zip(axes, ("geometry_fixed", "geometry_calibrated")):
            p = tdir / ent / "traces" / f"{ent}.json"
            if not p.exists():
                continue
            rows = [r for r in json.loads(p.read_text()).get(case, []) if r["mode_scored"]]
            if not rows:
                continue
            t = np.array([r["t"] for r in rows])
            err = (np.array([r["controller_obj_pos"] for r in rows]) - np.array([r["obj_pos"] for r in rows])) * 1000
            for k, (ax_name, col) in enumerate((("x", "#2a78d6"), ("y", "#1baf7a"), ("z", "#eb6834"))):
                ax.plot(t, err[:, k], color=col, lw=1.2, label=f"{ax_name} estimate error")
            rel = [r["t"] for r in rows if r["released"]]
            if rel:
                ax.axvline(rel[0], color="#8a8984", lw=0.8, ls="--")
            ax.set_title(f"{LABEL[ent]} — {case}", loc="left", fontsize=8)
            ax.set_xlabel("episode time (s); dashed: giver release")
        axes[0].set_ylabel("controller estimate − true (mm)")
        axes[1].legend(fontsize=6.5)
        fig.tight_layout()
        p = out_dir / f"trace_{case}.png"
        save(fig, p)
        out.append(p.name)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--summary", default=str(ROOT / "results/v4/summary"))
    ap.add_argument("--runs", required=True)
    ap.add_argument("--index", default=str(ROOT / "configs/v4/final_matrix_index.json"))
    ap.add_argument("--train", default=None, help="formal train dir with train_log.jsonl (default <runs>/train)")
    ap.add_argument("--output", default=str(ROOT / "results/v4/figures"))
    a = ap.parse_args()
    S, R, O = Path(a.summary), Path(a.runs), Path(a.output)
    O.mkdir(parents=True, exist_ok=True)
    summary = json.loads((S / "family_condition_summary.json").read_text())
    eff = json.loads((S / "paired_effects.json").read_text())
    index = json.loads(Path(a.index).read_text())
    severity(summary, "selected", O / "severity_selected.png")
    severity(summary, "final", O / "severity_final.png")
    effects(eff, O / "paired_effects.png")
    failures(summary, O / "failure_breakdown.png")
    grasp_offsets(R, index, O / "grasp_offsets.png")
    train = Path(a.train) if a.train else R / "train"
    if train.exists():
        learning_curves(train, O / "learning_curves.png")
    t = traces(R, O)
    print(sorted(p.name for p in O.glob("*.png")), t)


if __name__ == "__main__":
    main()
