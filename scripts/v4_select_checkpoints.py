#!/usr/bin/env python3
"""Select one checkpoint per formal V4 run from its validation records only (CPU, standard library).

    python3 scripts/v4_select_checkpoints.py --validation <runs>/validation --checkpoint-root <runs>/train --output results/v4/selection

Rule (frozen in configs/v4/analysis_plan.json): candidates are the first saved checkpoints at or after 2, 4, 6,
8 and 10 million transitions; step 0 is an untrained control and never eligible. Key, in order:
  1. validation mean success, equal weight per validation condition (6 x 40 cases), descending;
  2. unsafe-event rate (any prohibited collision or a drop), ascending;
  3. residual magnitude (mean over cases of the per-episode mean max-axis |residual|), ascending;
  4. latest candidate (largest transition count).
Numerical ties: each value is rounded to 12 decimal places before comparison. Every scheduled validation case must
be recorded exactly once; invalid resets abort selection for reconciliation. Final outcomes are never read.
"""

from __future__ import annotations

import argparse
import json
import sys
import subprocess
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from csci645_handover import v4_protocol as v4  # noqa: E402


def score(rows):
    conds = list(v4.VALIDATION)
    per = {c: [r for r in rows if r["condition"] == c] for c in conds}
    succ = sum(sum(r["success"] for r in v) / len(v) for v in per.values()) / len(conds)
    unsafe = sum(bool(r["collision"]) or r["terminal_reason"] == "drop" for r in rows) / len(rows)
    resid = sum(r["residual_abs_mean_m"] for r in rows) / len(rows)
    return {"success_rate": succ, "unsafe_rate": unsafe, "residual_magnitude_m": resid,
            "transitions": rows[0]["checkpoint_transitions"], "checkpoint_sha256": rows[0]["checkpoint_sha256"],
            "by_condition": {c: sum(r["success"] for r in v) for c, v in per.items()}}


def key(s):
    r = lambda x: round(x, 12)  # noqa: E731
    return (-r(s["success_rate"]), r(s["unsafe_rate"]), r(s["residual_magnitude_m"]), -s["transitions"])


PROFILES = ("combined_clean_ff", "combined_robust_ff", "combined_robust_history",
            "combined_robust_repeat", "residual_robust_history")
CANDIDATES = ("step_002031616", "step_004030464", "step_006029312", "step_008028160", "step_010027008")


def candidate(rows, cases, entry, checkpoint, suite_hash, source_commit):
    """Anchor records to the declared suite, actual checkpoint bytes and immutable source."""
    if not rows:
        raise ValueError("Empty validation records")
    tag = Path(entry["checkpoint"]).stem
    if tag not in (*CANDIDATES, "step_000000000"):
        raise ValueError("Undeclared checkpoint candidate")
    expected = {"entry_id": entry["id"], "training_seed": entry["training_seed"],
                "checkpoint_transitions": int(tag.split("_")[1]),
                "checkpoint_sha256": v4.sha256(checkpoint), "suite_hash": suite_hash,
                "source_commit": source_commit, "source_dirty": False}
    for field in ("config_hash", "controller_hash"):
        value = rows[0].get(field)
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError(f"Missing or malformed {field}")
        expected[field] = value
    check = v4.validate_records(rows, cases, expected, complete=True)
    if check["invalid_resets"] or check["infra_errors"]:
        raise ValueError("Reconcile invalid resets or infrastructure failures before selection")
    return {**score(rows), "tag": tag, "entry": entry["id"]}


def select(validation, output, checkpoint_root, source_commit):
    V, O, C = Path(validation), Path(output), Path(checkpoint_root)
    suite_path = ROOT / "configs/v4/suites/validation.jsonl"
    cases = [json.loads(l) for l in suite_path.read_text().splitlines() if l.strip()]
    suite_hash = v4.sha256(suite_path)
    expected_runs = {f"{p}_s{s}" for p in PROFILES for s in v4.TRAINING_SEEDS}
    matrices = sorted((ROOT / "configs/v4/frozen/matrices/validation").glob("*.json"))
    if {p.stem for p in matrices} != expected_runs:
        raise ValueError("Validation requires exactly all 25 declared run matrices; freeze first")
    frozen = json.loads((ROOT / "configs/v4/FREEZE.json").read_text())["inputs"]
    for p in [suite_path, *matrices]:
        if frozen.get(p.relative_to(ROOT).as_posix()) != v4.sha256(p):
            raise ValueError(f"Validation input differs from freeze: {p.name}")
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("Expected an immutable experiment commit SHA")
    out, reports = {}, {}
    for mp in matrices:
        run = mp.stem
        entries = json.loads(mp.read_text())["entries"]
        tags = [Path(e["checkpoint"]).stem for e in entries]
        if len(tags) != 6 or set(tags) != {*CANDIDATES, "step_000000000"}:
            raise ValueError(f"{run}: require step 0 plus the five declared candidates exactly once")
        cands, control = [], None
        for e in entries:
            if e["training_seed"] != int(run.rsplit("_s", 1)[1]):
                raise ValueError(f"{run}: matrix seed mismatch")
            cp = Path(e["checkpoint"])
            if cp.is_absolute() or cp.parts[:2] != (run, "checkpoints") or ".." in cp.parts:
                raise ValueError(f"{run}: checkpoint belongs to another run")
            tag = cp.stem
            expected_role = "untrained_control" if tag == "step_000000000" else "candidate"
            if e.get("role") != expected_role:
                raise ValueError(f"{run}: invalid candidate/control role")
            f = V / run / f"{e['id']}.jsonl"
            rows = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
            scored = candidate(rows, cases, e, C / cp, suite_hash, source_commit)
            if expected_role == "untrained_control":
                control = scored
            else:
                cands.append(scored)
        best = sorted(cands, key=key)[0]
        reports[run] = {"run": run, "rule": __doc__.split("Key, in order:")[1].strip(),
                        "source_commit": source_commit, "suite_sha256": suite_hash,
                        "selected": best["tag"], "candidates": cands, "untrained_control": control}
        out[run] = {"selected": best["tag"], "success_rate": best["success_rate"], "unsafe_rate": best["unsafe_rate"],
                    "residual_magnitude_m": best["residual_magnitude_m"], "checkpoint_sha256": best["checkpoint_sha256"]}
    # Nothing is published until every run passes validation.
    O.mkdir(parents=True, exist_ok=True)
    for run, report in reports.items():
        (O / f"{run}.json").write_text(json.dumps(report, indent=1) + "\n")
    (O / "selection.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--validation", required=True)
    ap.add_argument("--checkpoint-root", required=True, help="Formal train directory; hash checkpoint files without loading Torch")
    ap.add_argument("--output", default=str(ROOT / "results/v4/selection"))
    a = ap.parse_args()
    source = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "experiment-v4^{commit}"], text=True).strip()
    out = select(a.validation, a.output, a.checkpoint_root, source)
    print(json.dumps({k: v["selected"] for k, v in out.items()}, indent=1))


if __name__ == "__main__":
    main()
