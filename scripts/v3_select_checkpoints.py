#!/usr/bin/env python3
"""Select one checkpoint per formal v3 run from its validation records (CPU).

    python3 scripts/v3_select_checkpoints.py --validation <runs>/validation --output results/v3/selection

Rule (frozen; `selection.select_v2`): highest validation success, then lowest collision rate, then lowest mean
bounded residual squared norm, then the latest transition count. Step 0 is an untrained control and never
eligible. Every scheduled validation case (240) must be recorded with a valid reset before candidates are
compared. Writes <run>.json (all candidates + step-0 control + rationale) and selection.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from csci645_handover.selection import score_validation_records_v2, select_v2  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--validation", required=True)
    ap.add_argument("--output", default=str(ROOT / "results/v3/selection"))
    a = ap.parse_args()
    V, O = Path(a.validation), Path(a.output)
    O.mkdir(parents=True, exist_ok=True)
    suite = {json.loads(l)["case_id"] for l in (ROOT / "configs/v3/suites/validation.jsonl").read_text().splitlines() if l.strip()}
    out = {}
    for mp in sorted((ROOT / "configs/v3/frozen/matrices/validation").glob("*.json")):
        run = mp.stem
        mx = json.loads(mp.read_text())
        cands, control = [], None
        for e in mx["entries"]:
            f = V / run / e["id"] / f"{e['id']}.jsonl"
            rows = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
            ids = [r["case_id"] for r in rows]
            if set(ids) != suite or len(ids) != len(suite):
                raise SystemExit(f"{f}: {len(ids)} records, expected all {len(suite)} validation cases exactly once")
            if not all(r["reset_valid"] for r in rows):
                raise SystemExit(f"{f}: invalid resets; reconcile before selection")
            sc = score_validation_records_v2(rows)
            sc.update(tag=Path(e["checkpoint"]).stem, entry=e["id"], records=str(f.relative_to(V.parent)),
                      by_condition={c: sum(r["success"] for r in rows if r["condition"] == c) for c in sorted({r["condition"] for r in rows})})
            if e.get("role") == "untrained_control":
                control = sc
            else:
                cands.append(sc)
        best = select_v2(cands)
        rec = {"run": run, "rule": "select_v2: success desc, collision asc, residual sq norm asc, latest; step 0 excluded",
               "selected": best["tag"], "selected_checkpoint_sha256": best["checkpoint_sha256"], "candidates": cands,
               "untrained_control": control}
        (O / f"{run}.json").write_text(json.dumps(rec, indent=1) + "\n")
        out[run] = {"selected": best["tag"], "success_rate": best["success_rate"], "collision_rate": best["collision_rate"],
                    "checkpoint_sha256": best["checkpoint_sha256"]}
    (O / "selection.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
