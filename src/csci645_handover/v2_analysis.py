"""v2 analysis helpers (CPU only, numpy): record loading, condition summaries, paired comparisons,
constant-offset selection and factorial geometry-ablation effects."""

from __future__ import annotations

import collections
import csv
import json
from pathlib import Path

import numpy as np

from .core.stats import paired_bootstrap_diff, wilson

OUTCOMES = ("success", "drop", "collision", "episode_timeout", "release_timeout", "invalid_reset")


def load_records(*dirs: str | Path) -> dict[str, list[dict]]:
    """``{entry_or_file_id: records}`` from every ``*.jsonl`` record file (provenance files skipped)."""
    out: dict[str, list[dict]] = {}
    for d in dirs:
        for f in sorted(Path(d).glob("*.jsonl")):
            if f.name in ("eval_runs.jsonl",):
                continue
            rows = [json.loads(x) for x in f.read_text().splitlines() if x.strip()]
            if not rows or "case_id" not in rows[0]:
                continue
            key = rows[0].get("entry_id") or f.stem
            if key in out:
                raise ValueError(f"duplicate entry {key} in {f}")
            ids = [r["case_id"] for r in rows]
            if len(ids) != len(set(ids)):
                raise ValueError(f"duplicate case IDs in {f}")
            out[key] = rows
    return out


def outcome_flags(r: dict) -> dict[str, bool]:
    return {"success": bool(r["success"]), "drop": bool(r["drop"]), "collision": bool(r["collision"]),
            "episode_timeout": r["terminal_reason"] == "episode_timeout",
            "release_timeout": r["terminal_reason"] == "release_timeout",
            "invalid_reset": not r["reset_valid"]}


def summarize(rows: list[dict], groups: dict[str, list[str]]) -> dict[str, dict]:
    """Per condition and per group: scheduled, valid, counts, valid-case and scheduled-case success."""
    by = collections.defaultdict(list)
    for r in rows:
        by[r["condition"]].append(r)
    out = {}
    keys = list(sorted(by)) + list(groups)
    for k in keys:
        rs = by[k] if k in by else [r for c in groups[k] for r in by.get(c, [])]
        if not rs:
            continue
        valid = [r for r in rs if r["reset_valid"]]
        cnt = {o: sum(outcome_flags(r)[o] for r in rs) for o in OUTCOMES}
        n_v = len(valid)
        s = sum(r["success"] for r in valid)
        lo, hi = wilson(s, n_v)
        d = {"scheduled": len(rs), "valid": n_v, **{f"n_{o}": v for o, v in cnt.items()},
             "success_rate_valid": s / n_v if n_v else None, "success_rate_scheduled": s / len(rs),
             "success_wilson_low": lo, "success_wilson_high": hi,
             "terminal_reasons": dict(collections.Counter(r["terminal_reason"] for r in rs))}
        if k in groups:  # equal-condition mean (so clean repeats cannot dominate)
            per = [sum(x["success"] for x in by[c]) / len(by[c]) for c in groups[k] if by.get(c)]
            d["success_equal_condition_mean"] = float(np.mean(per)) if per else None
        out[k] = d
    return out


def outcome_matrix(entries: list[list[dict]], case_ids: list[str], key: str = "success") -> np.ndarray:
    """(len(entries), len(case_ids)) 0/1 matrix in a fixed case order (seed rows x shared cases)."""
    m = np.zeros((len(entries), len(case_ids)))
    for i, rows in enumerate(entries):
        idx = {r["case_id"]: r for r in rows}
        missing = [c for c in case_ids if c not in idx]
        if missing:
            raise ValueError(f"entry lacks {len(missing)} cases, e.g. {missing[:3]}")
        m[i] = [float(outcome_flags(idx[c])[key]) for c in case_ids]
    return m


def paired(a_entries, b_entries, case_ids, key="success", n_boot=10000, seed=645) -> dict:
    a = outcome_matrix(a_entries, case_ids, key)
    b = outcome_matrix(b_entries, case_ids, key)
    res = paired_bootstrap_diff(a, b, n_boot=n_boot, seed=seed)
    res.update(mean_a=float(a.mean()), mean_b=float(b.mean()), metric=key,
               per_seed_a=[float(x) for x in a.mean(1)], per_seed_b=[float(x) for x in b.mean(1)])
    return res


def select_constant(scores: list[dict]) -> dict:
    """Constant-offset rule: highest success; then fewer collision episodes; then smaller |x|; then ascending x."""
    return sorted(scores, key=lambda s: (-s["success"], s["collision_episodes"], abs(s["x_m"]), s["x_m"]))[0]


def factorial_effects(success_by_combo: dict[str, np.ndarray]) -> dict:
    """Main effects, two-way interactions and the three-way interaction of A/H/G on case-level success.

    ``success_by_combo`` maps 'none','A',...,'AHG' to 0/1 arrays over the same cases. Effects use the
    standard 2^3 contrasts (difference of means, +1/-1 coding / 4), plus every conditional effect
    (effect of one factor at each level of the other two)."""
    combos = ["none", "A", "H", "G", "AH", "AG", "HG", "AHG"]
    lev = {c: {f: (f in c and c != "none") for f in "AHG"} for c in combos}
    y = {c: success_by_combo[c] for c in combos}
    out = {}
    for name in ("A", "H", "G", "AH", "AG", "HG", "AHG"):
        contrast = np.zeros_like(next(iter(y.values())), dtype=float)
        for c in combos:
            sign = 1.0
            for f in name:
                sign *= 1.0 if lev[c][f] else -1.0
            contrast = contrast + sign * y[c]
        out[f"effect_{name}"] = float(contrast.mean() / 4.0)
    cond = {}
    for f in "AHG":
        others = [g for g in "AHG" if g != f]
        for o1 in (False, True):
            for o2 in (False, True):
                def combo(fv):
                    s = "".join(x for x, v in zip([f] + others, [fv, o1, o2]) if v)
                    s = "".join(ch for ch in "AHG" if ch in s)
                    return s or "none"
                key = f"{f}|{others[0]}={'on' if o1 else 'off'},{others[1]}={'on' if o2 else 'off'}"
                cond[key] = float(y[combo(True)].mean() - y[combo(False)].mean())
    out["conditional_effects"] = cond
    return out


def write_csv(path: str | Path, rows: list[dict]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in r.items()})


def pct(x) -> str:
    return "–" if x is None else f"{100 * x:.1f}"
