#!/usr/bin/env python3
"""Apply the frozen v2 checkpoint-selection rule to validation records (CPU only).

    python3 scripts/v2_select.py --train-root runs/v2/final/train --validation runs/v2/final/validation \
        --output results/v2/final/selection

For each run directory: candidates = first periodic checkpoint at/after 2M, 4M, 6M, 8M, 10M transitions
(step 0 excluded); every candidate must have exactly one complete validation record file
(``<run_id>__<tag>.jsonl`` with all validation cases). Rule: highest validation success; then lowest
collision-episode rate; then lowest mean bounded residual squared norm over scored steps; then the latest
transition count. Writes ``<run_id>.json`` (all candidate scores, ties, selected) and ``selection.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from csci645_handover.selection import score_validation_records_v2, select_v2, validation_candidates_v2  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--train-root", required=True)
    ap.add_argument("--validation", required=True)
    ap.add_argument("--suite", default=str(ROOT / "configs/v2/suites/validation.jsonl"))
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    suite_ids = {json.loads(x)["case_id"] for x in Path(a.suite).read_text().splitlines() if x.strip()}
    out = Path(a.output)
    out.mkdir(parents=True, exist_ok=True)
    summary = {}
    for rd in sorted(p for p in Path(a.train_root).iterdir() if (p / "checkpoints.jsonl").exists()):
        cands = validation_candidates_v2(rd / "checkpoints.jsonl")
        scored = []
        for c in cands:
            f = Path(a.validation) / rd.name / f"{rd.name}__{c['tag']}.jsonl"
            if not f.exists():
                f = Path(a.validation) / f"{rd.name}__{c['tag']}.jsonl"
            rows = [json.loads(x) for x in f.read_text().splitlines() if x.strip()] if f.exists() else []
            ids = {r["case_id"] for r in rows}
            if ids != suite_ids or len(rows) != len(suite_ids):
                raise SystemExit(f"{f}: {len(rows)} records, expected the {len(suite_ids)} validation cases")
            if {r["checkpoint_sha256"] for r in rows} != {c["sha256"]}:
                raise SystemExit(f"{f}: checkpoint hash does not match the ledger")
            s = score_validation_records_v2(rows)
            s.update(tag=c["tag"], file=f.name, ledger_transitions=c["transitions"])
            scored.append(s)
        sel = select_v2(scored)
        top = [s for s in scored if s["success_rate"] == sel["success_rate"]]
        rec = {"run_id": rd.name, "rule": "max success; min collision-episode rate; min mean residual squared norm; latest",
               "candidates": scored, "selected": sel,
               "ties_on_success": [s["tag"] for s in top],
               "ties_on_success_and_collision": [s["tag"] for s in top if s["collision_rate"] == sel["collision_rate"]],
               "selected_is_last_candidate": sel["tag"] == scored[-1]["tag"]}
        (out / f"{rd.name}.json").write_text(json.dumps(rec, indent=1) + "\n")
        summary[rd.name] = {"selected": sel["tag"], "transitions": sel["transitions"], "success_rate": sel["success_rate"],
                            "collision_rate": sel["collision_rate"], "residual_sq_norm_mean_m2": sel["residual_sq_norm_mean_m2"],
                            "n_tied_on_success": len(top)}
        print(f"{rd.name}: {sel['tag']} success={sel['success_rate']:.4f} coll={sel['collision_rate']:.4f} "
              f"res2={sel['residual_sq_norm_mean_m2']:.3e} (tied on success: {len(top)}/{len(scored)})")
    (out / "selection.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
