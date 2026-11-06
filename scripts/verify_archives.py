#!/usr/bin/env python3
"""Re-hash every member of every release archive against ``archive_inventories.json``.

    python3 scripts/verify_archives.py --bundle downloads/v1.0.0 [--extract downloads/v1.0.0/extracted]

Checks that each inventoried member exists with the recorded size and SHA-256 and that no archive holds
unlisted regular files. With --extract, archives are unpacked there (members with absolute paths or ``..``
are rejected). Prints a JSON summary and exits non-zero on any mismatch.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tarfile
from pathlib import Path, PurePosixPath


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--extract", default=None)
    a = ap.parse_args()
    root = Path(a.bundle)
    inv = json.loads((root / "archive_inventories.json").read_text())
    summary = {"archives": 0, "members_checked": 0, "mismatches": [], "unlisted": [], "missing": []}
    for name, members in sorted(inv.items()):
        path = root / name
        if not path.exists():
            summary["missing"].append(name)
            continue
        expect = {m["path"]: m for m in members}
        seen = set()
        with tarfile.open(path, "r:*") as tf:
            for ti in tf:
                p = PurePosixPath(ti.name)
                if p.is_absolute() or ".." in p.parts:
                    raise SystemExit(f"{name}: unsafe member {ti.name}")
                if not ti.isfile():
                    continue
                m = expect.get(ti.name)
                if m is None:
                    summary["unlisted"].append(f"{name}:{ti.name}")
                    continue
                h = hashlib.sha256()
                f = tf.extractfile(ti)
                for block in iter(lambda: f.read(1 << 20), b""):
                    h.update(block)
                seen.add(ti.name)
                summary["members_checked"] += 1
                if h.hexdigest() != m["sha256"] or ti.size != m["size_bytes"]:
                    summary["mismatches"].append(f"{name}:{ti.name}")
            if a.extract:
                dest = Path(a.extract)
                dest.mkdir(parents=True, exist_ok=True)
                tf.extractall(dest, filter="data")
        summary["missing"] += [f"{name}:{p}" for p in expect if p not in seen]
        summary["archives"] += 1
    ok = not (summary["mismatches"] or summary["unlisted"] or summary["missing"])
    summary["ok"] = ok
    print(json.dumps(summary, indent=2))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
