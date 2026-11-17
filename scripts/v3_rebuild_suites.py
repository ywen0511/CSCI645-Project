#!/usr/bin/env python3
"""Rebuild archived v3 suites without modifying the experiment checkout or freeze.

Use a full Git checkout at experiment-v3, not a source tarball: the pre-final
SUITES.json bytes are verified against the recorded freeze source commit.
Standard library only; no simulator import or GPU work.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

EXPERIMENT = "3811f5da5ef55638f95f7306e449609877f546df"
SUITES = "configs/v3/SUITES.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args])


def rebuild(repo, output=None):
    repo = Path(repo).resolve()
    if output is not None:
        output = Path(output).resolve()
        if output == repo or repo in output.parents:
            raise ValueError("Write suite copies outside the immutable experiment checkout")
    if git(repo, "rev-parse", "HEAD").decode().strip() != EXPERIMENT:
        raise ValueError("Use a checkout at the immutable experiment-v3 commit")
    if git(repo, "status", "--porcelain", "--untracked-files=no").strip():
        raise ValueError("Experiment checkout has tracked changes")
    freeze = json.loads((repo / "configs/v3/FREEZE.json").read_bytes())
    if freeze.get("status") != "frozen":
        raise ValueError("Expected the archived frozen manifest")
    original = git(repo, "show", f"{freeze['source_commit']}:{SUITES}")
    if digest(original) != freeze["files"][SUITES]:
        raise ValueError("Pre-final suite manifest does not match its frozen hash")
    manifest = json.loads((repo / SUITES).read_bytes())
    if {k: v for k, v in manifest.items() if k != "final"} != json.loads(original):
        raise ValueError("Only the documented final entry may differ from the pre-final manifest")
    for rel, expected in freeze["files"].items():
        if rel != SUITES and digest((repo / rel).read_bytes()) != expected:
            raise ValueError(f"Frozen input changed: {rel}")
    generator = repo / "src/csci645_handover/v3_protocol.py"
    if generator.relative_to(repo).as_posix() not in freeze["files"]:
        raise ValueError("Suite generator is not hash-covered")
    spec = importlib.util.spec_from_file_location("archived_v3_protocol", generator)
    module = importlib.util.module_from_spec(spec)
    old_bytecode = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = old_bytecode
    contents, verified = {}, {}
    for split in ("development", "validation", "final"):
        rows = module.make_cases(split)
        data = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows).encode()
        rel = f"configs/v3/suites/{split}.jsonl"
        expected = {"path": rel, "cases": len(rows), "sha256": digest(data)}
        if manifest.get(split) != expected or (repo / rel).read_bytes() != data:
            raise ValueError(f"Rebuilt suite or manifest differs: {split}")
        contents[split] = data
        verified[split] = expected
    audit = {"experiment_commit": EXPERIMENT, "frozen_inputs_verified": len(freeze["files"]),
             "suites": verified, "historical_manifest_exception": {
                 "path": SUITES, "source_commit": freeze["source_commit"],
                 "frozen_sha256": digest(original),
                 "reason": "The final suite entry was appended after freeze; original Git bytes and every final entry field were checked."},
             "simulator_run": False, "new_preregistration": False}
    if output is not None:
        output = Path(output).resolve()
        # An existing output directory is never reused, even if empty.
        output.mkdir(parents=True, exist_ok=False)
        for split, data in contents.items():
            (output / f"{split}.jsonl").write_bytes(data)
        (output / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    return audit


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-repo", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--output", help="New directory for copies of all three verified suites and audit.json")
    args = parser.parse_args()
    print(json.dumps(rebuild(args.experiment_repo, args.output), indent=2))
