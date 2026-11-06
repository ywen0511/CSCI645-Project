#!/usr/bin/env python3
"""Verify a closeout release directory (a local draft or a fresh anonymous download).

    python3 -I scripts/closeout_verify.py --bundle <dir> --extract <empty dir> --output verify.json \
        [--leak-pattern REGEX ...]

Checks: SHA256SUMS covers every asset except itself and every hash matches; manifest sizes/hashes; every archive
member re-hashed against archive_inventories.json (no unlisted or missing members); checkpoint, run and video
indices resolve to uploaded assets/members with matching hashes; every final run has untrained/selected/final/
resume roles and 11 periodic checkpoints; copied v2.0.0 assets keep their v2.0.0 hashes; repeatability record
counts; media (MP4 decode + frame counts, PDF page counts, PPTX slide count) when imageio/pypdf/python-pptx are
installed; leak scan of text members. Standard library for the integrity checks; exit code 1 on any failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tarfile
from pathlib import Path

DEFAULT_LEAKS = [r"/data/rtxw01", r"/home/(?!conda/)[a-z0-9_]+/", r"dcwip\w+", r"\.gm\.com", r"kztrgg", r"nbak/robot_intel"]
# /home/conda/... is the generic conda-forge build path recorded in pip freeze (also in the committed lock)


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
    ap.add_argument("--leak-pattern", action="append", default=None)
    a = ap.parse_args()
    B, X = Path(a.bundle), Path(a.extract)
    X.mkdir(parents=True, exist_ok=True)
    R: dict = {"bundle": B.name, "checks": {}, "failures": []}

    def fail(msg):
        R["failures"].append(msg)

    files = sorted(p.name for p in B.iterdir() if p.is_file() and not p.name.startswith(".")
                   and p.name != "download_log.json")
    sums = {}
    for line in (B / "SHA256SUMS").read_text().splitlines():
        if line.strip():
            h, n = line.split(None, 1)
            sums[n.strip().lstrip("*")] = h
    bad = [n for n, h in sums.items() if not (B / n).exists() or sha(B / n) != h]
    unlisted = [f for f in files if f not in sums and f != "SHA256SUMS"]
    R["checks"]["sha256sums"] = {"listed": len(sums), "assets": len(files), "mismatch_or_missing": bad, "unlisted": unlisted}
    if bad or unlisted or "SHA256SUMS" in sums:
        fail("SHA256SUMS")
    man = json.loads((B / "manifest.json").read_text())
    mbad = [x["name"] for x in man["assets"] if not (B / x["name"]).exists() or sha(B / x["name"]) != x["sha256"]
            or (B / x["name"]).stat().st_size != x["size_bytes"]]
    R["checks"]["manifest"] = {"assets": len(man["assets"]), "bad": mbad,
                               "covers_all_but_manifest_and_sums": sorted(x["name"] for x in man["assets"])
                               == sorted(f for f in files if f not in ("manifest.json", "SHA256SUMS"))}
    if mbad or not R["checks"]["manifest"]["covers_all_but_manifest_and_sums"]:
        fail("manifest")
    copied_bad = [c["name"] for c in man.get("copied_unchanged_from_v2.0.0", []) if sums.get(c["name"]) != c["sha256"]]
    R["checks"]["copied_from_v2.0.0"] = {"n": len(man.get("copied_unchanged_from_v2.0.0", [])), "hash_changed": copied_bad}
    if copied_bad:
        fail("copied v2.0.0 assets changed")

    # ---- archives
    inv = json.loads((B / "archive_inventories.json").read_text())
    arch = [f for f in files if f.endswith(".tar.gz")]
    members_total, mism = 0, []
    member_sha: dict[tuple[str, str], str] = {}
    for f in arch:
        rows = {r["path"]: r for r in inv.get(f, [])}
        if not rows:
            mism.append(f"{f}: no inventory")
            continue
        seen = set()
        with tarfile.open(B / f) as t:
            for m in t.getmembers():
                if not m.isfile():
                    continue
                if m.name.startswith("/") or ".." in Path(m.name).parts:
                    mism.append(f"{f}: unsafe path {m.name}")
                    continue
                seen.add(m.name)
                data = t.extractfile(m).read()
                h = hashlib.sha256(data).hexdigest()
                member_sha[(f, m.name)] = h
                r = rows.get(m.name)
                if r is None:
                    mism.append(f"{f}: unlisted {m.name}")
                elif ("sha256" in r and r["sha256"] != h) or r["size_bytes"] != len(data):
                    mism.append(f"{f}: hash/size {m.name}")
                dest = X / m.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                members_total += 1
        missing = set(rows) - seen
        if missing:
            mism.append(f"{f}: {len(missing)} inventory members missing")
    R["checks"]["archives"] = {"archives": len(arch), "members_rehashed": members_total, "problems": mism[:50],
                               "n_problems": len(mism)}
    if mism:
        fail("archives")

    # ---- indices
    ck = json.loads((B / "checkpoints.json").read_text())
    cbad, sup = [], 0
    for e in ck:
        key = (e["asset"], e["member"])
        want = e.get("sha256") or e.get("ledger_sha256")
        if e.get("superseded"):
            sup += 1
            continue
        if key not in member_sha:
            cbad.append(f"unresolved {e['member']}")
        elif member_sha[key] != want:
            cbad.append(f"hash {e['member']}")
    runs_final = {e["run_id"] for e in ck if e["run_type"] == "final"}
    roles_ok = all({e.get("role") for e in ck if e["run_id"] == r and e.get("role")} >= {"untrained", "selected", "final", "resume"}
                   and sum(1 for e in ck if e["run_id"] == r and e.get("tag", "").startswith("step_")
                           and not e.get("superseded")) == 11 for r in runs_final)  # step 0 + 10 periodic
    R["checks"]["checkpoints_index"] = {"entries": len(ck), "superseded": sup, "problems": cbad, "final_runs": len(runs_final),
                                        "all_final_runs_have_roles_and_11_periodic": roles_ok}
    if cbad or len(runs_final) != 9 or not roles_ok:
        fail("checkpoints index")
    runs = json.loads((B / "runs.json").read_text())
    rbad = []
    for r in runs:
        if "member_prefix" in r:
            if not any(k[0] == r["asset"] and k[1].startswith(r["member_prefix"]) for k in member_sha):
                rbad.append(r["run_id"])
    R["checks"]["runs_index"] = {"entries": len(runs), "closeout_unresolved": rbad,
                                 "types": sorted({r["run_type"] for r in runs if r.get("run_type")})}
    if rbad:
        fail("runs index")
    vids = json.loads((B / "videos.json").read_text())
    vbad = [v["video"] for v in vids if member_sha.get(("videos.tar.gz", v["member"])) != v["sha256"]]
    sides = [v["video"] for v in vids if ("videos.tar.gz", v["member"].replace(".mp4", ".json")) not in member_sha]
    R["checks"]["videos_index"] = {"videos": len(vids), "hash_problems": vbad, "missing_sidecars": sides,
                                   "replay_matches_evaluation": sum(bool(v.get("replay_matches_evaluation")) for v in vids)}
    if vbad or sides or len(vids) < 10:
        fail("videos index")

    # ---- repeatability record counts
    rec = 0
    for (f, m), _ in member_sha.items():
        if f == "closeout-repeatability.tar.gz" and m.startswith("closeout/sim/repeatability/") and m.endswith(".jsonl") \
                and not m.endswith("eval_runs.jsonl"):
            rec += sum(1 for l in (X / m).read_text().splitlines() if l.strip())
    R["checks"]["repeatability_records"] = rec
    if rec != 115200:
        fail(f"repeatability records {rec} != 115200")

    # ---- media
    media = {}
    try:
        import imageio.v2 as iio2
        dec = []
        for v in vids:
            rd = iio2.get_reader(X / v["member"], "ffmpeg")  # decodes every frame
            n, shape = 0, None
            for fr in rd:
                n += 1
                shape = fr.shape
            rd.close()
            w, h = v.get("resolution", [0, 0])  # decoders may pad the height to a multiple of 16 (540 -> 544)
            ok = n == v.get("frames") and shape is not None and shape[1] == w and 0 <= shape[0] - h < 16
            dec.append({"video": v["video"], "frames_decoded": n, "index_frames": v.get("frames"),
                        "frame_shape": list(shape) if shape is not None else None, "ok": ok})
        media["mp4"] = dec
        if not all(d["ok"] for d in dec):
            fail("video decode/frame count")
    except ImportError:
        media["mp4"] = "imageio not installed: not checked"
    try:
        from pypdf import PdfReader
        media["pdf"] = {f: len(PdfReader(B / f).pages) for f in files if f.endswith(".pdf")}
    except ImportError:
        media["pdf"] = "pypdf not installed: not checked"
    try:
        from pptx import Presentation
        media["pptx"] = {f: len(Presentation(B / f).slides) for f in files if f.endswith(".pptx")}
    except ImportError:
        media["pptx"] = "python-pptx not installed: not checked"
    R["checks"]["media"] = media

    # ---- leak scan (text members of new closeout archives + loose text assets)
    pats = [re.compile(p) for p in (a.leak_pattern or DEFAULT_LEAKS)]
    hits = []
    copied = {c["name"] for c in man.get("copied_unchanged_from_v2.0.0", [])} | {"v2.0.0-originals.tar.gz"}
    for (f, m), _ in member_sha.items():
        if f in copied or not m.endswith((".json", ".jsonl", ".log", ".txt", ".md", ".csv", ".sh", ".py")) \
                or m.endswith("scripts/closeout_verify.py"):  # the scanner's own pattern list
            continue
        t = (X / m).read_text(errors="replace")
        for p in pats:
            if p.search(t):
                hits.append(f"{f}:{m}: {p.pattern}")
    for f in files:
        if f.endswith((".json", ".md")) and f != "SHA256SUMS":
            t = (B / f).read_text(errors="replace")
            for p in pats:
                if p.search(t):
                    hits.append(f"{f}: {p.pattern}")
    R["checks"]["leak_scan"] = {"patterns": [p.pattern for p in pats], "hits": hits[:50], "n_hits": len(hits),
                                "scope": "text members of archives created for this release and loose JSON/Markdown "
                                         "assets (copied v2.0.0 archives were scanned when v2.0.0 was released)"}
    if hits:
        fail("leak scan")
    R["ok"] = not R["failures"]
    Path(a.output).write_text(json.dumps(R, indent=1) + "\n")
    print(json.dumps({k: (v if k != "checks" else {c: (x if not isinstance(x, dict) else {kk: vv for kk, vv in x.items()
                                                                                          if kk not in ("problems",)})
                                                     for c, x in v.items() if c != "media"}) for k, v in R.items()},
                     indent=1)[:4000])
    raise SystemExit(0 if R["ok"] else 1)


if __name__ == "__main__":
    main()
