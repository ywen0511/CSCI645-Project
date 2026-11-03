#!/usr/bin/env python3
"""Plot per-step telemetry traces (contact forces, positions, gripper widths, release, hold timer).

Usage:
    python3 scripts/plot_trace.py --traces outputs/baseline/traces.json --output outputs/baseline/trace_plots
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--traces", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--max", type=int, default=6)
    a = ap.parse_args()
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    traces = json.loads(Path(a.traces).read_text())
    out = Path(a.output)
    out.mkdir(parents=True, exist_ok=True)
    for k, (case_id, rows) in enumerate(traces.items()):
        if k >= a.max:
            break
        settle = [r for r in rows if r["mode"] == 0]
        rows = [r for r in rows if r["mode"] != 0] or rows
        t = np.array([r["t"] for r in rows])
        g = lambda key: np.array([r[key] for r in rows])  # noqa: E731
        fig, axs = plt.subplots(5, 1, figsize=(10, 13), sharex=True)
        obj, recv, giver, pex = g("obj_pos"), g("recv_tcp"), g("giver_tcp"), g("p_exec")
        for i, ax_name in enumerate("xyz"):
            axs[0].plot(t, obj[:, i], label=f"obj {ax_name}", color=f"C{i}")
            axs[0].plot(t, recv[:, i], "--", label=f"recv tcp {ax_name}", color=f"C{i}")
            axs[0].plot(t, pex[:, i], ":", label=f"recv target {ax_name}", color=f"C{i}")
        axs[0].set_ylabel("position [m]")
        axs[0].legend(fontsize=6, ncol=3)
        gf, rf = g("giver_force"), g("recv_force")
        axs[1].plot(t, gf[:, 0], label="giver L")
        axs[1].plot(t, gf[:, 1], label="giver R")
        axs[1].plot(t, rf[:, 0], label="recv L")
        axs[1].plot(t, rf[:, 1], label="recv R")
        axs[1].plot(t, g("table_force"), label="object-table")
        axs[1].plot(t, g("collision_force"), label="prohibited (max)", alpha=0.6)
        axs[1].set_yscale("symlog", linthresh=0.5)
        axs[1].set_ylabel("normal force [N]")
        axs[1].legend(fontsize=6, ncol=3)
        axs[2].plot(t, g("giver_width"), label="giver width")
        axs[2].plot(t, g("recv_width"), label="recv width")
        axs[2].plot(t, 2 * g("finger_cmd_giver"), ":", label="giver cmd")
        axs[2].plot(t, 2 * g("finger_cmd_recv"), ":", label="recv cmd")
        axs[2].set_ylabel("gripper gap [m]")
        axs[2].legend(fontsize=6, ncol=2)
        axs[3].plot(t, g("grasp_error"), label="|grasp point - recv tcp|")
        axs[3].plot(t, g("obj_rel_speed"), label="obj speed rel. receiver")
        axs[3].plot(t, np.abs(g("residual")).max(-1), label="|residual|max")
        axs[3].plot(t, np.abs(g("align_corr")).max(-1), label="|align corr|max")
        axs[3].set_ylabel("m or m/s")
        axs[3].set_yscale("symlog", linthresh=0.005)
        axs[3].legend(fontsize=6, ncol=2)
        axs[4].plot(t, g("hold_timer"), label="independent hold [s]")
        axs[4].plot(t, g("stab_dwell"), label="stability dwell [s]")
        axs[4].plot(t, g("released").astype(float), label="released")
        axs[4].plot(t, g("phase") / 3.0, label="phase/3 (0 giver,1 both,2 recv,3 none)")
        rq = rows[0]["release_request_time"]
        for ax in axs:
            ax.axvline(rq, color="k", lw=0.6, ls="--")
            ax.grid(alpha=0.3)
        axs[4].set_xlabel("episode time [s] (dashed: release request)")
        axs[4].legend(fontsize=6, ncol=2)
        end = [r for r in rows if r["reason"]]
        fig.suptitle(f"{case_id}  settle steps={len(settle)}  end reason code={end[-1]['reason'] if end else 'n/a'}")
        fig.tight_layout()
        fig.savefig(out / f"trace_{k:02d}_{case_id}.png", dpi=110)
        plt.close(fig)
    print(f"wrote {min(len(traces), a.max)} plots to {out}")


if __name__ == "__main__":
    main()
