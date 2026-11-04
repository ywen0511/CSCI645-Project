#!/usr/bin/env python3
"""Generate the v2 case suites with fixed seeds and record their hashes.

    python3 scripts/make_v2_suites.py development            # configs/v2/suites/development.jsonl
    python3 scripts/make_v2_suites.py heldout --protocol configs/v2/protocol.json   # validation + final

Case IDs carry a v2 suite prefix (``v2dev``, ``v2val``, ``v2final``), so they can never collide with v1 IDs
(``development``, ``validation``, ``final``). Each case is drawn from its own RNG stream
``SeedSequence([suite_seed, condition_index, case_index])`` (same scheme as v1). Pure Python + numpy.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from csci645_handover.core.case_suites import _case_rng, make_condition_cases, write_suite  # noqa: E402

V1_CONDITIONS = json.loads((ROOT / "configs/frozen/protocol.json").read_text())["evaluation"]["conditions"]
OUT = ROOT / "configs/v2/suites"


def development(seed: int = 6453028, per_condition: int = 50) -> dict:
    cases = []
    for ci, cond in enumerate(V1_CONDITIONS):
        cases += make_condition_cases("v2dev", seed, ci, cond, per_condition, "v2-dev")
    h = write_suite(OUT / "development.jsonl", cases)
    return {"development": {"path": "configs/v2/suites/development.jsonl", "seed": seed, "cases": len(cases),
                            "per_condition": per_condition, "conditions": [c["id"] for c in V1_CONDITIONS],
                            "sha256": h}}


def validation_cases(spec: dict) -> list[dict]:
    """Validation strata: each stratum has its own uniform position bound and release-offset range."""
    cases = []
    for si, st in enumerate(spec["strata"]):
        for i in range(st["cases"]):
            rng = _case_rng(spec["seed"], si, i)
            b = float(st["position_bound_m"])
            off = rng.uniform(-b, b, size=3) if b > 0 else [0.0, 0.0, 0.0]
            lo, hi = st["release_offset_range_s"]
            rel = float(rng.uniform(lo, hi)) if hi > lo else float(lo)
            cases.append({
                "case_id": f"v2val-{st['id']}-{i:04d}", "suite": "v2val", "condition": st["id"],
                "distribution": st.get("relation", ""),
                "requested_offset_xyz_m": [round(float(v), 9) for v in off], "release_offset_s": round(rel, 9),
                "init_seed": int(rng.integers(0, 2**31 - 1)), "config_id": "v2", "suite_version": 2,
            })
    return cases


def heldout(protocol_path: str) -> dict:
    p = json.loads(Path(protocol_path).read_text())
    ev = p["evaluation"]
    val = validation_cases(ev["validation"])
    final = []
    for ci, cond in enumerate(ev["final_conditions"]):
        final += make_condition_cases("v2final", ev["final_suite_seed"], ci, cond, cond.get("cases", 200), "v2")
    out = {
        "validation": {"path": "configs/v2/suites/validation.jsonl", "seed": ev["validation"]["seed"],
                       "cases": len(val), "sha256": write_suite(OUT / "validation.jsonl", val)},
        "final": {"path": "configs/v2/suites/final.jsonl", "seed": ev["final_suite_seed"], "cases": len(final),
                  "sha256": write_suite(OUT / "final.jsonl", final)},
    }
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("which", choices=["development", "heldout"])
    ap.add_argument("--protocol", default="configs/v2/protocol.json")
    a = ap.parse_args()
    manifest_path = OUT / "SUITES.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    manifest.update(development() if a.which == "development" else heldout(str(ROOT / a.protocol)))
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
