#!/usr/bin/env python3
"""Allow the intended configuration change in the reversed-history and current-frame-only mechanism matrices (CPU).

    python3 scripts/v5_mechanism_matrices.py

The two interventions evaluate a selected history checkpoint with `observation_history_permutation` = [3, 2, 1, 0]
or `observation_history_mode` = "repeat_current". Both fields are part of the configuration hash, so
`eval_matrix.py` refuses the checkpoint unless the entry sets `allow_config_mismatch` (it then records both hashes).
V4 set that flag on exactly these entries (scripts/v4_manifests.py); the frozen V5 generator
(scripts/v5_slip_study.py `mechanisms`) omitted it, and all ten tasks exited before simulating. This step adds only
that flag to those entries. Idempotent.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "configs/v5/slip/matrices_post/mechanisms"


def main():
    n = 0
    for p in sorted(list(D.glob("reversed_*.json")) + list(D.glob("current_only_*.json"))):
        m = json.loads(p.read_text())
        assert m["base_overrides"] and len(m["entries"]) == 1, p
        for e in m["entries"]:
            if not e.get("allow_config_mismatch"):
                e["allow_config_mismatch"] = True
                n += 1
        p.write_text(json.dumps(m, indent=1) + "\n")
    print(f"{n} entries updated")


if __name__ == "__main__":
    main()
