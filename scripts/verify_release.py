#!/usr/bin/env python3
"""Verify a local release inventory; does not prove scientific completeness or replay."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys


REQUIRED_KINDS = {"report", "results", "logs", "configs", "checkpoints", "videos", "reproduction", "index"}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def safe_path(root, name):
    if not isinstance(name, str) or not name or "\\" in name:
        raise ValueError("Artifact paths must be nonempty POSIX strings")
    relative = PurePosixPath(name)
    if relative.is_absolute() or ".." in relative.parts or str(relative) != name:
        raise ValueError(f"Unsafe or noncanonical artifact path: {name}")
    resolved = (root / name).resolve()
    if root not in resolved.parents:
        raise ValueError(f"Artifact escapes bundle root: {name}")
    if not resolved.is_file():
        raise ValueError(f"Missing artifact: {name}")
    return resolved


def verify(bundle, protocol_path):
    root = Path(bundle).resolve()
    protocol_path = Path(protocol_path)
    protocol = json.loads(protocol_path.read_text())
    manifest_path = safe_path(root, "manifest.json")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema_version") != 1 or manifest.get("status") != "complete":
        raise ValueError("Expected a schema-version-1 manifest marked complete")
    for field in ("experiment_source_commit", "analysis_commit"):
        if not re.fullmatch(r"[0-9a-f]{40}", str(manifest.get(field, ""))):
            raise ValueError(f"Invalid {field}")
    if manifest.get("protocol_sha256") != digest(protocol_path):
        raise ValueError("Frozen protocol hash does not match")
    if protocol.get("status") != "frozen":
        raise ValueError("Protocol must be explicitly marked frozen")
    if not isinstance(manifest.get("release_tag"), str) or not manifest["release_tag"].strip():
        raise ValueError("Missing release tag")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("No artifacts listed")
    seen, kinds, checkpoints = set(), set(), set()
    actual_hashes = {"manifest.json": digest(manifest_path)}
    for item in artifacts:
        name = item["path"]
        if name in seen or name in {"manifest.json", "SHA256SUMS"}:
            raise ValueError(f"Duplicate or reserved artifact path: {name}")
        path = safe_path(root, name)
        seen.add(name)
        if type(item["size_bytes"]) is not int or item["size_bytes"] <= 0 or item["size_bytes"] != path.stat().st_size:
            raise ValueError(f"Invalid file size: {name}")
        actual_hashes[name] = digest(path)
        if item["sha256"] != actual_hashes[name]:
            raise ValueError(f"Checksum mismatch: {name}")
        kinds.add(item["kind"])
        if item["kind"] == "checkpoints":
            if type(item.get("seed")) is not int:
                raise ValueError(f"Checkpoint archive lacks integer seed: {name}")
            checkpoints.add((item["method"], item["seed"]))
    if not REQUIRED_KINDS <= kinds:
        raise ValueError(f"Missing artifact kinds: {sorted(REQUIRED_KINDS - kinds)}")
    expected = {(m["id"], s) for m in protocol["methods"] if m["learned"] for s in protocol["training"]["seeds"]}
    if not expected <= checkpoints:
        raise ValueError(f"Missing checkpoint method/seed coverage: {sorted(expected - checkpoints)}")
    sums = {}
    for line in safe_path(root, "SHA256SUMS").read_text().splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match or match[2] in sums:
            raise ValueError("Malformed or duplicate SHA256SUMS entry")
        sums[match[2]] = match[1]
    if sums != actual_hashes:
        raise ValueError("SHA256SUMS does not exactly match the manifest and artifact inventory")
    return len(artifacts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path, help="Directory containing downloaded or staged assets")
    parser.add_argument("--protocol", required=True, type=Path, help="Exact frozen JSON protocol used for experiments")
    args = parser.parse_args()
    try:
        count = verify(args.bundle, args.protocol)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Release inventory verification failed: {exc}", file=sys.stderr)
        return 1
    print(f"Verified {count} artifact sizes/hashes and required method/seed archive coverage.")
    print("Still required: archive semantics, raw-result reconciliation, checkpoint replay, report/video QA, and online availability.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
