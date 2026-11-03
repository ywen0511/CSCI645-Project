#!/usr/bin/env python3
"""Generate the development / validation / final case suites from a protocol file (numpy only).

Usage:
    python3 scripts/make_suites.py --protocol configs/frozen/protocol.json --output configs/frozen/suites

Writes development.jsonl, validation.jsonl, final.jsonl and suites.json (counts + SHA-256 hashes).
Refuses to overwrite an existing suite file whose content would change (frozen suites are immutable).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from csci645_handover.core.case_suites import build_suites, canonical_jsonl  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--protocol", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--dev-per-condition", type=int, default=50)
    ap.add_argument("--force", action="store_true", help="Allow replacing changed suites (never after freeze).")
    a = ap.parse_args()
    proto_path = Path(a.protocol)
    protocol = json.loads(proto_path.read_text())
    config_id = protocol.get("config_id", "unfrozen")
    suites = build_suites(protocol, config_id, a.dev_per_condition)
    out = Path(a.output)
    out.mkdir(parents=True, exist_ok=True)
    index = {"protocol": proto_path.name, "config_id": config_id, "suites": {}}
    for name, cases in suites.items():
        data = canonical_jsonl(cases)
        path = out / f"{name}.jsonl"
        if path.exists() and path.read_bytes() != data and not a.force:
            raise SystemExit(f"{path} exists with different content; refusing to overwrite a suite")
        path.write_bytes(data)
        conds = {}
        for c in cases:
            conds[c["condition"]] = conds.get(c["condition"], 0) + 1
        index["suites"][name] = {"file": path.name, "cases": len(cases), "sha256": hashlib.sha256(data).hexdigest(),
                                 "per_condition": conds}
    (out / "suites.json").write_text(json.dumps(index, indent=2))
    print(json.dumps(index, indent=2))


if __name__ == "__main__":
    main()
