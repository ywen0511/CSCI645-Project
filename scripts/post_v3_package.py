#!/usr/bin/env python3
"""Build the v3.0.1 maintenance release bundle (CPU, standard library only).

    python3 -I scripts/post_v3_package.py --original <dir with the 30 v3.0.0 assets> \
        --original-download-log <download_log.json of an anonymous v3.0.0 download> \
        --repo <maintenance checkout at the source tag> --source-tag maintenance-v3.0.1 --tag v3.0.1 --output <new dir>

Layout (every file is a GitHub release asset):

  v3.0.0-original-assets.tar     all 30 published v3.0.0 assets, byte-identical, at the archive root (uncompressed,
                                 deterministic member order/metadata). Extract it into an empty directory and the
                                 original v3.0.0 verifier (scripts/v3_verify.py at tag v3.0.0) runs unchanged on it.
  source-maintenance-v3.0.1.tar.gz   git archive of the maintenance source tag (tooling, docs, evidence)
  maintenance-evidence.tar.gz    results/post_v3 (CPU and Stage A GPU acceptance evidence), docs/post_v3,
                                 maintenance docs, status and the maintenance scripts, as committed at the tag
  MAINTENANCE_RELEASE_NOTES.md, MAINTENANCE.md, REPRODUCE.md (revised V3 instructions), POST_V3_STATUS.json
  checkpoint_locations.json      every v3.0.0 checkpoint index entry -> nested location (this release's asset,
                                 original asset inside it, member inside that) with size and SHA-256
  archive_inventories.json       member lists (path, size, SHA-256) of every archive in this release, including
                                 the nested original tar
  release_manifest.json          provenance (experiment, delivery and tooling commits), layout, every asset with
                                 size/SHA-256, and the original v3.0.0 asset list cross-checked against the
                                 anonymous v3.0.0 download log and the original SHA256SUMS
  SHA256SUMS                     every other asset (no self-hash)

The packager refuses a non-empty output directory and fails if an original asset differs from the download log.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path

EXPERIMENT_SHA = "3811f5da5ef55638f95f7306e449609877f546df"
DELIVERY_SHA = "ebfa328b17103c32ae19c13f0a6408ebc55a6459"
EVIDENCE_PATHS = ["results/post_v3", "docs/post_v3", "docs/v3/MAINTENANCE.md", "docs/v3/REPRODUCE.md",
                  "POST_V3_STATUS.json", "scripts/post_v3_cache_demo.py", "scripts/post_v3_replay_audit.py",
                  "scripts/post_v3_package.py", "scripts/post_v3_verify_release.py", "scripts/v3_jobs.py",
                  "scripts/v3_rebuild_suites.py", "scripts/v3_download.py", "tests/test_v3_maintenance.py"]
LOOSE = {"MAINTENANCE_RELEASE_NOTES.md": "docs/post_v3/RELEASE_NOTES_v3.0.1.md", "MAINTENANCE.md": "docs/v3/MAINTENANCE.md",
         "REPRODUCE.md": "docs/v3/REPRODUCE.md", "POST_V3_STATUS.json": "POST_V3_STATUS.json"}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def git(repo: Path, *args, binary=False):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True)
    return r.stdout if binary else r.stdout.decode().strip()


def add_file(tar: tarfile.TarFile, name: str, data: bytes):
    ti = tarfile.TarInfo(name)
    ti.size, ti.mtime, ti.mode, ti.uid, ti.gid, ti.uname, ti.gname = len(data), 0, 0o644, 0, 0, "", ""
    tar.addfile(ti, io.BytesIO(data))


def inventory_tar(p: Path) -> list[dict]:
    out = []
    with tarfile.open(p) as t:
        for m in t:
            if m.isfile():
                data = t.extractfile(m).read()
                out.append({"path": m.name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
            elif not m.isdir():
                raise SystemExit(f"{p.name}: unsupported member type {m.name}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--original", required=True)
    ap.add_argument("--original-download-log", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--source-tag", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    O, OUT, repo = Path(a.original), Path(a.output), Path(a.repo)
    OUT.mkdir(parents=True, exist_ok=True)
    if any(OUT.iterdir()):
        raise SystemExit(f"{OUT} is not empty")
    tooling_sha = git(repo, "rev-parse", f"{a.source_tag}^{{commit}}")
    if git(repo, "rev-parse", "HEAD") != tooling_sha or git(repo, "status", "--porcelain", "--untracked-files=no"):
        raise SystemExit("repo must be a clean checkout of the source tag")

    # --- original assets: must equal the anonymous v3.0.0 download, byte for byte
    log = json.loads(Path(a.original_download_log).read_text())
    if log.get("tag") != "v3.0.0":
        raise SystemExit("download log is not for v3.0.0")
    originals = []
    for x in sorted(log["assets"], key=lambda x: x["name"]):
        p = O / x["name"]
        if sha(p) != x["sha256"] or p.stat().st_size != x["bytes"]:
            raise SystemExit(f"original asset differs from the public download: {x['name']}")
        originals.append({"name": x["name"], "bytes": x["bytes"], "sha256": x["sha256"], "v3.0.0_url": x["url"]})
    if sorted(p.name for p in O.iterdir() if p.is_file()) != [x["name"] for x in originals]:
        raise SystemExit("original directory has files that are not v3.0.0 assets (or misses some)")
    sums = {l.split()[1].lstrip("*"): l.split()[0] for l in (O / "SHA256SUMS").read_text().splitlines() if l.strip()}
    for x in originals:
        if x["name"] != "SHA256SUMS" and sums.get(x["name"]) != x["sha256"]:
            raise SystemExit(f"original SHA256SUMS disagrees for {x['name']}")
    nested = OUT / "v3.0.0-original-assets.tar"
    with tarfile.open(nested, "w", format=tarfile.PAX_FORMAT) as t:
        for x in originals:
            add_file(t, x["name"], (O / x["name"]).read_bytes())

    # --- new source and evidence archives
    src = OUT / f"source-maintenance-{a.tag}.tar.gz"
    src.write_bytes(git(repo, "archive", "--format=tar.gz", f"--prefix=CSCI645-Project-maintenance-{a.tag}/",
                        a.source_tag, binary=True))
    ev = OUT / "maintenance-evidence.tar.gz"
    files = sorted({f for p in EVIDENCE_PATHS for f in git(repo, "ls-files", "--", p).splitlines()})
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as t:
        for f in files:
            add_file(t, f, git(repo, "show", f"{a.source_tag}:{f}", binary=True))
    ev.write_bytes(gzip.compress(raw.getvalue(), mtime=0))
    for name, rel in LOOSE.items():
        (OUT / name).write_bytes(git(repo, "show", f"{a.source_tag}:{rel}", binary=True))

    # --- checkpoint locations through the nested archive
    ck = json.loads((O / "checkpoints.json").read_text())
    inv_orig = json.loads((O / "archive_inventories.json").read_text())
    locs = []
    for row in ck:
        locs.append({**{k: row[k] for k in ("run", "category", "tag", "roles", "sha256", "size_bytes", "identical_bytes_as")},
                     "asset": nested.name, "original_asset": row["asset"], "member": row["member"]})
    (OUT / "checkpoint_locations.json").write_text(json.dumps({
        "note": "Each entry: download this release's asset, extract original_asset from it, then member from that.",
        "count": len(locs), "checkpoints": locs}, indent=1) + "\n")

    # --- inventories and manifest
    inventories = {nested.name: inventory_tar(nested), src.name: inventory_tar(src), ev.name: inventory_tar(ev),
                   "nested_original_archive_inventories": "v3.0.0 archive_inventories.json (inside the nested tar)"}
    (OUT / "archive_inventories.json").write_text(json.dumps(inventories, indent=1) + "\n")
    assets = sorted(p for p in OUT.iterdir() if p.is_file())
    manifest = {
        "release": a.tag, "repository": "https://github.com/ywen0511/CSCI645-Project",
        "kind": "maintenance release of the V3 study; no new scientific result",
        "provenance": {"experiment_v3_tag": "experiment-v3", "experiment_v3_sha": EXPERIMENT_SHA,
                       "original_delivery_tag": "v3.0.0", "original_delivery_sha": DELIVERY_SHA,
                       "maintenance_source_tag": a.source_tag, "maintenance_tooling_sha": tooling_sha},
        "layout": __doc__.split("Layout (every file is a GitHub release asset):")[1].split("The packager refuses")[0].strip(),
        "assets": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in assets],
        "original_v3.0.0_assets": originals,
        "original_checks": {"matches_anonymous_download_log": True, "matches_original_SHA256SUMS": True,
                            "original_archive_member_inventory_entries": sum(len(v) for v in inv_orig.values()
                                                                             if isinstance(v, list))},
        "checkpoints": {"entries": len(locs), "index": "checkpoint_locations.json"},
    }
    (OUT / "release_manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    assets = sorted(p for p in OUT.iterdir() if p.is_file())
    (OUT / "SHA256SUMS").write_text("".join(f"{sha(p)}  {p.name}\n" for p in assets))
    print(json.dumps({"assets": len(assets) + 1, "bytes": sum(p.stat().st_size for p in OUT.iterdir()),
                      "tooling_sha": tooling_sha, "checkpoints": len(locs)}))


if __name__ == "__main__":
    main()
