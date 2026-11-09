#!/usr/bin/env python3
"""Verify a downloaded v3.0.1 maintenance release and extract the preserved v3.0.0 assets (standard library only).

    python3 -I scripts/post_v3_verify_release.py --bundle <download dir> --original-out <new empty dir> \
        [--expect-tooling-sha <sha>] --output <verify.json>

Checks (all must pass; every problem is listed):
  1. SHA256SUMS: every listed asset matches; every downloaded asset except SHA256SUMS and the downloader's own
     download_log.json is listed.
  2. release_manifest.json lists every other asset (all but itself and SHA256SUMS) with matching size and SHA-256.
  3. Every archive in the release: member paths are safe (relative, no '..', regular files/directories only) and
     the member set, sizes and SHA-256 equal archive_inventories.json.
  4. The nested v3.0.0-original-assets.tar is extracted into --original-out; each original asset equals the
     manifest's original list (which was cross-checked against an anonymous v3.0.0 download at packaging time)
     and the original SHA256SUMS inside it.
  5. checkpoint_locations.json: every entry resolves - its original asset exists, the member exists inside that
     archive and hashes to the indexed SHA-256 and size (all checkpoint archives are opened and hashed).
  6. Provenance fields are present; optionally the maintenance tooling SHA equals --expect-tooling-sha.
After this, run the original verifier on --original-out (see docs/v3/REPRODUCE.md, section 2).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
from pathlib import Path, PurePosixPath


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def safe(name: str) -> bool:
    p = PurePosixPath(name)
    return not p.is_absolute() and ".." not in p.parts and name not in ("", ".")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--original-out", required=True)
    ap.add_argument("--expect-tooling-sha", default=None)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    B, O = Path(a.bundle), Path(a.original_out)
    problems, info = [], {}
    sums = {l.split()[1].lstrip("*"): l.split()[0] for l in (B / "SHA256SUMS").read_text().splitlines() if l.strip()}
    present = sorted(p.name for p in B.iterdir() if p.is_file() and p.name not in ("SHA256SUMS", "download_log.json"))
    for n in present:
        if n not in sums:
            problems.append(f"asset not in SHA256SUMS: {n}")
    for n, h in sums.items():
        if not (B / n).exists():
            problems.append(f"listed asset missing: {n}")
        elif sha(B / n) != h:
            problems.append(f"checksum mismatch: {n}")
    info["assets_checked"] = len(sums)
    man = json.loads((B / "release_manifest.json").read_text())
    listed = {x["name"]: x for x in man["assets"]}
    for n in present:
        if n == "release_manifest.json":
            continue
        x = listed.get(n)
        if x is None or x["sha256"] != sha(B / n) or x["bytes"] != (B / n).stat().st_size:
            problems.append(f"manifest does not cover {n} correctly")
    for k in ("experiment_v3_sha", "original_delivery_sha", "maintenance_source_tag", "maintenance_tooling_sha"):
        if not man.get("provenance", {}).get(k):
            problems.append(f"manifest provenance lacks {k}")
    if a.expect_tooling_sha and man["provenance"].get("maintenance_tooling_sha") != a.expect_tooling_sha:
        problems.append("maintenance tooling SHA differs from the expected tag commit")
    info["provenance"] = man.get("provenance")

    inv = json.loads((B / "archive_inventories.json").read_text())
    members = 0
    for name, rows in inv.items():
        if not isinstance(rows, list):
            continue
        want = {r["path"]: r for r in rows}
        got = {}
        with tarfile.open(B / name) as t:
            for m in t:
                if not safe(m.name):
                    problems.append(f"{name}: unsafe member path {m.name}")
                    continue
                if m.isdir():
                    continue
                if not m.isfile():
                    problems.append(f"{name}: non-regular member {m.name}")
                    continue
                data = t.extractfile(m).read()
                got[m.name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        if set(got) != set(want):
            problems.append(f"{name}: member set differs from inventory ({len(got)} vs {len(want)})")
        for p, g in got.items():
            w = want.get(p)
            if w and (w["bytes"] != g["bytes"] or w["sha256"] != g["sha256"]):
                problems.append(f"{name}: member hash/size mismatch {p}")
        members += len(got)
    info["archive_members_rehashed"] = members

    O.mkdir(parents=True, exist_ok=True)
    if any(O.iterdir()):
        raise SystemExit(f"{O} is not empty")
    nested = B / "v3.0.0-original-assets.tar"
    with tarfile.open(nested) as t:
        for m in t:
            if not (m.isfile() and safe(m.name) and "/" not in m.name):
                problems.append(f"nested archive: unexpected member {m.name}")
                continue
            (O / m.name).write_bytes(t.extractfile(m).read())
    orig = {x["name"]: x for x in man["original_v3.0.0_assets"]}
    if sorted(p.name for p in O.iterdir()) != sorted(orig):
        problems.append("extracted original asset set differs from the manifest")
    osums = {l.split()[1].lstrip("*"): l.split()[0] for l in (O / "SHA256SUMS").read_text().splitlines() if l.strip()}
    for n, x in orig.items():
        h = sha(O / n) if (O / n).exists() else None
        if h != x["sha256"]:
            problems.append(f"original asset differs from manifest: {n}")
        if n != "SHA256SUMS" and osums.get(n) != h:
            problems.append(f"original asset differs from original SHA256SUMS: {n}")
    info["original_assets"] = len(orig)

    locs = json.loads((B / "checkpoint_locations.json").read_text())["checkpoints"]
    need = {}
    for e in locs:
        need.setdefault(e["original_asset"], {})[e["member"]] = e
    resolved = 0
    for asset, want in sorted(need.items()):
        p = O / asset
        if not p.exists():
            problems.append(f"checkpoint archive missing: {asset}")
            continue
        seen = set()
        with tarfile.open(p) as t:
            for m in t:
                if m.name in want and m.isfile():
                    data = t.extractfile(m).read()
                    e = want[m.name]
                    if hashlib.sha256(data).hexdigest() != e["sha256"] or len(data) != e["size_bytes"]:
                        problems.append(f"checkpoint hash/size mismatch: {asset}:{m.name}")
                    seen.add(m.name)
        for missing in sorted(set(want) - seen):
            problems.append(f"checkpoint member missing: {asset}:{missing}")
        resolved += len(seen)
    info["checkpoints_indexed"] = len(locs)
    info["checkpoints_resolved"] = resolved
    rec = {"ok": not problems, "problems": problems, **info}
    Path(a.output).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: v for k, v in rec.items() if k != "provenance"}))
    raise SystemExit(0 if rec["ok"] else 1)


if __name__ == "__main__":
    main()
