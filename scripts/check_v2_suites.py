#!/usr/bin/env python3
"""Check that v2 suites are disjoint from each other and from the v1 suites (case IDs and sampled offsets).

    python3 scripts/check_v2_suites.py --output results/v2/suites_check.json

Clean and timing-only cases have zero position offset by construction; they are deterministic repeats, not
independent physical draws, and are excluded from the offset-collision check (reported separately).
"""

import argparse
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(p):
    return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", default=str(ROOT / "results/v2/suites_check.json"))
    a = ap.parse_args()
    suites = {p.stem: load(p) for p in sorted((ROOT / "configs/v2/suites").glob("*.jsonl")) if p.stem != "v1_replay_sample"}
    suites.update({f"v1_{p.stem}": load(p) for p in sorted((ROOT / "configs/frozen/suites").glob("*.jsonl"))})
    ids = collections.Counter(c["case_id"] for s in suites.values() for c in s)
    dup_ids = [k for k, v in ids.items() if v > 1]
    offs = collections.defaultdict(set)
    zero = collections.Counter()
    for name, s in suites.items():
        for c in s:
            o = tuple(round(v, 9) for v in c["requested_offset_xyz_m"])
            if all(v == 0 for v in o):
                zero[name] += 1
                continue
            offs[o].add(name)
    shared = {str(k): sorted(v) for k, v in offs.items() if len(v) > 1}
    seeds = collections.Counter(c["init_seed"] for s in suites.values() for c in s)
    out = {"suites": {k: len(v) for k, v in suites.items()}, "duplicate_case_ids": dup_ids,
           "nonzero_offsets_shared_between_suites": shared, "zero_offset_cases_per_suite": dict(zero),
           "duplicate_init_seeds": sum(1 for v in seeds.values() if v > 1),
           "ok": not dup_ids and not shared}
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
