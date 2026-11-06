#!/usr/bin/env python3
"""Stage 4 repeatability analysis and replay agreement (CPU only; numpy + matplotlib).

    python3 scripts/closeout_repeatability.py analyze --sim <work>/sim --archived <v2.0.0 x>/final/eval \
        --ledger <work>/ledger --output results/closeout/repeatability
    python3 scripts/closeout_repeatability.py agreement --archived <v2.0.0 x>/final/eval --replay <work>/sim/replay \
        --output replay_comparison.json

The analysis follows docs/closeout/REPEATABILITY_PLAN.md (frozen before collection):
* every rate uses all scheduled cases as the denominator; missing cases count as non-success and are reported;
* comparisons: combined (3 training seeds) - geometry_1p5cm and - const_geometry_1p5cm, per batch size, process
  repeat and checkpoint role, with the v2 two-level paired bootstrap (training seeds x shared cases);
* the repeat summary averages each case over the three repeats *before* resampling: repeats are never treated
  as new cases or new training seeds; batch sizes are separate sensitivity analyses;
* agreement with the archived v2.0.0 record of the same controller and case (terminal reason, success flag).
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from csci645_handover.core.stats import paired_bootstrap_diff  # noqa: E402

REASONS = ["success", "drop", "prohibited_collision", "episode_timeout", "release_timeout"]
N_BOOT = 10000


def load_dir(d: Path) -> dict[str, list[dict]]:
    out = {}
    for f in sorted(d.rglob("*.jsonl")):
        if f.name == "eval_runs.jsonl" or "_matrix" in f.parts:
            continue
        rows = [json.loads(x) for x in f.read_text().splitlines() if x.strip()]
        if rows and "case_id" in rows[0]:
            out.setdefault(rows[0]["entry_id"], []).extend(rows)
    return out


def counts(rows: list[dict], case_ids: list[str]) -> dict:
    ids = [r["case_id"] for r in rows]
    c = collections.Counter(ids)
    dup = sum(v - 1 for v in c.values() if v > 1)
    idx = {r["case_id"]: r for r in rows}
    sched = set(case_ids)
    rec = [idx[i] for i in case_ids if i in idx]
    tr = collections.Counter(r["terminal_reason"] for r in rec)
    d = {"scheduled": len(case_ids), "recorded": len(rec), "duplicates": dup,
         "missing": len(sched - set(idx)), "unexpected": len(set(idx) - sched),
         "invalid_reset": sum(not r["reset_valid"] for r in rec),
         **{f"n_{k}": tr.get(k, 0) for k in REASONS},
         "n_other_terminal": sum(v for k, v in tr.items() if k not in REASONS),
         "n_success_flag": sum(bool(r["success"]) for r in rec),
         "n_collision_flag": sum(bool(r["collision"]) for r in rec),
         "n_drop_flag": sum(bool(r["drop"]) for r in rec)}
    d["success_rate_scheduled"] = d["n_success_flag"] / len(case_ids)
    return d


def vec(rows: list[dict], case_ids: list[str], key="success") -> np.ndarray:
    idx = {r["case_id"]: r for r in rows}
    return np.array([float(bool(idx[c][key])) if c in idx else 0.0 for c in case_ids])


def agree(a_rows: list[dict], b_rows: list[dict], case_ids: list[str]) -> dict:
    A = {r["case_id"]: r for r in a_rows}
    B = {r["case_id"]: r for r in b_rows}
    both = [c for c in case_ids if c in A and c in B]
    tr = sum(A[c]["terminal_reason"] == B[c]["terminal_reason"] for c in both)
    sc = sum(bool(A[c]["success"]) == bool(B[c]["success"]) for c in both)
    flips = collections.Counter((bool(A[c]["success"]), bool(B[c]["success"])) for c in both
                                if bool(A[c]["success"]) != bool(B[c]["success"]))
    return {"compared": len(both), "terminal_reason_equal": tr, "success_equal": sc,
            "success_archived_only": flips.get((True, False), 0), "success_replay_only": flips.get((False, True), 0),
            "terminal_reason_disagree": len(both) - tr}


def cmd_agreement(a):
    arch = load_dir(Path(a.archived))
    rep = load_dir(Path(a.replay))
    rows = []
    for e, rr in sorted(rep.items()):
        ids = [r["case_id"] for r in rr]
        if e not in arch:
            raise SystemExit(f"no archived records for {e}")
        g = agree(arch[e], rr, ids)
        rows.append({"entry": e, "learned": bool(rr[0].get("checkpoint_sha256")),
                     "checkpoint_sha256_matches_archived": rr[0].get("checkpoint_sha256") == arch[e][0].get("checkpoint_sha256"),
                     **g})
    tot = {k: sum(r[k] for r in rows) for k in ("compared", "terminal_reason_equal", "success_equal",
                                                 "terminal_reason_disagree", "success_archived_only",
                                                 "success_replay_only")}
    det = [r for r in rows if not r["learned"]]
    out = {"summary": {**tot, "entries": len(rows),
                       "deterministic": {k: sum(r[k] for r in det) for k in ("compared", "terminal_reason_equal", "success_equal")},
                       "learned": {k: sum(r[k] for r in rows if r["learned"]) for k in ("compared", "terminal_reason_equal", "success_equal")},
                       "all_checkpoint_hashes_match": all(r["checkpoint_sha256_matches_archived"] for r in rows if r["learned"]),
                       "note": "observed agreement on the predeclared sample; not a population bound and not a bitwise "
                               "reproducibility claim"},
           "per_entry": rows}
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["summary"], indent=1))


def cmd_analyze(a):
    cfg = json.loads((ROOT / "configs/closeout/repeatability.json").read_text())
    man = json.loads((ROOT / "results/closeout/repeatability/run_manifest.json").read_text())
    case_ids = [json.loads(l)["case_id"] for l in (ROOT / cfg["suite"]).read_text().splitlines() if l.strip()]
    arch = load_dir(Path(a.archived))
    sim = Path(a.sim)
    out = Path(a.output)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    seeds = [11, 22, 33]
    batches, repeats = cfg["batch_sizes"], list(range(1, len(cfg["process_seeds"]) + 1))
    entries = [e["id"] for e in cfg["entries"]]

    # ---- per task ----------------------------------------------------------------------------------------
    data, per_task = {}, []
    ledger = collections.defaultdict(list)
    if a.ledger and Path(a.ledger).exists():
        for f in Path(a.ledger).glob("b*_r*_*.jsonl"):
            for l in f.read_text().splitlines():
                r = json.loads(l)
                ledger[r["task"]].append(r)
    for t in man["tasks"]:
        d = sim / t["output"]
        rows = load_dir(d).get(t["entry"], []) if d.exists() else []
        data[(t["batch_size"], t["repeat"], t["entry"])] = rows
        c = counts(rows, case_ids)
        g = agree(arch[t["entry"]], rows, case_ids)
        att = ledger.get(t["task"], [])
        per_task.append({"task": t["task"], "batch_size": t["batch_size"], "repeat": t["repeat"],
                         "process_seed": t["process_seed"], "entry": t["entry"], **c,
                         "agree_terminal_reason": g["terminal_reason_equal"], "agree_success": g["success_equal"],
                         "compared_with_archived": g["compared"], "attempts": len(att),
                         "attempt_return_codes": ";".join(str(x["rc"]) for x in att),
                         "hosts": ";".join(sorted({x.get("host", "") for x in att})),
                         "gpus": ";".join(sorted({(x.get("gpu") or ["", ""])[1] if len(x.get("gpu") or []) > 1 else "" for x in att}))})
    arch_c = {e: counts(arch[e], case_ids) for e in entries}

    # ---- comparisons ---------------------------------------------------------------------------------------
    comps = []

    def mat(get, role):
        return np.stack([get(f"combined_seed{s}__{role}") for s in seeds])

    def add(layout, rep, role, A, B, name, n_rep):
        r = paired_bootstrap_diff(A, B, n_boot=N_BOOT, seed=645)
        comps.append({"batch_size": layout, "repeat": rep, "role": role, "comparison": name,
                      "diff_pp": 100 * r["diff"], "ci_low_pp": 100 * r["ci_low"], "ci_high_pp": 100 * r["ci_high"],
                      "mean_combined": float(A.mean()), "mean_other": float(B.mean()),
                      "per_seed_combined": ";".join(f"{x:.4f}" for x in A.mean(1)),
                      "n_cases": r["n_cases"], "seeds": r["seeds_a"], "repeats_averaged": n_rep,
                      "p_two_sided_sign": r["p_two_sided_sign"]})

    others = [("combined - geometry_1p5cm", "geometry_1p5cm"), ("combined - const_geometry_1p5cm", "const_geometry_1p5cm")]
    for role in ("selected", "final"):
        A0 = mat(lambda e: vec(arch[e], case_ids), role)
        for name, o in others:
            add("archived (900, seed 0)", "v2.0.0", role, A0, vec(arch[o], case_ids)[None], name, 0)
        for b in batches:
            for rp in repeats:
                A = mat(lambda e: vec(data[(b, rp, e)], case_ids), role)
                for name, o in others:
                    add(b, rp, role, A, vec(data[(b, rp, o)], case_ids)[None], name, 1)
            Aavg = mat(lambda e: np.mean([vec(data[(b, rp, e)], case_ids) for rp in repeats], 0), role)
            for name, o in others:
                Bavg = np.mean([vec(data[(b, rp, o)], case_ids) for rp in repeats], 0)[None]
                add(b, "mean of repeats", role, Aavg, Bavg, name, len(repeats))

    # ---- interpretation (frozen rule) ----------------------------------------------------------------------
    verdict = {}
    for role in ("selected", "final"):
        for name, _ in others:
            per = [c for c in comps if c["role"] == role and c["comparison"] == name and isinstance(c["batch_size"], int)]
            reps = [c for c in per if c["repeat"] != "mean of repeats"]
            avgs = [c for c in per if c["repeat"] == "mean of repeats"]
            signs = {int(np.sign(round(c["diff_pp"], 9))) for c in reps}
            any_zero_ci = any(c["ci_low_pp"] <= 0 <= c["ci_high_pp"] for c in avgs)
            verdict[f"{role}: {name}"] = {
                "range_pp_over_repeats_and_layouts": [min(c["diff_pp"] for c in reps), max(c["diff_pp"] for c in reps)],
                "signs": sorted(signs), "repeat_averaged_ci_includes_0_in_some_layout": any_zero_ci,
                "per_layout_repeat_averaged": {str(c["batch_size"]): [c["diff_pp"], c["ci_low_pp"], c["ci_high_pp"]] for c in avgs},
                "classification": ("unresolved / sensitive to evaluation layout and process"
                                   if (len(signs) > 1 or any_zero_ci) else
                                   ("stable disadvantage under the tested settings" if signs == {-1}
                                    else "stable advantage under the tested settings"))}

    # ---- reconciliation --------------------------------------------------------------------------------------
    rec = {"scheduled": sum(p["scheduled"] for p in per_task), "recorded": sum(p["recorded"] for p in per_task),
           "missing": sum(p["missing"] for p in per_task), "duplicates": sum(p["duplicates"] for p in per_task),
           "unexpected": sum(p["unexpected"] for p in per_task), "invalid_reset": sum(p["invalid_reset"] for p in per_task),
           "tasks": len(per_task), "tasks_complete": sum(p["recorded"] == p["scheduled"] and p["missing"] == 0 for p in per_task),
           "attempts_total": sum(p["attempts"] for p in per_task),
           "tasks_with_resume": sum(p["attempts"] > 1 for p in per_task)}

    write_csv(out / "per_task.csv", per_task)
    write_csv(out / "comparisons.csv", comps)
    write_csv(out / "archived_reference.csv", [{"entry": e, **arch_c[e]} for e in entries])
    summary = {"design": "configs/closeout/repeatability.json", "plan": "docs/closeout/REPEATABILITY_PLAN.md",
               "reconciliation": rec, "verdict": verdict, "n_boot": N_BOOT, "bootstrap_seed": 645,
               "success_rate_by_entry": {e: {"archived": arch_c[e]["success_rate_scheduled"],
                                             **{f"b{b}_r{rp}": counts(data[(b, rp, e)], case_ids)["success_rate_scheduled"]
                                                for b in batches for rp in repeats}} for e in entries},
               "agreement_with_archived": {f"b{p['batch_size']}_r{p['repeat']}_{p['entry']}":
                                           [p["agree_terminal_reason"], p["agree_success"], p["compared_with_archived"]]
                                           for p in per_task}}
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    figures(out / "figures", comps, per_task, entries, batches, repeats, arch_c)
    print(json.dumps({"reconciliation": rec, "verdict": verdict}, indent=1))


def write_csv(p: Path, rows: list[dict]):
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.6f}" if isinstance(v, float) else v) for k, v in r.items()})


def figures(d: Path, comps, per_task, entries, batches, repeats, arch_c):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=False)
    for ax, (name, title) in zip(axes, [("combined - geometry_1p5cm", "combined − geometry 1.5 cm"),
                                        ("combined - const_geometry_1p5cm", "combined − geometry 1.5 cm + 10 mm constant")]):
        labels, ys, los, his, cols = [], [], [], [], []
        for role, col in (("selected", "#1f77b4"), ("final", "#d62728")):
            for c in comps:
                if c["comparison"] != name or c["role"] != role:
                    continue
                lab = ("v2.0.0" if c["repeat"] == "v2.0.0" else
                       f"b{c['batch_size']} {'avg' if c['repeat'] == 'mean of repeats' else 'r' + str(c['repeat'])}")
                labels.append(f"{role[:3]} {lab}")
                ys.append(c["diff_pp"]); los.append(c["ci_low_pp"]); his.append(c["ci_high_pp"]); cols.append(col)
        x = np.arange(len(ys))
        for i in x:
            ax.errorbar(i, ys[i], yerr=[[ys[i] - los[i]], [his[i] - ys[i]]], fmt="o", color=cols[i], capsize=2, ms=4)
        ax.axhline(0, color="k", lw=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=90, fontsize=7)
        ax.set_ylabel("success difference [pp] (95% CI)")
        ax.set_title(title, fontsize=10)
        ax.grid(axis="y", alpha=0.3)
    fig.suptitle("Repeatability: paired differences per process repeat and batch layout (blue: selected, red: final)",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(d / "repeatability_differences.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4))
    w = 0.8 / (1 + len(batches) * len(repeats))
    for j, e in enumerate(entries):
        ax.bar(j - 0.4 + w / 2, 100 * arch_c[e]["success_rate_scheduled"], w, color="k", label="v2.0.0" if j == 0 else None)
        k = 1
        for b, hue in zip(batches, ("#1f77b4", "#ff7f0e")):
            for rp in repeats:
                p = next(p for p in per_task if p["entry"] == e and p["batch_size"] == b and p["repeat"] == rp)
                ax.bar(j - 0.4 + w / 2 + k * w, 100 * p["success_rate_scheduled"], w, color=hue, alpha=0.5 + 0.15 * rp,
                       label=f"b{b} r{rp}" if j == 0 else None)
                k += 1
    ax.set_xticks(range(len(entries)))
    ax.set_xticklabels([e.replace("combined_seed", "comb s").replace("__", " ").replace("const_geometry_1p5cm", "geom+10mm")
                        .replace("geometry_1p5cm", "geometry") for e in entries], fontsize=8)
    lo = min(100 * p["success_rate_scheduled"] for p in per_task) - 2
    ax.set_ylim(max(0, lo), 100)
    ax.set_ylabel("success [% of 2,400 scheduled]")
    ax.legend(fontsize=7, ncol=7, loc="lower right")
    ax.grid(axis="y", alpha=0.3)
    ax.set_title("Success per controller: archived v2.0.0 vs three process repeats at batch 900 and 23", fontsize=10)
    fig.tight_layout()
    fig.savefig(d / "repeatability_success.png", dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("analyze")
    p.add_argument("--sim", required=True)
    p.add_argument("--archived", required=True)
    p.add_argument("--ledger", default=None)
    p.add_argument("--output", required=True)
    q = sub.add_parser("agreement")
    q.add_argument("--archived", required=True)
    q.add_argument("--replay", required=True)
    q.add_argument("--output", required=True)
    a = ap.parse_args()
    {"analyze": cmd_analyze, "agreement": cmd_agreement}[a.cmd](a)


if __name__ == "__main__":
    main()
