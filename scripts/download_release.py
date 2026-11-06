#!/usr/bin/env python3
"""Download every asset of a public GitHub Release anonymously (no credentials, standard library only).

    python3 scripts/download_release.py --tag v1.0.0 --output downloads/v1.0.0
    python3 scripts/download_release.py --tag v2.0.0 --output downloads/v2.0.0 --repo ywen0511/CSCI645-Project

Refuses a non-empty output directory. Writes ``download_log.json`` (asset names, sizes, URLs, UTC time).
Verify afterwards with ``sha256sum -c SHA256SUMS`` and ``scripts/verify_archives.py``.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path


def get_json(url: str):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "csci645-dl"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default="ywen0511/CSCI645-Project")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    out = Path(a.output)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} is not empty")
    out.mkdir(parents=True, exist_ok=True)
    rel = get_json(f"https://api.github.com/repos/{a.repo}/releases/tags/{a.tag}")
    log = {"repo": a.repo, "tag": a.tag, "release_url": rel["html_url"], "published_at": rel.get("published_at"),
           "draft": rel.get("draft"), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "assets": []}
    for asset in rel["assets"]:
        dest = out / asset["name"]
        url = asset["browser_download_url"]
        req = urllib.request.Request(url, headers={"User-Agent": "csci645-dl"})
        with urllib.request.urlopen(req, timeout=600) as r, open(dest, "wb") as f:
            while True:
                block = r.read(1 << 20)
                if not block:
                    break
                f.write(block)
        size = dest.stat().st_size
        if size != asset["size"]:
            raise SystemExit(f"{asset['name']}: size {size} != {asset['size']}")
        log["assets"].append({"name": asset["name"], "size": size, "url": url})
        print(f"{asset['name']}: {size} bytes")
    (out / "download_log.json").write_text(json.dumps(log, indent=2))
    print(f"downloaded {len(log['assets'])} assets to {out}")


if __name__ == "__main__":
    main()
