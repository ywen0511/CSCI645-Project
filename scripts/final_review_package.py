#!/usr/bin/env python3
"""Build or verify a CPU-review release package. No GPU or network access.

Build from a clean committed checkout:
  python scripts/final_review_package.py build --directory release_assets/final-review
Verify after a fresh public download:
  python scripts/final_review_package.py verify --directory downloads/final-review-release
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
FILES = ["report/final/overview.pdf", "report/final/overview.md", "report/final/boundary_sensitivity.png",
         "docs/final_review/REVIEW.md", "docs/final_review/DEFENSE_NOTES.md", "docs/final_review/RELEASE_NOTES.md",
         "results/final_review/audit.json", "results/final_review/INHERITED_ASSETS.json"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode().strip()


def build(directory):
    require(not git("status", "--porcelain"), "commit all changes before packaging")
    require(not directory.exists() or not any(directory.iterdir()), "use an empty package directory")
    directory.mkdir(parents=True, exist_ok=True)
    commit = git("rev-parse", "HEAD")
    require(json.loads((ROOT / "results/final_review/audit.json").read_text())["passed"], "audit failed")
    for rel in FILES:
        shutil.copyfile(ROOT / rel, directory / Path(rel).name)
    (directory / "SOURCE_COMMIT.txt").write_text(commit + "\n")
    subprocess.run(["git", "archive", "--format=tar.gz", "--prefix=CSCI645-Project/",
                    f"--output={directory.resolve() / 'source-review.tar.gz'}", commit], cwd=ROOT, check=True)
    assets = [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in sorted(directory.iterdir())]
    manifest = {"schema": 1, "source_commit": commit, "kind": "CPU review supplement; inherited study data unchanged",
                "assets": assets}
    (directory / "release_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (directory / "SHA256SUMS").write_text("".join(f"{sha(p)}  {p.name}\n" for p in sorted(directory.iterdir())
                                                 if p.name != "SHA256SUMS"))
    return verify(directory)


def verify(directory):
    manifest = json.loads((directory / "release_manifest.json").read_text())
    expected = {a["name"] for a in manifest["assets"]} | {"release_manifest.json", "SHA256SUMS"}
    require(expected == {Path(p).name for p in FILES} |
            {"SOURCE_COMMIT.txt", "source-review.tar.gz", "release_manifest.json", "SHA256SUMS"},
            "unexpected package asset set")
    require({p.name for p in directory.iterdir()} == expected, "missing or unlisted package assets")
    require(len(manifest["assets"]) == len(expected) - 2, "duplicate manifest names")
    for a in manifest["assets"]:
        require(Path(a["name"]).name == a["name"], "unsafe asset name")
        p = directory / a["name"]
        require(p.is_file() and not p.is_symlink(), "nonregular package asset")
        require(p.stat().st_size == a["bytes"] and sha(p) == a["sha256"], f"asset mismatch: {p.name}")
    sums = {}
    for line in (directory / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        require(name in expected - {"SHA256SUMS"} and name not in sums, "bad checksum list")
        require(sha(directory / name) == digest, f"checksum mismatch: {name}")
        sums[name] = digest
    require(set(sums) == expected - {"SHA256SUMS"}, "incomplete checksum list")
    require((directory / "SOURCE_COMMIT.txt").read_text().strip() == manifest["source_commit"], "source commit mismatch")
    require((directory / "overview.pdf").read_bytes().startswith(b"%PDF-"), "missing PDF")
    with tarfile.open(directory / "source-review.tar.gz") as tar:
        seen = set()
        for m in tar.getmembers():
            p = PurePosixPath(m.name)
            require(not p.is_absolute() and ".." not in p.parts and p.parts[0] == "CSCI645-Project", "unsafe archive path")
            require(m.name not in seen and (m.isfile() or m.isdir()), "duplicate or nonregular archive member")
            seen.add(m.name)
        for rel in FILES:
            archived = tar.extractfile("CSCI645-Project/" + rel).read()
            require(hashlib.sha256(archived).hexdigest() == sha(directory / Path(rel).name), f"source/package mismatch: {rel}")
    return {"passed": True, "assets": len(expected), "source_commit": manifest["source_commit"],
            "archive_members": len(seen), "scope": "local bytes and source consistency; no network or GPU replay"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["build", "verify"])
    p.add_argument("--directory", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(build(a.directory) if a.action == "build" else verify(a.directory), indent=2))


if __name__ == "__main__":
    main()
