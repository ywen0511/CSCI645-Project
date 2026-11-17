#!/usr/bin/env python3
"""Build the v4.0.1 patch release directory (CPU, standard library).

    python3 -I scripts/v4_patch_release.py --tag v4.0.1 --data-download-log <download_log.json of v4.0.0> --output <new dir>

v4.0.1 fixes the delivery source only: tag v4.0.0 lacked the GPU verification stage used by REPRODUCE section 3. The
experiment source (experiment-v4), every checkpoint, record, video and document of the study stay in release v4.0.0,
unchanged. This patch release contains the source archive of the v4.0.1 delivery commit, the corrected REPRODUCE.md and
VERIFICATION.md, its release notes, and release_manifest.json listing its own assets plus every v4.0.0 data asset by
name, size and SHA-256 (taken from an anonymous v4.0.0 download), then SHA256SUMS (no self-hash).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", default="v4.0.1")
    ap.add_argument("--data-download-log", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    git = lambda *x: subprocess.run(["git", "-C", str(ROOT), *x], capture_output=True, check=True).stdout  # noqa: E731
    head = git("rev-parse", "HEAD").decode().strip()
    if head != git("rev-parse", f"{a.tag}^{{commit}}").decode().strip() or git("status", "--porcelain", "--untracked-files=no"):
        raise SystemExit("run from a clean checkout of the tag")
    O = Path(a.output)
    O.mkdir(parents=True, exist_ok=False)
    (O / f"source-{a.tag}.tar.gz").write_bytes(git("archive", "--format=tar.gz", f"--prefix=CSCI645-Project-{a.tag}/", a.tag))
    for name, rel in (("REPRODUCE.md", "docs/v4/REPRODUCE.md"), ("VERIFICATION.md", "docs/v4/VERIFICATION.md"),
                      ("RELEASE_NOTES.md", "docs/v4/RELEASE_NOTES_v4.0.1.md")):
        (O / name).write_bytes((ROOT / rel).read_bytes())
    log = json.loads(Path(a.data_download_log).read_text())
    if log.get("tag") != "v4.0.0" or not log.get("anonymous"):
        raise SystemExit("expected an anonymous v4.0.0 download log")
    man = {"release": a.tag, "delivery_commit": head, "experiment_tag": "experiment-v4",
           "experiment_commit": git("rev-parse", "experiment-v4^{commit}").decode().strip(),
           "data_release": "v4.0.0", "note": "all study data (checkpoints, records, logs, videos, report, slides) are the v4.0.0 assets below, unchanged",
           "assets": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in sorted(O.iterdir())],
           "v4.0.0_assets": [{"name": x["name"], "bytes": x["bytes"], "sha256": x["sha256"], "url": x["url"]} for x in log["assets"]]}
    (O / "release_manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    (O / "SHA256SUMS").write_text("".join(f"{sha(p)}  {p.name}\n" for p in sorted(O.iterdir())))
    print(json.dumps({"assets": len(list(O.iterdir())), "delivery_commit": head, "v4.0.0_assets": len(man["v4.0.0_assets"])}))


if __name__ == "__main__":
    main()
