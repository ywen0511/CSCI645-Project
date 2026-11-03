#!/usr/bin/env python3
"""Apply the frozen checkpoint-selection rule to validation records (no simulator).

Usage:
    python3 scripts/select_checkpoints.py --validation RUNS/validation --run-id combined_seed11 --output RUNS/selection

Rule (configs/frozen/protocol.json): highest validation success rate; ties by lowest validation drop rate,
then by the earliest training step. Writes <output>/<run_id>.json with every candidate's scores.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from csci645_handover.selection import score_validation_file, select  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--validation", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--expected-candidates", type=int, default=6)
    a = ap.parse_args()
    files = sorted(Path(a.validation).glob(f"{a.run_id}__step_*.jsonl"))
    scored = [score_validation_file(f) for f in files]
    if len(scored) != a.expected_candidates:
        raise SystemExit(f"{a.run_id}: expected {a.expected_candidates} validation candidates, found {len(scored)}")
    if any(s["scheduled"] != 100 for s in scored):
        raise SystemExit(f"{a.run_id}: incomplete validation file(s)")
    best = select(scored)
    out = Path(a.output)
    out.mkdir(parents=True, exist_ok=True)
    rule = "highest validation success, then lowest validation drop rate, then earliest step"
    (out / f"{a.run_id}.json").write_text(json.dumps({"run_id": a.run_id, "selected": best, "candidates": scored,
                                                      "rule": rule}, indent=2))
    print(f"{a.run_id}: selected {best['checkpoint']} (success {best['success_rate']:.2f}, drop {best['drop_rate']:.2f})")


if __name__ == "__main__":
    main()
