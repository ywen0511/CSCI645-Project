#!/usr/bin/env python3
"""Check fresh anonymous downloads of the inherited V4 releases against INHERITED_ASSETS.json (standard library).

    python3 -I scripts/v3_download.py --tag v4.0.0 --output <dir>/v4.0.0
    python3 -I scripts/v3_download.py --tag v4.0.1 --output <dir>/v4.0.1
    python3 -I scripts/final_review_inherited_check.py --index results/final_review/INHERITED_ASSETS.json \
        --downloads <dir> --output inherited.json

Every indexed asset must exist in <dir>/<tag>/, be re-hashed from disk, and match the indexed size, SHA-256 and
public URL recorded in that tag's download_log.json. Each release must contain exactly the indexed asset set.
"""
import argparse
import hashlib
import json
from pathlib import Path


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--index", required=True)
    ap.add_argument("--downloads", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    index = json.loads(Path(a.index).read_text())
    out = {"releases": [], "assets": [], "passed": True}
    for rel in index["releases"]:
        d = Path(a.downloads) / rel["tag"]
        log = json.loads((d / "download_log.json").read_text())
        logged = {x["name"]: x for x in log["assets"]}
        names = {x["name"] for x in rel["assets"]}
        set_ok = set(logged) == names
        out["releases"].append({"tag": rel["tag"], "url": rel["url"], "indexed_assets": len(names),
                                "downloaded_assets": len(logged), "anonymous": bool(log.get("anonymous")),
                                "exact_asset_set": set_ok})
        out["passed"] &= set_ok and bool(log.get("anonymous"))
        for x in rel["assets"]:
            p = d / x["name"]
            r = {"tag": rel["tag"], "name": x["name"], "url": x["url"], "bytes": x["bytes"], "sha256": x["sha256"]}
            if not p.is_file():
                r.update(present=False, passed=False)
            else:
                got_bytes, got_sha = p.stat().st_size, sha(p)
                lg = logged.get(x["name"], {})
                r.update(present=True, downloaded_bytes=got_bytes, downloaded_sha256=got_sha,
                         size_ok=got_bytes == x["bytes"], sha256_ok=got_sha == x["sha256"],
                         url_ok=lg.get("url") == x["url"], log_sha256_ok=lg.get("sha256") == got_sha)
                r["passed"] = r["size_ok"] and r["sha256_ok"] and r["url_ok"] and r["log_sha256_ok"]
            out["passed"] &= r["passed"]
            out["assets"].append(r)
    out["assets_checked"] = len(out["assets"])
    out["assets_passed"] = sum(r["passed"] for r in out["assets"])
    Path(a.output).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("passed", "assets_checked", "assets_passed")}))
    raise SystemExit(0 if out["passed"] else 1)


if __name__ == "__main__":
    main()
