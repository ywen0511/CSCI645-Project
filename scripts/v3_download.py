#!/usr/bin/env python3
"""Anonymously download every asset of a public GitHub release into an empty directory (standard library only;
no token or credential is read or sent).

    python3 -I scripts/v3_download.py --tag v3.0.0 --output <empty dir>

Lists assets through the public REST API, downloads each from its public browser_download_url, and writes
download_log.json (asset name, URL, bytes, SHA-256, UTC time). Refuses a non-empty output directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.request
from pathlib import Path

REPO = "ywen0511/CSCI645-Project"


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "csci645-v3-verify", "Accept": "application/octet-stream"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                return r.read()
        except Exception:  # noqa: BLE001
            if attempt == 4:
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("unreachable")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", default="v3.0.0")
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    out = Path(a.output)
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise SystemExit(f"{out} is not empty")
    rel = json.loads(urllib.request.urlopen(urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/releases/tags/{a.tag}", headers={"User-Agent": "csci645-v3-verify"}), timeout=60).read())
    log = {"repo": REPO, "tag": a.tag, "release_url": rel["html_url"], "published_at": rel.get("published_at"),
           "anonymous": True, "assets": []}
    for x in sorted(rel["assets"], key=lambda x: x["name"]):
        data = get(x["browser_download_url"])
        if len(data) != x["size"]:
            raise SystemExit(f"{x['name']}: {len(data)} bytes, API says {x['size']}")
        (out / x["name"]).write_bytes(data)
        log["assets"].append({"name": x["name"], "url": x["browser_download_url"], "bytes": len(data),
                              "sha256": hashlib.sha256(data).hexdigest(), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        print(f"{x['name']}: {len(data):,} bytes", flush=True)
    (out / "download_log.json").write_text(json.dumps(log, indent=1) + "\n")
    print(f"{len(log['assets'])} assets, {sum(x['bytes'] for x in log['assets']) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
