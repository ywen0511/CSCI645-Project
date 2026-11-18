#!/usr/bin/env python3
"""V5 figures from generated summaries and raw records (CPU; numpy + matplotlib). Deterministic PNGs, 200 dpi.

    python3 scripts/v5_figures.py --study-a results/v5/calibration/summary.json \
        --probe-traces <runs>/probe/mechanisms_r2/traces/calibrated_M6.json \
        [--study-b results/v5/slip/analysis/summary.json --train <runs>/formal/train --selection results/v5/slip/selection] \
        --output results/v5/figures

Figures: study_a_factorial (success of the 2x2x2 configurations on four conditions), slip_mechanism (realized
in-grasp displacement vs the regulated target for probe traces), study_b_conditions (success by method and
condition, selected checkpoints; learned = mean of five seeds with the seed range), study_b_contrasts (primary and
key exploratory contrasts with 95% intervals), learning_curves (training-episode success of the 15 formal runs),
validation_curves (validation success of every candidate). Colors are fixed per entity, never by rank.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

plt.rcParams.update({"svg.hashsalt": "v5", "font.size": 8, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "axes.labelcolor": "#0b0b0b", "xtick.color": "#52514e",
                     "ytick.color": "#52514e", "axes.grid": True, "grid.color": "#e4e3df", "grid.linewidth": 0.6,
                     "legend.frameon": False, "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
COLOR = {"geometry_calibrated": "#2a78d6", "geometry_fixed": "#eb6834", "geometry_ema": "#1baf7a", "nominal": "#8a8984",
         "geometry_tracking": "#eda100", "best_constant_geometry": "#008300", "slip_robust_history": "#6250d6",
         "slip_robust_ff": "#e87ba4", "slip_robust_repeat": "#e34948"}
LABEL = {"geometry_calibrated": "one-shot calibrated geometry (V4 parent)", "geometry_fixed": "fixed-transform geometry",
         "geometry_ema": "EMA geometry", "nominal": "nominal", "geometry_tracking": "tracking geometry (= geometry_best)",
         "best_constant_geometry": "calibrated + best constant", "slip_robust_history": "learned, 4-frame history",
         "slip_robust_ff": "learned, feed-forward", "slip_robust_repeat": "learned, repeated current frame"}
BASES = ["nominal", "geometry_fixed", "geometry_ema", "geometry_calibrated", "best_constant_geometry", "geometry_tracking"]
LEARNED = ["slip_robust_ff", "slip_robust_history", "slip_robust_repeat"]


def save(fig, path):
    fig.savefig(path, dpi=200, metadata={"Software": None})
    plt.close(fig)


def study_a(summary: dict, out: Path):
    conds = ["mixed_id", "grasp_10mm", "grasp_15mm", "mixed_ood"]
    cells = {(c["config"], c["condition"]): c["success_pct"] for c in summary["cells"]}
    cfgs = list(dict.fromkeys(c["config"] for c in summary["cells"]))
    col = {"fixed": "#eb6834", "cal050": "#2a78d6"}
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    x = np.arange(len(conds))
    for k, cfg in enumerate(cfgs):
        ema, ref, bound = cfg.split("_")
        off = (k - (len(cfgs) - 1) / 2) * 0.095
        mk = "o" if bound == "a25" else "s"
        face = col[ref] if ema == "ema0p2" else "#fcfcfb"
        ax.plot(x + off, [cells[(cfg, c)] for c in conds], mk, ms=5, mfc=face, mec=col[ref], mew=1.2,
                label=f"{'calibrated' if ref == 'cal050' else 'fixed'} ref., EMA {'0.2' if ema == 'ema0p2' else '1.0'}, "
                      f"bound {bound[1:]} mm")
    ax.set_xticks(x, [c.replace("_", " ") for c in conds])
    ax.set_ylabel("success (% of 200 held-out cases)")
    ax.set_ylim(-3, 103)
    ax.set_title("Study A: the calibrated reference, not EMA or the bound, carries the gain (filled = EMA 0.2; "
                 "EMA has zero effect)", loc="left", fontsize=8)
    ax.legend(fontsize=6, ncol=2, loc="lower left")
    fig.tight_layout()
    save(fig, out / "study_a_factorial.png")


def slip_mechanism(traces: dict, out: Path):
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6), sharex=True)
    shown = 0
    for cid, rows in sorted(traces.items()):
        sc = [r for r in rows if r.get("mode_scored")]
        if not sc or not any(r.get("slip_phase", 0) for r in sc):
            continue
        sc = [r for r in sc if r["t"] <= 2.0 + 1e-9]
        t = np.array([r["t"] for r in sc])
        d = np.array([r["in_grasp_displacement"] for r in sc]) * 1000
        k0 = next(i for i, r in enumerate(sc) if r.get("slip_phase", 0) >= 1)
        tgt = sc[k0]["slip_target"][0] * 1000
        ok = 0 < tgt <= 8
        lab = f"target {tgt:+.0f} mm ({'accepted range' if ok else 'rejected range'})"
        colr = ["#2a78d6", "#eb6834", "#1baf7a", "#6250d6"][shown % 4]
        axes[0].plot(t, d[:, 0] - d[max(0, k0 - 1), 0], lw=1.3, color=colr, label=lab)
        axes[1].plot(t, d[:, 2] - d[max(0, k0 - 1), 2], lw=1.3, color=colr)
        shown += 1
    axes[0].set_ylabel("bar-axis displacement since onset (mm)")
    axes[1].set_ylabel("vertical displacement since onset (mm)")
    for ax in axes:
        ax.set_xlabel("scored time (s)")
        ax.set_xlim(0, 2.2)
        ax.axvline(2.0, color="#8a8984", lw=0.8, ls=":")
    axes[1].axhspan(-1.5, 1.5, color="#e4e3df", alpha=0.6, lw=0)
    axes[0].set_ylim(-10, 18)
    axes[1].set_ylim(-12, 4)
    axes[0].legend(fontsize=6)
    axes[0].set_title("Physical slip (development probe, mechanism M6)", loc="left", fontsize=8)
    axes[1].set_title("grey band: 1.5 mm validity tolerance; dotted: receiver grasp", loc="left", fontsize=7)
    fig.tight_layout()
    save(fig, out / "slip_mechanism.png")
    return shown


def study_b_conditions(summary: dict, out: Path):
    cells = [c for c in summary["cells"] if c["checkpoints"] in ("baseline", "selected")]
    conds = list(dict.fromkeys(c["condition"] for c in cells))
    by = {(c["method"], c["condition"]): c for c in cells}
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
    x = np.arange(len(conds))
    for ax, fams, title in ((axes[0], [b for b in BASES if (b, conds[0]) in by], "Training-free controllers"),
                            (axes[1], LEARNED, "Learned residuals (selected checkpoints, mean and range of 5 seeds)")):
        n = len(fams)
        for k, f in enumerate(fams):
            off = (k - (n - 1) / 2) * 0.13
            ax.plot(x + off, [by[(f, c)]["success_pct"] for c in conds], "o", ms=4.2, color=COLOR[f], mec="#fcfcfb",
                    mew=0.8, label=LABEL[f])
            if f in LEARNED:
                ax.vlines(x + off, [min(by[(f, c)]["per_seed_success_pct"]) for c in conds],
                          [max(by[(f, c)]["per_seed_success_pct"]) for c in conds], color=COLOR[f], lw=1.2, alpha=0.8)
        ax.set_xticks(x, [c.replace("_", " ") for c in conds], rotation=35, ha="right")
        ax.set_title(title, loc="left", fontsize=8.5)
        ax.set_ylim(-3, 103)
        ax.legend(loc="lower left", fontsize=6.3)
    axes[0].set_ylabel("success (% of scheduled cases)")
    fig.tight_layout()
    save(fig, out / "study_b_conditions.png")


def study_b_contrasts(summary: dict, out: Path):
    rows = [("B1 history − feed-forward (primary)", summary["primary"][0], "#6250d6"),
            ("B2 history − geometry_best (primary)", summary["primary"][1], "#6250d6")]
    pc = summary["primary"][0]["condition"]
    for cid, lab in (("repeat_minus_ff", "repeat − feed-forward"), ("tracking_minus_calibrated", "tracking − one-shot calibrated"),
                     ("history_minus_calibrated_parent", "history − one-shot calibrated parent"),
                     ("ff_minus_calibrated_parent", "feed-forward − one-shot calibrated parent")):
        c = next((c for c in summary["secondary_exploratory"]["contrasts"] if c["id"] == cid and c["condition"] == pc), None)
        if c:
            rows.append((f"{lab} (exploratory)", c, "#8a8984"))
    fig, ax = plt.subplots(figsize=(7.2, 0.45 * len(rows) + 0.9))
    for i, (lab, c, colr) in enumerate(rows):
        y = len(rows) - 1 - i
        ax.hlines(y, *c["ci95"], color=colr, lw=2)
        if "ci97.5" in c and "superiority_established" in c:
            ax.hlines(y, *c["ci97.5"], color=colr, lw=0.8)
        ax.plot(c["difference_pp"], y, "o", color=colr, ms=5, mec="#fcfcfb")
    ax.axvline(0, color="#52514e", lw=0.8)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows][::-1])
    ax.set_xlabel(f"difference in success on {pc} (percentage points; thick 95%, thin Bonferroni 97.5%)")
    ax.set_title("Study B contrasts (selected checkpoints; paired seed x case bootstrap)", loc="left", fontsize=8)
    fig.tight_layout()
    save(fig, out / "study_b_contrasts.png")


def learning(train: Path, out: Path):
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    for p in LEARNED:
        for k, d in enumerate(sorted(train.glob(f"{p}_s*"))):
            rows = [json.loads(x) for x in (d / "train_log.jsonl").read_text().splitlines() if x.strip()]
            tr = np.array([r["transitions"] for r in rows]) / 1e6
            s = np.array([r["train_success"] / max(1, r["episodes"]) for r in rows])
            w = 10
            sm = np.convolve(s, np.ones(w) / w, mode="valid")
            ax.plot(tr[w - 1:], 100 * sm, color=COLOR[p], lw=0.9, alpha=0.85, label=LABEL[p] if k == 0 else None)
    ax.set_xlabel("training transitions (millions)")
    ax.set_ylabel("training-episode success (%, 10-iteration mean)")
    ax.set_title("Formal training (15 runs; training episodes include slip with probability 0.5)", loc="left", fontsize=8)
    ax.legend(fontsize=6.5)
    fig.tight_layout()
    save(fig, out / "learning_curves.png")


def validation(sel_dir: Path, out: Path):
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    for p in LEARNED:
        for k, f in enumerate(sorted(sel_dir.glob(f"{p}_s*.json"))):
            rep = json.loads(f.read_text())
            cs = sorted(rep["candidates"], key=lambda c: c["transitions"])
            ax.plot([c["transitions"] / 1e6 for c in cs], [100 * c["success_rate"] for c in cs], "-o", ms=2.5, lw=0.8,
                    color=COLOR[p], alpha=0.85, label=LABEL[p] if k == 0 else None)
            s = next(c for c in cs if c["tag"] == rep["selected"])
            ax.plot(s["transitions"] / 1e6, 100 * s["success_rate"], "*", ms=8, color=COLOR[p], mec="#0b0b0b", mew=0.4)
    ax.set_xlabel("checkpoint (million transitions)")
    ax.set_ylabel("validation success (%)")
    ax.set_title("Validation of every candidate (stars: selected)", loc="left", fontsize=8)
    ax.legend(fontsize=6.5)
    fig.tight_layout()
    save(fig, out / "validation_curves.png")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--study-a", required=True)
    ap.add_argument("--probe-traces", required=True)
    ap.add_argument("--study-b", default=None)
    ap.add_argument("--train", default=None)
    ap.add_argument("--selection", default=None)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    out = Path(a.output)
    out.mkdir(parents=True, exist_ok=True)
    study_a(json.loads(Path(a.study_a).read_text()), out)
    slip_mechanism(json.loads(Path(a.probe_traces).read_text()), out)
    if a.study_b:
        s = json.loads(Path(a.study_b).read_text())
        study_b_conditions(s, out)
        study_b_contrasts(s, out)
    if a.train:
        learning(Path(a.train), out)
    if a.selection:
        validation(Path(a.selection), out)
    print(sorted(p.name for p in out.glob("*.png")))


if __name__ == "__main__":
    main()
