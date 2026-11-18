#!/usr/bin/env python3
"""Address post-selection matrices through the delivery checkout in the runner manifests (CPU).

    python3 scripts/v5_manifest_paths.py final_learned regression repeat_learned mech_dev [mechanisms]

The frozen generator (`scripts/v5_slip_study.py`, a freeze input) writes post-selection matrices under
configs/v5/slip/matrices_post/ in the delivery checkout and addresses them relative to the execution checkout,
which is the frozen `experiment-v5b` tag and therefore cannot contain them. V4 addressed such matrices as
`$DELIVERY/...` (scripts/v4_manifests.py). This step rewrites only those path strings in
results/v5/jobs/<name>.json (matrix argument and declared inputs); matrix contents, suites, protocols,
checkpoints and seeds are unchanged. Idempotent.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "configs/v5/slip/matrices_post/"


def fix(value):
    return "$DELIVERY/" + value if isinstance(value, str) and value.startswith(PREFIX) else value


def main(names):
    for name in names:
        p = ROOT / "results/v5/jobs" / f"{name}.json"
        m = json.loads(p.read_text())
        n = 0
        for t in m["tasks"]:
            new_argv, new_in = [fix(v) for v in t["argv"]], [fix(v) for v in t.get("inputs", [])]
            n += (new_argv != t["argv"]) + (new_in != t.get("inputs", []))
            t["argv"], t["inputs"] = new_argv, new_in
        for t in m["tasks"]:
            for v in t["argv"] + t["inputs"]:
                if isinstance(v, str) and v.startswith(PREFIX):
                    raise SystemExit(f"{name}: unresolved {v}")
        p.write_text(json.dumps(m, indent=1) + "\n")
        print(f"{name}: {len(m['tasks'])} tasks, {n} fields rewritten")


if __name__ == "__main__":
    main(sys.argv[1:])
