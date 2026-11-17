#!/usr/bin/env python3
"""Verify a v3 release directory (draft or fresh anonymous download). Exit code 1 on any failure.

    python3 -I scripts/v3_verify.py --bundle <dir> --extract <empty dir> --output verify.json

Checks: SHA256SUMS covers every asset except itself and matches; release_manifest lists every other asset with
matching size/hash; every archive member (including source archives) re-hashed against archive_inventories.json
with safe extraction; checkpoints.json entries resolve to members with matching hashes; all 23 formal runs exist
with step 0, ten periodic, final and latest checkpoints, and each selected tag resolves to a saved checkpoint;
final raw records: every executed final entry has 2,600 records; validation 138 entries x 240; videos decode
with sidecars; PDFs/PPTX open; leak scan of new text members.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tarfile
from pathlib import Path

LEAKS = [r"/data/rtxw01", r"/home/(?!conda/)[a-z0-9_]+/", r"dcwip\w+", r"\.gm\.com", r"kztrgg", r"nbak/robot_intel"]
FORMAL = {"combined_clean_ff": 5, "combined_robust_ff": 5, "combined_robust_history": 5, "residual_robust_history": 5,
          "combined_robust_repeat": 3}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--extract", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    B, X = Path(a.bundle), Path(a.extract)
    X.mkdir(parents=True, exist_ok=True)
    R, fail = {"checks": {}}, []
    files = sorted(p.name for p in B.iterdir() if p.is_file() and not p.name.startswith(".") and p.name != "download_log.json")
    sums = dict(reversed(l.split(None, 1)) for l in (B / "SHA256SUMS").read_text().splitlines() if l.strip())
    sums = {k.strip(): v for k, v in sums.items()}
    bad = [n for n, h in sums.items() if not (B / n).exists() or sha(B / n) != h]
    unl = [f for f in files if f not in sums and f != "SHA256SUMS"]
    R["checks"]["sha256sums"] = {"listed": len(sums), "assets": len(files), "bad": bad, "unlisted": unl}
    if bad or unl or "SHA256SUMS" in sums:
        fail.append("SHA256SUMS")
    man = json.loads((B / "release_manifest.json").read_text())
    mb = [x["name"] for x in man["assets"] if not (B / x["name"]).exists() or sha(B / x["name"]) != x["sha256"]]
    cover = sorted(x["name"] for x in man["assets"]) == sorted(f for f in files if f not in ("release_manifest.json", "SHA256SUMS"))
    R["checks"]["manifest"] = {"assets": len(man["assets"]), "bad": mb, "covers_all_other_assets": cover,
                               "experiment_commit": man["experiment_commit"], "delivery_commit": man["delivery_commit"]}
    if mb or not cover:
        fail.append("manifest")
    inv = json.loads((B / "archive_inventories.json").read_text())
    msha, probs, n = {}, [], 0
    for f in [f for f in files if f.endswith(".tar.gz")]:
        rows = {r["path"]: r for r in inv.get(f, [])}
        if not rows:
            probs.append(f"{f}: no inventory")
            continue
        seen = set()
        with tarfile.open(B / f) as t:
            for m in t.getmembers():
                if not m.isfile():
                    continue
                if m.name.startswith("/") or ".." in Path(m.name).parts:
                    probs.append(f"{f}: unsafe {m.name}")
                    continue
                data = t.extractfile(m).read()
                h = hashlib.sha256(data).hexdigest()
                msha[(f, m.name)] = h
                r = rows.get(m.name)
                if r is None or r.get("sha256") != h or r["size_bytes"] != len(data):
                    probs.append(f"{f}: {m.name}")
                seen.add(m.name)
                d = X / m.name
                d.parent.mkdir(parents=True, exist_ok=True)
                d.write_bytes(data)
                n += 1
        if set(rows) - seen:
            probs.append(f"{f}: {len(set(rows) - seen)} members missing")
    R["checks"]["archives"] = {"members_rehashed": n, "problems": probs[:30], "n_problems": len(probs)}
    if probs:
        fail.append("archives")
    ck = json.loads((B / "checkpoints.json").read_text())
    cbad = [c["member"] for c in ck if msha.get((c["asset"], c["member"])) != c["sha256"]]
    runs = json.loads((B / "run_index.json").read_text())
    formal = [r for r in runs if r["type"] == "final"]
    per_fam = {f: sum(1 for r in formal if r["family"] == f) for f in FORMAL}
    need = {"step_000000000", "final", "latest"}
    ck_ok = all(need <= {c["tag"] for c in ck if c["run"] == r["run"]}
                and sum(1 for c in ck if c["run"] == r["run"] and c["tag"].startswith("step_") and c["tag"] != "step_000000000") == 10
                and any(c["tag"] == r["selected"] for c in ck if c["run"] == r["run"]) for r in formal)
    R["checks"]["checkpoints"] = {"entries": len(ck), "unresolved_or_bad": cbad[:20], "formal_runs_per_family": per_fam,
                                  "each_formal_run_has_step0_10_periodic_final_latest_and_selected": ck_ok,
                                  "pilot_smoke_runs": sum(1 for r in runs if r["type"] != "final")}
    if cbad or per_fam != FORMAL or not ck_ok:
        fail.append("checkpoints")
    fin = [p for p in (X / "final").rglob("*.jsonl") if p.name not in ("eval_runs.jsonl",)]
    counts = {str(p.relative_to(X)): sum(1 for l in p.read_text().splitlines() if l.strip()) for p in fin}
    val = [p for p in (X / "validation").rglob("*.jsonl") if p.name != "eval_runs.jsonl"]
    vcounts = [sum(1 for l in p.read_text().splitlines() if l.strip()) for p in val]
    R["checks"]["raw_counts"] = {"final_files": len(fin), "final_all_2600": all(v == 2600 for v in counts.values()),
                                 "final_records": sum(counts.values()), "validation_files": len(val),
                                 "validation_all_240": all(v == 240 for v in vcounts)}
    if len(fin) != 50 or not all(v == 2600 for v in counts.values()) or len(val) != 138 or not all(v == 240 for v in vcounts):
        fail.append("raw counts")
    media = {}
    vids = json.loads((B / "videos.json").read_text())
    try:
        import imageio.v2 as iio2
        dec = []
        for v in vids:
            p = X / v["member"]
            rd = iio2.get_reader(p, "ffmpeg")
            k = sum(1 for _ in rd)
            rd.close()
            dec.append({"video": v["video"], "frames": k, "ok": k > 0 and (v.get("frames") in (None, k))})
        media["mp4"] = dec
        if not all(d["ok"] for d in dec) or len(dec) < 8:
            fail.append("videos")
    except ImportError:
        media["mp4"] = "imageio not installed"
    try:
        from pypdf import PdfReader
        media["pdf"] = {f: len(PdfReader(B / f).pages) for f in files if f.endswith(".pdf")}
    except ImportError:
        media["pdf"] = "pypdf not installed"
    try:
        from pptx import Presentation
        media["pptx"] = {f: len(Presentation(B / f).slides) for f in files if f.endswith(".pptx")}
    except ImportError:
        media["pptx"] = "python-pptx not installed"
    R["checks"]["media"] = media
    pats = [re.compile(p) for p in LEAKS]
    hits = []
    for (f, m), _ in msha.items():
        if f.startswith("source-") or not m.endswith((".json", ".jsonl", ".log", ".txt", ".md", ".csv", ".sh")):
            continue
        t = (X / m).read_text(errors="replace")
        hits += [f"{f}:{m}:{p.pattern}" for p in pats if p.search(t)]
    for f in files:
        if f.endswith((".json", ".md")):
            t = (B / f).read_text(errors="replace")
            hits += [f"{f}:{p.pattern}" for p in pats if p.search(t)]
    R["checks"]["leak_scan"] = {"hits": hits[:30], "n_hits": len(hits)}
    if hits:
        fail.append("leak scan")
    R["failures"], R["ok"] = fail, not fail
    Path(a.output).write_text(json.dumps(R, indent=1) + "\n")
    print(json.dumps({"ok": R["ok"], "failures": fail, **{k: {kk: vv for kk, vv in v.items() if kk not in ("problems", "hits", "mp4")}
                                                           if isinstance(v, dict) else v for k, v in R["checks"].items()}}, indent=1)[:4000])
    raise SystemExit(0 if R["ok"] else 1)


if __name__ == "__main__":
    main()
