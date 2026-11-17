#!/usr/bin/env python3
"""CPU failure taxonomy of the published V4 final records (proposal metrics; no simulator, no GPU).

The original proposal promised success and drop rates, completion time, collisions and a failure
analysis that separates misalignment, premature release and conflicting motion during shared holding.
V1 reported these; the V4 final synthesis did not. This script recomputes them from the public
``raw-final.tar.gz`` (v4.0.0) without extracting it, for every executed final entry and condition.

python scripts/v5_failure_taxonomy.py --archive downloads/v4-review/raw-final.tar.gz

Outputs (all derived, read-only with respect to published V4 results):
  results/v5/cpu/failure_taxonomy.json   per family x role x condition counts and rates
  results/v5/cpu/failure_taxonomy.md     compact tables used by the final synthesis
  report/final/failure_modes.png         exclusive terminal reasons, four key conditions

Definitions (src/csci645_handover/core/outcomes.py):
  terminal_reason   exclusive: success | prohibited_collision | drop | episode_timeout | release_timeout | invalid_reset
  flag_misaligned_at_grasp   grasp-point error > 10 mm at the nominal grasp time
  flag_premature_release     giver released while the receiver stability proxy was false
  flag_conflicting_motion    giver-receiver TCP separation changed > 10 mm during shared holding
  The three flags are diagnostic and non-exclusive; they are reported among failed valid-reset episodes.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import tarfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_SHA = "26b27cd5f9d97f1a6dea85412ecb050aba772eb84fee6bd9a9f18038bf7cf627"
REASONS = ["success", "prohibited_collision", "drop", "episode_timeout", "release_timeout", "invalid_reset"]
FLAGS = {"misaligned": "flag_misaligned_at_grasp", "premature_release": "flag_premature_release",
         "conflicting_motion": "flag_conflicting_motion"}
KEY_CONDITIONS = ["grasp_15mm", "mixed_id", "mixed_ood", "boundary_x_minus_7"]
FAMILIES = [("nominal", "baseline", "Nominal"), ("geometry_fixed", "baseline", "Fixed geometry"),
            ("geometry_ema", "baseline", "EMA geometry"), ("geometry_calibrated", "baseline", "Calibrated geometry"),
            ("combined_robust_ff", "selected", "Robust feed-forward"),
            ("combined_robust_history", "selected", "Robust history"),
            ("combined_robust_repeat", "selected", "Repeated current frame"),
            ("residual_robust_history", "selected", "Residual-only history")]


def summarize(rows: list[dict]) -> dict:
    """Counts for one (family, role, condition) cell; ``rows`` pools every training seed."""
    n = len(rows)
    if n == 0:
        raise ValueError("empty cell")
    reasons = Counter(r["terminal_reason"] for r in rows)
    unknown = set(reasons) - set(REASONS)
    if unknown:
        raise ValueError(f"unknown terminal reason {sorted(unknown)}")
    for r in rows:
        if r["success"] != (r["terminal_reason"] == "success"):
            raise ValueError(f"{r['case_id']}: success flag disagrees with terminal reason")
        if (not r["reset_valid"]) != (r["terminal_reason"] == "invalid_reset"):
            raise ValueError(f"{r['case_id']}: reset flag disagrees with terminal reason")
    failed = [r for r in rows if r["reset_valid"] and not r["success"]]
    times = [r["completion_time_s"] for r in rows if r["success"]]
    out = {"episodes": n, "terminal_reason_counts": {k: reasons.get(k, 0) for k in REASONS},
           "terminal_reason_pct": {k: 100.0 * reasons.get(k, 0) / n for k in REASONS},
           "failed_valid_episodes": len(failed),
           "flags_among_failed_counts": {k: sum(bool(r[f]) for r in failed) for k, f in FLAGS.items()},
           "any_collision_pct": 100.0 * sum(bool(r["collision"]) for r in rows) / n,
           "any_drop_pct": 100.0 * sum(bool(r["drop"]) for r in rows) / n,
           "completion_time_s_successes": None}
    if times:
        out["completion_time_s_successes"] = {"median": statistics.median(times), "mean": statistics.fmean(times),
                                              "n": len(times)}
    return out


def read_archive(archive: Path) -> dict:
    data = archive.read_bytes()
    if hashlib.sha256(data).hexdigest() != ARCHIVE_SHA:
        raise ValueError("raw archive checksum mismatch (expected the v4.0.0 raw-final.tar.gz)")
    index = json.loads((ROOT / "configs/v4/final_matrix_index.json").read_text())
    cells: dict[tuple, list] = defaultdict(list)
    seen = set()
    with tarfile.open(archive) as tar:
        for entry in index["entries"]:
            if entry.get("alias_of"):
                continue  # declared alias of geometry_calibrated; never double counted
            path = entry["records"]
            if path in seen:
                raise ValueError(f"duplicate records path {path}")
            seen.add(path)
            raw = tar.extractfile(tar.getmember(path)).read()
            if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
                raise ValueError(f"record checksum mismatch: {path}")
            rows = [json.loads(x) for x in raw.splitlines()]
            if len(rows) != 2400:
                raise ValueError(f"{path}: expected 2400 records")
            for r in rows:
                cells[(entry["family"], entry["role"], r["condition"])].append(r)
    if len(seen) != 54:
        raise ValueError("expected 54 executed final entries")
    return cells


def build(cells: dict) -> dict:
    rows = []
    for (family, role, condition), rs in sorted(cells.items()):
        rows.append({"family": family, "role": role, "condition": condition, **summarize(rs)})
    return {"schema": 1, "source_archive_sha256": ARCHIVE_SHA,
            "scope": "Derived CPU taxonomy of v4.0.0 final records; learned rows pool five training seeds.",
            "definitions": {"terminal_reason": "exclusive, all scheduled episodes",
                            "flags": "non-exclusive diagnostics among failed valid-reset episodes",
                            "misalign_tol_m": 0.01, "conflict_tol_m": 0.01},
            "episodes": sum(r["episodes"] for r in rows), "cells": rows}


def cell(result, family, role, condition):
    return next(r for r in result["cells"] if (r["family"], r["role"], r["condition"]) == (family, role, condition))


def markdown(result) -> str:
    lines = ["# V4 failure taxonomy (derived from v4.0.0 raw final records)", "",
             "Exclusive terminal reasons as % of all scheduled episodes (learned rows: selected checkpoints, five seeds "
             "pooled). Success completion time is the median over successful episodes.", ""]
    for condition in KEY_CONDITIONS:
        lines += [f"## {condition}", "",
                  "| Controller | Success | Collision | Drop | Episode timeout | Release timeout | Invalid reset | "
                  "Median completion (s) | Failed: misaligned / premature / conflicting |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
        for family, role, label in FAMILIES:
            c = cell(result, family, role, condition)
            p = c["terminal_reason_pct"]
            t = c["completion_time_s_successes"]
            f = c["flags_among_failed_counts"]
            lines.append(f"| {label} | {p['success']:.1f} | {p['prohibited_collision']:.1f} | {p['drop']:.1f} | "
                         f"{p['episode_timeout']:.1f} | {p['release_timeout']:.1f} | {p['invalid_reset']:.1f} | "
                         f"{t['median']:.2f} | {c['failed_valid_episodes']}: {f['misaligned']} / "
                         f"{f['premature_release']} / {f['conflicting_motion']} |" if t else
                         f"| {label} | {p['success']:.1f} | ... | | | | | n/a | |")
        lines.append("")
    return "\n".join(lines)


def figure(result, path: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Reference categorical palette, fixed slot order (dataviz palette.md, light mode); text stays in ink colors.
    colors = {"prohibited_collision": "#2a78d6", "drop": "#eb6834", "episode_timeout": "#1baf7a",
              "release_timeout": "#eda100", "invalid_reset": "#e87ba4"}
    labels = {"prohibited_collision": "Prohibited collision", "drop": "Drop", "episode_timeout": "Episode timeout",
              "release_timeout": "Release timeout", "invalid_reset": "Invalid reset"}
    titles = {"grasp_15mm": "Grasp-15", "mixed_id": "Mixed ID", "mixed_ood": "Mixed OOD",
              "boundary_x_minus_7": "x = -7 mm boundary"}
    fig, axes = plt.subplots(1, 4, figsize=(10.5, 3.6), sharey=True, layout="constrained")
    ink, muted = "#0b0b0b", "#52514e"
    used = set()
    for ax, condition in zip(axes, KEY_CONDITIONS):
        for i, (family, role, _) in enumerate(FAMILIES):
            p = cell(result, family, role, condition)["terminal_reason_pct"]
            left = 0.0
            for k in colors:
                if p[k] > 0:
                    ax.barh(i, p[k], left=left, height=0.62, color=colors[k], edgecolor="white", linewidth=1.0)
                    used.add(k)
                    left += p[k]
            ax.text(left + 2, i, f"{left:.1f}", va="center", fontsize=7, color=muted)
        ax.set_title(titles[condition], loc="left", fontsize=10, color=ink)
        ax.set_xlim(0, 112)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.tick_params(colors=muted, labelsize=8)
        ax.grid(axis="x", color="#e4e3df", lw=0.6)
        ax.set_axisbelow(True)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.spines["bottom"].set_color("#c9c8c2")
    axes[0].set_yticks(range(len(FAMILIES)), [f[2] for f in FAMILIES], fontsize=8, color=ink)
    axes[0].invert_yaxis()
    fig.supxlabel("Failed episodes, % of scheduled (exclusive terminal reason; number = total failure %)",
                  fontsize=8, color=muted)
    from matplotlib.patches import Patch
    keys = [k for k in colors if k in used]  # every reason drawn in any panel, fixed slot order
    fig.legend([Patch(color=colors[k]) for k in keys], [labels[k] for k in keys],
               loc="outside upper center", ncol=len(keys), fontsize=8, frameon=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, metadata={"Software": "CSCI645 v5_failure_taxonomy.py"})
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "results/v5/cpu")
    parser.add_argument("--figure", type=Path, default=ROOT / "report/final/failure_modes.png")
    args = parser.parse_args()
    result = build(read_archive(args.archive))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "failure_taxonomy.json").write_text(json.dumps(result, indent=1) + "\n")
    (args.out_dir / "failure_taxonomy.md").write_text(markdown(result) + "\n")
    figure(result, args.figure)
    print(f"PASS: {result['episodes']} episodes in {len(result['cells'])} cells -> {args.out_dir}")


if __name__ == "__main__":
    main()
