#!/usr/bin/env python3
"""Mechanism analysis of the learned residuals (CPU; numpy + matplotlib).

    python3 scripts/v3_mechanisms.py --index configs/v3/final_matrix_index.json --root <runs root> \
        --output results/v3/mechanisms

Per learned family/seed (selected checkpoints), on all non-clean final cases: least-squares fit of the
episode-mean commanded residual (per axis) on [1, true physical offset, sensor bias] -> intercept (constant
insertion offset), slope on truth (state-dependent correction) and slope on observed error (following the
corrupted measurement), with R^2. Also residual magnitude, geometry alignment saturation, workspace clipping
(residual authority), and the paired success/failure comparison against geometry_common on identical cases.
Writes mechanisms.json, residual_fits.csv and figures (residual vs truth/observed error, by family).
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--index", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--output", default="results/v3/mechanisms")
    a = ap.parse_args()
    idx = json.loads(Path(a.index).read_text())
    root, out = Path(a.root), Path(a.output)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    load = lambda e: [json.loads(l) for l in (root / e["records"]).read_text().splitlines() if l.strip()]  # noqa: E731
    base = next(e for e in idx["entries"] if e["family"] == "geometry_common")
    G = {r["case_id"]: r for r in load(base)}
    fits, summary = [], {}
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    learned = [e for e in idx["entries"] if e["role"] == "selected"]
    fams = sorted({e["family"] for e in learned})
    fig, axes = plt.subplots(2, len(fams), figsize=(3.2 * len(fams), 6), sharey="row")
    for j, fam in enumerate(fams):
        rows_all = []
        for e in [x for x in learned if x["family"] == fam]:
            rows = [r for r in load(e) if r["condition"] != "clean"]
            rows_all += rows
            res = np.array([r["residual_mean_xyz_m"] for r in rows]) * 1000
            tru = np.array([r["realized_offset_xyz_m"] for r in rows]) * 1000
            bias = np.array([r["observation_error"]["bias_xyz_m"] for r in rows]) * 1000
            for k, ax_name in enumerate("xyz"):
                X = np.column_stack([np.ones(len(rows)), tru[:, k], bias[:, k]])
                coef, *_ = np.linalg.lstsq(X, res[:, k], rcond=None)
                pred = X @ coef
                ss = ((res[:, k] - res[:, k].mean()) ** 2).sum()
                r2 = 1 - ((res[:, k] - pred) ** 2).sum() / ss if ss > 0 else None
                fits.append({"family": fam, "seed": e["seed"], "axis": ax_name, "intercept_mm": coef[0],
                             "slope_on_true_offset": coef[1], "slope_on_sensor_bias": coef[2], "r2": r2,
                             "residual_sd_mm": float(res[:, k].std()), "cases": len(rows)})
            paired = [(G[r["case_id"]]["success"], r["success"]) for r in rows if r["case_id"] in G]
            summary.setdefault(fam, []).append({
                "seed": e["seed"],
                "residual_abs_mean_mm": 1000 * float(np.mean([r["residual_abs_mean_m"] for r in rows])),
                "residual_abs_max_mm": 1000 * float(np.max([r["residual_abs_max_m"] for r in rows])),
                "align_saturation_frac": float(np.mean([r["geometry_align_saturation_frac"] for r in rows])),
                "workspace_clip_mean_mm": 1000 * float(np.mean([r["workspace_clip_mean_m"] for r in rows])),
                "paired_vs_geometry_common": {"both_success": sum(g and p for g, p in paired),
                                              "only_geometry": sum(g and not p for g, p in paired),
                                              "only_policy": sum(p and not g for g, p in paired),
                                              "both_fail": sum((not g) and (not p) for g, p in paired)}})
        res = np.array([r["residual_mean_xyz_m"][0] for r in rows_all]) * 1000
        tru = np.array([r["realized_offset_xyz_m"][0] for r in rows_all]) * 1000
        obs = np.array([r["observation_error"]["bias_xyz_m"][0] for r in rows_all]) * 1000
        axes[0, j].scatter(tru, res, s=2, alpha=0.3)
        axes[0, j].set_title(fam.replace("_", "\n"), fontsize=8)
        axes[1, j].scatter(obs, res, s=2, alpha=0.3, color="#d62728")
        axes[1, j].set_xlabel("x: sensor bias [mm]", fontsize=8)
        axes[0, j].set_xlabel("x: true object offset [mm]", fontsize=8)
    axes[0, 0].set_ylabel("episode-mean residual x [mm]")
    axes[1, 0].set_ylabel("episode-mean residual x [mm]")
    fig.suptitle("Commanded residual (x, selected checkpoints, all seeds, non-clean final cases) vs true offset and sensor bias", fontsize=9)
    fig.tight_layout()
    fig.savefig(out / "figures" / "residual_vs_error.png", dpi=150)
    plt.close(fig)
    with open(out / "residual_fits.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(fits[0]))
        w.writeheader()
        for r in fits:
            w.writerow({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in r.items()})
    (out / "mechanisms.json").write_text(json.dumps({"per_seed": summary, "fits": fits,
                                                     "method": "OLS of episode-mean residual on [1, true offset, sensor bias] per axis"},
                                                    indent=1, default=float) + "\n")
    print(json.dumps({f: [round(s["residual_abs_mean_mm"], 2) for s in v] for f, v in summary.items()}))


if __name__ == "__main__":
    main()
