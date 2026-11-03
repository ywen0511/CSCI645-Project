#!/usr/bin/env python3
"""Validate counts and regenerate every reported metric/figure from raw episode records.

Usage:
    python scripts/analyze.py --run-index results/run_index.json --output results/summary

Inputs (paths in the run index are relative to the index file):
    final_eval:   list of {run_id, method, training_seed, file}   (raw final-evaluation JSONL)
    validation:   list of {run_id, method, training_seed, files: [...]}  (one JSONL per candidate checkpoint)
    training:     list of {run_id, method, training_seed, train_log, selection?}
    protocol:     frozen protocol JSON; suites: {final: path, validation: path}

Outputs: counts.csv, metrics_per_run.csv, metrics_per_method.csv, comparisons.csv, failure_breakdown.csv,
selection.json, learning_curves.csv, summary.json, tables.md, figures/*.png|pdf.
Requires numpy and matplotlib only (no simulator).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from csci645_handover.core.stats import paired_bootstrap_diff, wilson  # noqa: E402

METHOD_ORDER = ["nominal", "geometry", "residual", "combined", "combined_no_phase"]
LEARNED = {"residual", "combined", "combined_no_phase"}
PRIMARY = [("combined", "nominal"), ("combined", "geometry"), ("combined", "residual"), ("combined", "combined_no_phase")]
DESCRIPTIVE = [("geometry", "nominal"), ("residual", "nominal")]  # reported, not among the four primary comparisons
REASONS = ["success", "drop", "release_timeout", "prohibited_collision", "episode_timeout", "infrastructure_error",
           "invalid_reset"]


def read_jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    keys = list(rows[0].keys())
    for r in rows[1:]:
        keys += [k for k in r if k not in keys]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def episode_metrics(rs: list[dict]) -> dict:
    valid = [r for r in rs if r["reset_valid"] and r["terminal_reason"] != "infrastructure_error"]
    n = len(valid)
    k = sum(r["success"] for r in valid)
    lo, hi = wilson(k, n)
    succ = [r for r in valid if r["success"]]
    delays = [r["release_delay_s"] for r in valid if r.get("release_delay_s") is not None]
    return {
        "scheduled": len(rs), "valid": n,
        "invalid_resets": sum(1 for r in rs if not r["reset_valid"]),
        "infra_errors": sum(1 for r in rs if r["terminal_reason"] == "infrastructure_error"),
        "successes": k, "success_rate": k / n if n else None, "success_ci_low": lo, "success_ci_high": hi,
        "drops": sum(r["drop"] for r in valid), "drop_rate": sum(r["drop"] for r in valid) / n if n else None,
        "release_timeouts": sum(r["terminal_reason"] == "release_timeout" for r in valid),
        "episode_timeouts": sum(r["terminal_reason"] == "episode_timeout" for r in valid),
        "terminal_collisions": sum(r["terminal_reason"] == "prohibited_collision" for r in valid),
        "collision_episode_rate": sum(r["collision"] for r in valid) / n if n else None,
        "collision_events": sum(r["collision_count"] for r in valid),
        "completion_time_mean_s": mean([r["completion_time_s"] for r in succ]),
        "completion_time_median_s": statistics.median([r["completion_time_s"] for r in succ]) if succ else None,
        "completion_n": len(succ),
        "release_delay_mean_s": mean(delays),
        "flag_misaligned_rate": sum(r["flag_misaligned_at_grasp"] for r in valid) / n if n else None,
        "flag_premature_rate": sum(r["flag_premature_release"] for r in valid) / n if n else None,
        "flag_conflict_rate": sum(r["flag_conflicting_motion"] for r in valid) / n if n else None,
        "geometry_align_saturation_mean": mean([r.get("geometry_align_saturation_frac") for r in valid]),
        "residual_abs_mean_m": mean([r.get("residual_abs_mean_m") for r in valid]),
        "exec_minus_candidate_mean_m": mean([r.get("exec_minus_candidate_mean_m") for r in valid]),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-index", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--n-boot", type=int, default=10000)
    ap.add_argument("--no-figures", action="store_true")
    a = ap.parse_args()
    idx_path = Path(a.run_index)
    base = idx_path.parent
    idx = json.loads(idx_path.read_text())
    out = Path(a.output)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    protocol = json.loads((base / idx["protocol"]).read_text())
    conditions = [c["id"] for c in protocol["evaluation"]["conditions"]]
    per_cond = protocol["evaluation"]["episodes_per_condition"]
    final_cases = read_jsonl(base / idx["suites"]["final"])
    case_ids = {c: [x["case_id"] for x in final_cases if x["condition"] == c] for c in conditions}
    errors: list[str] = []

    # ---------------- final evaluation: load, reconcile ----------------
    runs = []
    for e in idx.get("final_eval", []):
        rs = read_jsonl(base / e["file"])
        ids = [r["case_id"] for r in rs]
        dup = [k for k, v in Counter(ids).items() if v > 1]
        if dup:
            errors.append(f"{e['run_id']}: {len(dup)} duplicate case records")
        bad_run = {r.get("run_id") for r in rs} - {e["run_id"]}
        if bad_run:
            errors.append(f"{e['run_id']}: foreign run IDs {bad_run}")
        runs.append({**e, "records": {r["case_id"]: r for r in rs}})
    counts = []
    for run in runs:
        for c in conditions:
            got = [run["records"][i] for i in case_ids[c] if i in run["records"]]
            row = {"run_id": run["run_id"], "method": run["method"], "training_seed": run.get("training_seed"),
                   "condition": c, "scheduled": per_cond, "recorded": len(got),
                   "missing": per_cond - len(got),
                   "invalid_resets": sum(1 for r in got if not r["reset_valid"]),
                   "infra_errors": sum(1 for r in got if r["terminal_reason"] == "infrastructure_error")}
            row["valid"] = row["recorded"] - row["invalid_resets"] - row["infra_errors"]
            if row["missing"]:
                errors.append(f"{run['run_id']}/{c}: {row['missing']} scheduled cases missing")
            counts.append(row)
    write_csv(out / "counts.csv", counts)

    per_run = []
    for run in runs:
        for c in conditions + ["ALL_IN_RANGE", "ALL_STRESS"]:
            if c == "ALL_IN_RANGE":
                sel = [x for x in conditions if "stress" not in x]
            elif c == "ALL_STRESS":
                sel = [x for x in conditions if "stress" in x]
            else:
                sel = [c]
            rs = [run["records"][i] for s in sel for i in case_ids[s] if i in run["records"]]
            per_run.append({"run_id": run["run_id"], "method": run["method"], "training_seed": run.get("training_seed"),
                            "condition": c, **episode_metrics(rs)})
    write_csv(out / "metrics_per_run.csv", per_run)

    per_method = []
    for m in METHOD_ORDER:
        for c in conditions + ["ALL_IN_RANGE", "ALL_STRESS"]:
            rows = [r for r in per_run if r["method"] == m and r["condition"] == c]
            if not rows:
                continue
            sr = [r["success_rate"] for r in rows if r["success_rate"] is not None]
            dr = [r["drop_rate"] for r in rows if r["drop_rate"] is not None]
            per_method.append({
                "method": m, "condition": c, "n_runs": len(rows),
                "success_mean": mean(sr), "success_sd": statistics.stdev(sr) if len(sr) > 1 else None,
                "success_per_seed": ";".join(f"{r['training_seed']}:{r['success_rate']:.3f}" for r in rows if r["success_rate"] is not None),
                "drop_mean": mean(dr), "drop_sd": statistics.stdev(dr) if len(dr) > 1 else None,
                "successes_total": sum(r["successes"] for r in rows), "valid_total": sum(r["valid"] for r in rows),
                "release_timeout_total": sum(r["release_timeouts"] for r in rows),
                "collision_episode_rate_mean": mean([r["collision_episode_rate"] for r in rows]),
                "completion_time_mean_s": mean([r["completion_time_mean_s"] for r in rows]),
                "completion_n_total": sum(r["completion_n"] for r in rows),
            })
    write_csv(out / "metrics_per_method.csv", per_method)

    # ---------------- paired comparisons ----------------
    def matrix(method, cond_list):
        rows = []
        ids = [i for c in cond_list for i in case_ids[c]]
        for run in sorted([r for r in runs if r["method"] == method], key=lambda r: r.get("training_seed") or 0):
            row = []
            for i in ids:
                rec = run["records"].get(i)
                row.append(float(rec["success"]) if rec and rec["reset_valid"] and rec["terminal_reason"] != "infrastructure_error" else math.nan)
            rows.append(row)
        return rows, ids

    import numpy as np

    comps = []
    for x, y in PRIMARY + DESCRIPTIVE:
        for c in conditions + ["ALL_IN_RANGE", "ALL_STRESS"]:
            sel = ([c] if c in conditions else [k for k in conditions if ("stress" in k) == (c == "ALL_STRESS")])
            ax, _ = matrix(x, sel)
            bx, _ = matrix(y, sel)
            if not ax or not bx:
                continue
            A, B = np.array(ax), np.array(bx)
            keep = ~(np.isnan(A).any(0) | np.isnan(B).any(0))  # drop cases invalid for either method
            res = paired_bootstrap_diff(A[:, keep], B[:, keep], n_boot=a.n_boot, seed=645)
            comps.append({"a": x, "b": y, "primary": (x, y) in PRIMARY, "condition": c,
                          "excluded_cases": int((~keep).sum()), **res})
    write_csv(out / "comparisons.csv", comps)

    # ---------------- failure breakdown ----------------
    fb = []
    for run in runs:
        for c in conditions:
            rs = [run["records"][i] for i in case_ids[c] if i in run["records"]]
            cnt = Counter(r["terminal_reason"] for r in rs)
            fb.append({"run_id": run["run_id"], "method": run["method"], "training_seed": run.get("training_seed"),
                       "condition": c, **{k: cnt.get(k, 0) for k in REASONS},
                       "flag_misaligned": sum(r["flag_misaligned_at_grasp"] for r in rs),
                       "flag_premature": sum(r["flag_premature_release"] for r in rs),
                       "flag_conflict": sum(r["flag_conflicting_motion"] for r in rs)})
    write_csv(out / "failure_breakdown.csv", fb)

    # ---------------- validation, selection, learning curves ----------------
    curves, selection = [], {}
    for v in idx.get("validation", []):
        cands = []
        for f in v["files"]:
            rs = read_jsonl(base / f)
            if not rs:
                errors.append(f"{v['run_id']}: empty validation file {f}")
                continue
            met = episode_metrics(rs)
            trans = rs[0].get("checkpoint_transitions")
            cands.append({"run_id": v["run_id"], "method": v["method"], "training_seed": v["training_seed"],
                          "checkpoint": rs[0].get("checkpoint"), "checkpoint_sha256": rs[0].get("checkpoint_sha256"),
                          "transitions": trans, "success_rate": met["success_rate"], "drop_rate": met["drop_rate"],
                          "valid": met["valid"], "scheduled": met["scheduled"]})
        cands.sort(key=lambda r: r["transitions"])
        curves += cands
        if cands:
            best = sorted(cands, key=lambda r: (-(r["success_rate"] or 0), r["drop_rate"] or 0, r["transitions"]))[0]
            selection[v["run_id"]] = {"selected": best, "candidates": cands,
                                      "rule": protocol["training"]["checkpoint_selection"]}
    write_csv(out / "learning_curves.csv", curves)
    (out / "selection.json").write_text(json.dumps(selection, indent=2))
    train_curves = []
    for t in idx.get("training", []):
        for row in read_jsonl(base / t["train_log"]):
            train_curves.append({"run_id": t["run_id"], "method": t["method"], "training_seed": t["training_seed"],
                                 "transitions": row["transitions"], "mean_step_reward": row["mean_step_reward"],
                                 "fps": row["fps"], "episodes": row["episodes"],
                                 "train_success": row.get("train_success"), "train_drop": row.get("train_drop")})
    write_csv(out / "training_curves.csv", train_curves)

    summary = {"errors": errors, "n_final_runs": len(runs),
               "final_records": sum(len(r["records"]) for r in runs),
               "expected_final_records": len(runs) * per_cond * len(conditions),
               "selection": {k: {kk: v["selected"][kk] for kk in ("checkpoint", "transitions", "success_rate", "drop_rate")}
                             for k, v in selection.items()}}
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    write_tables(out, per_method, comps, counts, conditions)
    if not a.no_figures:
        make_figures(out, per_run, per_method, curves, train_curves, fb, conditions)
    print(json.dumps(summary, indent=2))
    if errors:
        print("COUNT RECONCILIATION ERRORS:\n- " + "\n- ".join(errors), file=sys.stderr)
        return 2
    return 0


def fmt(x, pct=True):
    if x is None:
        return "n/a"
    return f"{100*x:.1f}" if pct else f"{x:.2f}"


def write_tables(out, per_method, comps, counts, conditions):
    lines = ["# Generated tables (do not edit; regenerate with scripts/analyze.py)", ""]
    lines += ["## Success rate (%) by method and condition (mean over training seeds; sd in parentheses)", ""]
    lines.append("| condition | " + " | ".join(METHOD_ORDER) + " |")
    lines.append("|---|" + "---|" * len(METHOD_ORDER))
    for c in conditions + ["ALL_IN_RANGE", "ALL_STRESS"]:
        cells = []
        for m in METHOD_ORDER:
            r = next((x for x in per_method if x["method"] == m and x["condition"] == c), None)
            if r is None:
                cells.append("-")
            else:
                sd = f" ({fmt(r['success_sd'])})" if r["success_sd"] is not None else ""
                cells.append(f"{fmt(r['success_mean'])}{sd}")
        lines.append(f"| {c} | " + " | ".join(cells) + " |")
    lines += ["", "## Drop rate (%)", "", "| condition | " + " | ".join(METHOD_ORDER) + " |",
              "|---|" + "---|" * len(METHOD_ORDER)]
    for c in conditions:
        cells = []
        for m in METHOD_ORDER:
            r = next((x for x in per_method if x["method"] == m and x["condition"] == c), None)
            cells.append("-" if r is None else fmt(r["drop_mean"]))
        lines.append(f"| {c} | " + " | ".join(cells) + " |")
    lines += ["", "## Paired differences in success rate (percentage points, 95% bootstrap CI)", "",
              "| comparison | condition | diff | CI |", "|---|---|---|---|"]
    for r in comps:
        lines.append(f"| {r['a']} - {r['b']} | {r['condition']} | {100*r['diff']:+.1f} | "
                     f"[{100*r['ci_low']:+.1f}, {100*r['ci_high']:+.1f}] |")
    tot = Counter()
    for r in counts:
        tot["scheduled"] += r["scheduled"]
        tot["recorded"] += r["recorded"]
        tot["invalid"] += r["invalid_resets"]
        tot["infra"] += r["infra_errors"]
    lines += ["", f"Count reconciliation: scheduled {tot['scheduled']}, recorded {tot['recorded']}, "
              f"invalid resets {tot['invalid']}, infrastructure errors {tot['infra']}.", ""]
    (out / "tables.md").write_text("\n".join(lines))


def make_figures(out, per_run, per_method, curves, train_curves, fb, conditions):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    colors = {"nominal": "#7f7f7f", "geometry": "#1f77b4", "residual": "#ff7f0e", "combined": "#2ca02c",
              "combined_no_phase": "#9467bd"}
    # 1. success by condition
    fig, ax = plt.subplots(figsize=(12, 4.2))
    w = 0.16
    x = np.arange(len(conditions))
    for j, m in enumerate(METHOD_ORDER):
        ys, lo, hi, pts = [], [], [], []
        for c in conditions:
            r = next((q for q in per_method if q["method"] == m and q["condition"] == c), None)
            ys.append(100 * (r["success_mean"] or 0) if r else np.nan)
            runs = [q for q in per_run if q["method"] == m and q["condition"] == c]
            pts.append([100 * q["success_rate"] for q in runs if q["success_rate"] is not None])
            if len(runs) == 1:
                lo.append(100 * (runs[0]["success_ci_low"] or 0))
                hi.append(100 * (runs[0]["success_ci_high"] or 0))
            else:
                lo.append(np.nan)
                hi.append(np.nan)
        pos = x + (j - 2) * w
        ax.bar(pos, ys, w, color=colors[m], label=m, alpha=0.85)
        for p, y0, l0, h0, pp in zip(pos, ys, lo, hi, pts):
            if not np.isnan(l0):
                ax.errorbar(p, y0, yerr=[[y0 - l0], [h0 - y0]], color="k", lw=0.8, capsize=2)
            if len(pp) > 1:
                ax.scatter([p] * len(pp), pp, s=8, color="k", zorder=3)
    ax.set_xticks(x, conditions, rotation=25, ha="right")
    ax.set_ylabel("success rate (%)")
    ax.set_ylim(0, 105)
    ax.legend(ncol=5, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.28), frameon=False)
    ax.set_title("Held-out success by condition (bars: mean; dots: training seeds; whiskers: Wilson 95% CI)")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(out / "figures" / f"success_by_condition.{ext}", dpi=160)
    plt.close(fig)
    # 2. learning curves (validation)
    if curves:
        fig, axs = plt.subplots(1, 2, figsize=(11, 3.8))
        for m in sorted({c["method"] for c in curves}, key=METHOD_ORDER.index):
            seeds = sorted({c["training_seed"] for c in curves if c["method"] == m})
            allx = sorted({c["transitions"] for c in curves if c["method"] == m})
            for k, key in enumerate(("success_rate", "drop_rate")):
                ys_all = []
                for s in seeds:
                    pts = sorted([c for c in curves if c["method"] == m and c["training_seed"] == s], key=lambda c: c["transitions"])
                    axs[k].plot([p["transitions"] / 1e6 for p in pts], [100 * (p[key] or 0) for p in pts],
                                color=colors[m], alpha=0.35, lw=1)
                    ys_all.append({p["transitions"]: p[key] for p in pts})
                meanc = [100 * np.mean([y[t] for y in ys_all if t in y]) for t in allx]
                axs[k].plot([t / 1e6 for t in allx], meanc, color=colors[m], lw=2.2, label=m)
        axs[0].set_title("validation success (%)")
        axs[1].set_title("validation drop rate (%)")
        for axx in axs:
            axx.set_xlabel("environment transitions (millions)")
            axx.grid(alpha=0.3)
        axs[0].legend(fontsize=8)
        fig.tight_layout()
        for ext in ("png", "pdf"):
            fig.savefig(out / "figures" / f"learning_curves.{ext}", dpi=160)
        plt.close(fig)
    # 3. training reward curves
    if train_curves:
        fig, ax = plt.subplots(figsize=(6.5, 3.8))
        for rid in sorted({t["run_id"] for t in train_curves}):
            pts = [t for t in train_curves if t["run_id"] == rid]
            ax.plot([p["transitions"] / 1e6 for p in pts], [p["mean_step_reward"] for p in pts],
                    color=colors[pts[0]["method"]], alpha=0.6, lw=1, label=rid)
        ax.set_xlabel("environment transitions (millions)")
        ax.set_ylabel("mean per-step training reward")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=6, ncol=3)
        fig.tight_layout()
        for ext in ("png", "pdf"):
            fig.savefig(out / "figures" / f"training_reward.{ext}", dpi=160)
        plt.close(fig)
    # 4. failure breakdown (aggregated over seeds and all conditions)
    fig, ax = plt.subplots(figsize=(8, 3.8))
    bottom = np.zeros(len(METHOD_ORDER))
    rc = {"success": "#2ca02c", "drop": "#d62728", "release_timeout": "#ff7f0e", "prohibited_collision": "#8c564b",
          "episode_timeout": "#7f7f7f", "infrastructure_error": "#000000", "invalid_reset": "#bcbd22"}
    for reason in REASONS:
        vals = []
        for m in METHOD_ORDER:
            rows = [r for r in fb if r["method"] == m]
            tot = sum(sum(r[k] for k in REASONS) for r in rows)
            vals.append(100 * sum(r[reason] for r in rows) / tot if tot else 0)
        ax.bar(METHOD_ORDER, vals, bottom=bottom, color=rc[reason], label=reason)
        bottom += np.array(vals)
    ax.set_ylabel("% of episodes (all conditions, all seeds)")
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(out / "figures" / f"terminal_reasons.{ext}", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())
