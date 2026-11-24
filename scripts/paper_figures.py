#!/usr/bin/env python3
"""Figures for the conference-style final report (report/paper) and the final talk (report/talk).

Every plotted number is read from the audited value files (results/v5/report_values.json,
results/v4/report_values.json); nothing is typed in by hand.

    python scripts/paper_figures.py                       # plots -> report/paper/figures
    python scripts/paper_figures.py --videos <dir>        # also crops the Fig. 1 frames from the v5.0.0 videos
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "report/paper/figures"
V5 = json.loads((ROOT / "results/v5/report_values.json").read_text())
V4 = json.loads((ROOT / "results/v4/report_values.json").read_text())
V4 = V4.get("values", V4)

BLUE, ORANGE, AQUA, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def val(d: dict, key: str):
    return d[key]["value"]


def style(fs: float = 8.0, sans: bool = False):
    plt.rcParams.update({
        "font.family": "sans-serif" if sans else "serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"], "font.serif": ["Times New Roman", "Times", "STIXGeneral", "DejaVu Serif"],
        "mathtext.fontset": "stix", "font.size": fs, "axes.labelsize": fs, "xtick.labelsize": fs - 0.5,
        "ytick.labelsize": fs - 0.5, "legend.fontsize": fs - 0.5, "axes.edgecolor": INK2, "axes.labelcolor": INK,
        "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
        "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6, "pdf.fonttype": 42,
        "savefig.bbox": "tight", "savefig.pad_inches": 0.02})


# ---------------------------------------------------------------- Fig. 3: Study A offset sweep
def study_a(path: Path, width=3.45, height=1.75, fs=8.0):
    style(fs)
    conds = ["clean", "grasp_2mm", "grasp_5mm", "grasp_10mm", "grasp_15mm"]
    xs = [0, 2, 5, 10, 15]
    series = [("ema0p2_cal050_a25", "calibrated, 25 mm", BLUE, "-", "o"),
              ("ema0p2_cal050_a15", "calibrated, 15 mm", BLUE, "--", "s"),
              ("ema0p2_fixed_a15", "fixed, 15 mm", ORANGE, "--", "s"),
              ("ema0p2_fixed_a25", "fixed, 25 mm", ORANGE, "-", "o")]
    fig, ax = plt.subplots(figsize=(width, height))
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for cfg, label, c, ls, mk in series:
        ys = [val(V5, f"a.succ.{cfg}.{k}") for k in conds]
        ax.plot(xs, ys, ls=ls, color=c, lw=1.6, marker=mk, ms=4.2, mec="white", mew=0.8, label=label, zorder=3)
    ax.set_xticks(xs)
    ax.set_xticklabels(["0", "2", "5", "10", "15"])
    ax.set_xlabel("in-grasp offset condition (mm)")
    ax.set_ylabel("success (%)")
    ax.set_ylim(-4, 104)
    ax.set_xlim(-0.6, 15.6)
    ax.legend(loc="lower left", frameon=False, handlelength=2.2, borderaxespad=0.2)
    fig.savefig(path)
    plt.close(fig)


# ---------------------------------------------------------------- Fig. 4: paired differences under slip
def b_ci(key: str, level: str):
    return val(V5, key), val(V5, f"{key}.{level}")


def parse_pp(text: str):
    """'+3.9 pp [+0.9, +7.3]' -> (3.9, (0.9, 7.3))"""
    t = text.replace("−", "-").replace(" pp", "")
    d, rest = t.split(" [")
    lo, hi = rest.rstrip("]").split(", ")
    return float(d), (float(lo), float(hi))


def contrasts(path: Path, width=3.45, height=2.35, fs=8.0, keep=None, xlim=(-4.5, 9.5)):
    style(fs)
    rows = []  # (label, diff, (lo, hi), kind)
    d, ci = b_ci("b.B1", "ci975")
    rows.append(("B1  history $-$ feed-forward", d, ci, "primary"))
    d, ci = b_ci("b.B2", "ci975")
    rows.append(("B2  history $-$ tracking geometry", d, ci, "primary"))
    d, ci = b_ci("b.sens.slip_mixed_id.B1", "ci975")
    rows.append(("B1 without invalid slips", d, ci, "posthoc"))
    d, ci = b_ci("b.sens.slip_mixed_id.B2", "ci975")
    rows.append(("B2 without invalid slips", d, ci, "posthoc"))
    for key, label in [("b.c.repeat_minus_ff.slip_mixed_id", "repeated frame $-$ feed-forward"),
                       ("b.c.tracking_minus_calibrated.slip_mixed_id", "tracking $-$ one-shot parent"),
                       ("b.c.history_minus_calibrated_parent.slip_mixed_id", "history $-$ one-shot parent"),
                       ("b.c.ff_minus_calibrated_parent.slip_mixed_id", "feed-forward $-$ one-shot parent")]:
        d, ci = parse_pp(V5[key]["text"])
        rows.append((label, d, ci, "explore"))
    n_primary = sum(r[3] != "explore" for r in rows)
    if keep is not None:
        rows = [rows[i] for i in keep]
        n_primary = sum(r[3] != "explore" for r in rows)
    fig, ax = plt.subplots(figsize=(width, height))
    n = len(rows)
    for i, (label, d, (lo, hi), kind) in enumerate(rows):
        y = n - 1 - i
        c = {"primary": BLUE, "posthoc": BLUE, "explore": GRAY}[kind]
        face = "white" if kind == "posthoc" else c
        ax.plot([lo, hi], [y, y], color=c, lw=1.6, solid_capstyle="round", zorder=2)
        ax.plot([d], [y], marker="o", ms=5, mfc=face, mec=c, mew=1.3, zorder=3, ls="none")
        ax.text(hi + 0.35, y, f"{d:+.1f}".replace("-", "\u2212"), va="center", ha="left", fontsize=fs - 0.5, color=INK2)
    ax.axvline(0, color=INK2, lw=0.7, zorder=1)
    ax.axhline(n - n_primary - 0.5, color=GRID, lw=0.8)
    ax.set_yticks(range(n))
    ax.set_yticklabels([r[0] for r in rows][::-1])
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.set_xlim(*xlim)
    ax.set_xticks(range(-4, 10, 2))
    ax.set_xlabel("paired difference on slip_mixed_id (pp)")
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    fig.savefig(path)
    plt.close(fig)


# ---------------------------------------------------------------- Fig. 5: late-training collapse per seed
def seeds(path: Path, width=3.45, height=1.45, fs=8.0):
    style(fs)
    sel = [float(x) for x in V5["b.seeds.slip_robust_history.selected.slip_mixed_id"]["text"].split(" / ")]
    fin = [float(x) for x in V5["b.seeds.slip_robust_history.final.slip_mixed_id"]["text"].split(" / ")]
    ff = [float(x) for x in V5["b.seeds.slip_robust_ff.final.slip_mixed_id"]["text"].split(" / ")]
    names = ["111", "222", "333", "444", "555"]
    fig, ax = plt.subplots(figsize=(width, height))
    ax.grid(axis="x", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for i, (s, f, g) in enumerate(zip(sel, fin, ff)):
        y = 4 - i
        ax.plot([f, s], [y, y], color=GRID, lw=2.2, zorder=1, solid_capstyle="round")
        ax.plot([g], [y], marker="|", ms=8, mew=1.4, color=GRAY, zorder=2, ls="none")
        ax.plot([s], [y], marker="o", ms=5, color=BLUE, zorder=3, ls="none", mec="white", mew=0.6)
        ax.plot([f], [y], marker="o", ms=5, color=ORANGE, zorder=3, ls="none", mec="white", mew=0.6)
    ax.set_yticks(range(5))
    ax.set_yticklabels([f"seed {n}" for n in names][::-1])
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.set_xlim(0, 100)
    ax.set_xlabel("history policy success on slip_mixed_id (%)")
    h = [plt.Line2D([], [], marker="o", color=BLUE, ls="none", ms=5, label="selected"),
         plt.Line2D([], [], marker="o", color=ORANGE, ls="none", ms=5, label="final (10M)"),
         plt.Line2D([], [], marker="|", color=GRAY, ls="none", ms=8, mew=1.4, label="feed-forward final")]
    ax.legend(handles=h, loc="lower center", bbox_to_anchor=(0.45, 1.0), frameon=False, ncol=3, borderaxespad=0.1,
              handletextpad=0.2, columnspacing=0.9)
    fig.savefig(path)
    plt.close(fig)


# ---------------------------------------------------------------- Fig. 1 frames (from the v5.0.0 videos)
FRAMES = {"a": 20, "b": 40, "c": 58, "d": 96}  # 20 fps: 1.0 s, 2.0 s, 2.9 s, 4.8 s
VIDEO = "study_a_matched_calibration__ema0p2_cal050_a25__v5cal-heldout-grasp_15mm-0000.mp4"
CROP = (280, 118, 780, 308)


def frames(videos: Path):
    import imageio
    from PIL import Image

    reader = imageio.get_reader(str(videos / VIDEO), "ffmpeg")
    want = {i: k for k, i in FRAMES.items()}
    for i, f in enumerate(reader):
        if i in want:
            Image.fromarray(f).crop(CROP).save(OUT / f"frame_{want[i]}.png", optimize=True)


# ---------------------------------------------------------------- Fig. 4: slip mechanism (development probe)
def slip_mechanism(traces: dict, path: Path, width=3.45, height=1.55, fs=8.0):
    """Same case selection as scripts/v5_figures.py:slip_mechanism, paper styling."""
    import numpy as np

    style(fs)
    fig, axes = plt.subplots(1, 2, figsize=(width, height), sharex=True)
    colors = [BLUE, ORANGE, AQUA]
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
        c = colors[shown % 3]
        ls = "-" if 0 < tgt <= 8 else "--"
        axes[0].plot(t, d[:, 0] - d[max(0, k0 - 1), 0], lw=1.4, color=c, ls=ls, label=f"{tgt:+.0f} mm")
        axes[1].plot(t, d[:, 2] - d[max(0, k0 - 1), 2], lw=1.4, color=c, ls=ls)
        shown += 1
    axes[0].set_ylabel("along bar (mm)")
    axes[1].set_ylabel("vertical (mm)")
    for ax in axes:
        ax.set_xlabel("time (s)")
        ax.set_xlim(0, 2.1)
        ax.axvline(2.0, color=GRAY, lw=0.8, ls=":")
        ax.grid(axis="y", color=GRID, lw=0.6)
        ax.set_axisbelow(True)
    axes[1].axhspan(-1.5, 1.5, color=GRID, alpha=0.8, lw=0)
    axes[0].set_ylim(-10, 18)
    axes[1].set_ylim(-12, 4)
    axes[0].legend(loc="upper left", frameon=False, handlelength=1.6, borderaxespad=0.1, title="target",
                   title_fontsize=fs - 0.5)
    fig.tight_layout(w_pad=0.8)
    fig.savefig(path)
    plt.close(fig)
    return shown


# ---------------------------------------------------------------- talk figures (report/talk/figures)
def e1_bars(path: Path, width=6.0, height=3.2, fs=15.0):
    """E1 (V2) all-case success, from results/v2/summary/metrics_per_entry.csv and metrics_per_method.csv."""
    import csv

    style(fs)
    ent = {r["entry"]: r for r in csv.DictReader(open(ROOT / "results/v2/summary/metrics_per_entry.csv"))
           if r["condition_or_group"] == "all"}
    meth = {(r["method"], r["role"]): r for r in csv.DictReader(open(ROOT / "results/v2/summary/metrics_per_method.csv"))
            if r["condition_or_group"] == "all"}
    rate = lambda e: 100 * int(ent[e]["n_success"]) / int(ent[e]["scheduled"])  # noqa: E731
    rows = [("nominal", rate("nominal"), GRAY),
            ("nominal + PPO residual", 100 * float(meth[("residual", "selected")]["success_mean"]), ORANGE),
            ("geometry", rate("geometry_1p5cm"), BLUE),
            ("geometry + PPO residual", 100 * float(meth[("combined", "selected")]["success_mean"]), ORANGE),
            ("geometry + tuned constant", rate("const_geometry_1p5cm"), BLUE)]
    fig, ax = plt.subplots(figsize=(width, height))
    for i, (lab, v, c) in enumerate(rows):
        y = len(rows) - 1 - i - (0.35 if i >= 2 else 0)
        ax.barh(y, v, height=0.62, color=c, zorder=2)
        ax.text(v + 1.2, y, f"{v:.1f}%", va="center", ha="left", fontsize=fs - 1, color=INK)
        ax.text(-2, y, lab, va="center", ha="right", fontsize=fs - 1, color=INK)
    ax.set_xlim(0, 112)
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("held-out success, 2,400 cases (%)")
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.savefig(path)
    plt.close(fig)


def talk(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    global style
    serif_style = style
    style = lambda fs=8.0: serif_style(fs, sans=True)  # noqa: E731
    plt.rcParams["savefig.dpi"] = 250
    e1_bars(out / "e1_bars.png")
    study_a(out / "study_a_sweep.png", width=6.4, height=3.7, fs=15)
    contrasts(out / "slip_contrasts.png", width=7.0, height=4.3, fs=17, keep=[0, 1, 7, 5], xlim=(-4.5, 9.8))
    seeds(out / "history_seeds.png", width=6.2, height=2.8, fs=14)
    style = serif_style


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--videos", type=Path, help="extracted videos/ directory of the v5.0.0 videos.tar.gz")
    ap.add_argument("--probe-traces", type=Path,
                    help="development/probe/mechanisms_r2/traces/calibrated_M6.json from raw-development.tar.gz")
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    study_a(a.out / "study_a_sweep.pdf")
    contrasts(a.out / "slip_contrasts.pdf")
    seeds(a.out / "history_seeds.pdf")
    talk(ROOT / "report/talk/figures")
    if a.probe_traces:
        slip_mechanism(json.loads(a.probe_traces.read_text()), a.out / "slip_mechanism.pdf")
    if a.videos:
        frames(a.videos)


if __name__ == "__main__":
    main()
