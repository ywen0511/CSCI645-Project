#!/usr/bin/env python3
"""Plot per-step traces of one case for several controllers (signed residual, targets, forces, timers).

    python3 scripts/v2_plot_traces.py --case v2dev-position_stress-0000 \
        --trace results/v2/raw/dev/controls/traces/geometry_zero.json \
        --trace results/v2/raw/dev/learned/traces/combined_final_s11.json --output fig.png

Panels: signed residual x/y/z [mm]; executed minus nominal target x/y/z [mm] (includes geometry and clamps);
alignment correction dashed; grasp error [mm]; receiver/giver finger forces [N] and table force;
independent-hold timer [s] with release request/command marks. Time axis is the scored-episode clock.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", required=True)
    ap.add_argument("--trace", action="append", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axs = plt.subplots(3, 3, figsize=(13, 8.5), sharex=True)
    for tp in a.trace:
        tr = json.loads(Path(tp).read_text())
        rows = [r for r in tr.get(a.case, []) if r.get("mode_scored", r.get("mode") == 1) or r.get("reason")]
        if not rows:
            continue
        lab = Path(tp).stem
        t = np.array([r["t"] for r in rows])
        res = np.array([r["residual"] for r in rows]) * 1000
        dexec = (np.array([r["p_exec"] for r in rows]) - np.array([r["p_nom"] for r in rows])) * 1000
        al = np.array([r["align_corr"] for r in rows]) * 1000
        for i in range(3):
            ln, = axs[0, i].plot(t, res[:, i], label=lab)
            axs[1, i].plot(t, dexec[:, i], color=ln.get_color(), label=lab)
            axs[1, i].plot(t, al[:, i], color=ln.get_color(), ls="--", lw=0.8)
        axs[2, 0].plot(t, [1000 * r["grasp_error"] for r in rows], label=lab)
        rf = np.array([r["recv_force"] for r in rows]).min(1)
        gf = np.array([r["giver_force"] for r in rows]).min(1)
        l, = axs[2, 1].plot(t, rf, label=f"{lab} recv")
        axs[2, 1].plot(t, gf, ls="--", color=l.get_color(), label=f"{lab} giver")
        axs[2, 2].plot(t, [r["hold_timer"] for r in rows], color=l.get_color(), label=lab)
        rc = rows[-1]["release_cmd_time"]
        if np.isfinite(rc):
            axs[2, 2].axvline(rc, color=l.get_color(), ls=":", lw=1)
    for i, nm in enumerate("xyz"):
        axs[0, i].set_title(f"bounded residual {nm} [mm]")
        axs[1, i].set_title(f"executed - nominal {nm} [mm] (dashed: alignment)")
    axs[2, 0].set_title("grasp error [mm]"); axs[2, 1].set_title("min finger force [N] (solid recv, dashed giver)")
    axs[2, 2].set_title("independent-hold timer [s] (dotted: release command)")
    for ax in axs.flat:
        ax.grid(alpha=0.3)
    for ax in axs[2]:
        ax.set_xlabel("episode time t [s]")
    axs[0, 0].legend(fontsize=7)
    fig.suptitle(a.case)
    fig.tight_layout()
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.output, dpi=130)
    print(f"wrote {a.output}")


if __name__ == "__main__":
    main()
