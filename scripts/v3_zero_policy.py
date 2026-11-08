#!/usr/bin/env python3
"""Zero-policy controls (CPU): untrained step-0 checkpoints of each distinct profile (seed 11) on the 65-case
subset, compared case by case with the deterministic controller they reduce to in the final matrix
(combined -> geometry_common, residual -> nominal). Step 0 has a zero-mean initialization, so the deterministic
inference action is zero and the outcome should match the controller; agreement is reported, not assumed.

    python3 scripts/v3_zero_policy.py --runs <runs root> [--output results/v3/zero_policy]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILES = {"combined_clean_ff": "geometry_common", "combined_robust_ff": "geometry_common",
            "combined_robust_history": "geometry_common", "combined_robust_repeat": "geometry_common",
            "residual_robust_history": "nominal"}


def jl(p: Path):
    return {r["case_id"]: r for r in (json.loads(l) for l in p.read_text().splitlines() if l.strip())}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--output", default=str(ROOT / "results/v3/zero_policy"))
    a = ap.parse_args()
    R, O = Path(a.runs), Path(a.output)
    O.mkdir(parents=True, exist_ok=True)
    ids = [json.loads(l)["case_id"] for l in (ROOT / "configs/v3/suites/final_subset65.jsonl").read_text().splitlines() if l.strip()]
    rows = {}
    for prof, ref in PROFILES.items():
        z = jl(R / "zero_policy" / prof / f"{prof}_s11__step0.jsonl")
        g = jl(R / "final" / ref / f"{ref}.jsonl")
        if set(z) != set(ids):
            raise SystemExit(f"{prof}: {len(z)} of {len(ids)} cases")
        rows[prof] = {"reference": ref, "cases": len(ids), "success": sum(z[c]["success"] for c in ids),
                      "reference_success": sum(g[c]["success"] for c in ids),
                      "terminal_equal_reference": sum(z[c]["terminal_reason"] == g[c]["terminal_reason"] for c in ids),
                      "invalid_resets": sum(not z[c]["reset_valid"] for c in ids),
                      "max_abs_residual_m": max(z[c].get("residual_abs_max_m", 0.0) for c in ids)}
    out = {"rows": rows, "note": "reference records are the batch-256 final matrix; the control ran at batch 65"}
    (O / "zero_policy.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
