#!/usr/bin/env python3
"""Assemble the closeout release directory (CPU; standard library).

    python3 scripts/closeout_package.py --work <closeout work> --tag v2.1.0 --source-commit <sha to be tagged> \
        --output <release dir> --redact /private/prefix=<WORK> --redact-regex 'host[0-9]+=<cluster-node>'

Inputs (all must exist; a missing input aborts):
  <work>/inputs/v2.0.0/          the anonymously downloaded, checksum-verified v2.0.0 assets
  <work>/sim/{repeatability,throughput,negative}, <work>/{ledger,logs,env,records,lsf_logs}
  this checkout                  results/closeout, report/, docs/, configs/ (the commit given by --source-commit)

Release layout:
  * unchanged copies of every v2.0.0 checkpoint, raw-record, log and video archive and the corrected v1 report
    (same names, same bytes; the SHA-256 is checked against the v2.0.0 SHA256SUMS);
  * v2.0.0-originals.tar.gz: the v2.0.0 report, deck, reproduction guide, results/configs archives and indices,
    byte-identical, so the earlier delivery stays inspectable from this release alone;
  * new: closeout-repeatability.tar.gz, closeout-negative-controls.tar.gz, closeout-results.tar.gz,
    configs-and-docs.tar.gz, source-<tag>.tar.gz (git archive of --source-commit), revised documents;
  * indices: runs.json, checkpoints.json, videos.json, manifest.json, archive_inventories.json, SHA256SUMS
    (covers every asset except itself).
Text members of new archives are redacted (private path prefixes, host names); copied v2.0.0 archives were
redacted when v2.0.0 was built and are not modified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = {".json", ".jsonl", ".log", ".txt", ".md", ".csv", ".sh", ".yaml", ".py"}
REDACT: list[tuple[str, str]] = []
HOST_RES: list[tuple[re.Pattern, str]] = []
STAGE: Path | None = None
COPY_FROM_V2 = ["checkpoints-residual-seed11.tar.gz", "checkpoints-residual-seed22.tar.gz",
                "checkpoints-residual-seed33.tar.gz", "checkpoints-combined-seed11.tar.gz",
                "checkpoints-combined-seed22.tar.gz", "checkpoints-combined-seed33.tar.gz",
                "checkpoints-combined_no_phase-seed11.tar.gz", "checkpoints-combined_no_phase-seed22.tar.gz",
                "checkpoints-combined_no_phase-seed33.tar.gz", "checkpoints-pilot.tar.gz", "raw-final-eval.tar.gz",
                "raw-validation.tar.gz", "raw-development.tar.gz", "raw-pilot-eval.tar.gz", "raw-audit.tar.gz",
                "logs.tar.gz", "videos.tar.gz", "report-v1-corrected.pdf"]
V2_ORIGINALS = ["report.md", "report.pdf", "deck.pdf", "deck.pptx", "REPRODUCE.md", "results.tar.gz",
                "configs-and-docs.tar.gz", "runs.json", "checkpoints.json", "videos.json", "manifest.json",
                "archive_inventories.json", "SHA256SUMS"]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def redacted(src: Path) -> Path:
    if src.suffix not in TEXT:
        return src
    t = src.read_text(errors="replace")
    n = t
    for old, tok in REDACT:
        n = n.replace(old, tok)
    for rx, tok in HOST_RES:
        n = rx.sub(tok, n)
    if n == t:
        return src
    dst = STAGE / f"r{sum(1 for _ in STAGE.iterdir())}_{src.name}"
    dst.write_text(n)
    return dst


def make_tar(dest: Path, members: list[tuple[Path, str]], inv: dict, redact=True) -> None:
    rows, seen = [], set()
    with tarfile.open(dest, "w:gz", compresslevel=6) as tar:
        for src, arc in members:
            if not src.is_file():
                raise SystemExit(f"missing input for {dest.name}: {src}")
            if arc in seen:
                raise SystemExit(f"duplicate member {arc} in {dest.name}")
            seen.add(arc)
            r = redacted(src) if redact else src
            ti = tar.gettarinfo(str(r), arcname=arc)
            ti.uid = ti.gid = 0
            ti.uname = ti.gname = ""
            ti.mtime = int(src.stat().st_mtime)
            ti.mode = 0o644
            with open(r, "rb") as f:
                tar.addfile(ti, f)
            rows.append({"path": arc, "size_bytes": r.stat().st_size, "sha256": sha(r)})
    inv[dest.name] = rows


def tree(base: Path, prefix: str, exclude=()) -> list[tuple[Path, str]]:
    if not base.exists():
        raise SystemExit(f"missing directory {base}")
    return [(p, f"{prefix}/{p.relative_to(base).as_posix()}") for p in sorted(base.rglob("*"))
            if p.is_file() and not any(x in p.parts for x in exclude)]


def git(*args) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout.strip()


def main():
    global STAGE
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", required=True)
    ap.add_argument("--tag", default="v2.1.0")
    ap.add_argument("--source-commit", required=True, help="commit the release tag will point to (clean)")
    ap.add_argument("--output", required=True)
    ap.add_argument("--redact", action="append", default=[], help="OLD=TOKEN")
    ap.add_argument("--redact-regex", action="append", default=[], help="REGEX=TOKEN")
    a = ap.parse_args()
    for r in a.redact:
        old, tok = r.split("=", 1)
        REDACT.append((old, tok))
    for r in a.redact_regex:
        rx, tok = r.rsplit("=", 1)
        HOST_RES.append((re.compile(rx), tok))
    W = Path(a.work).resolve()
    V2 = W / "inputs/v2.0.0"
    out = Path(a.output)
    if out.exists():
        raise SystemExit(f"{out} exists; refusing to overwrite")
    src_commit = git("rev-parse", a.source_commit)
    if git("rev-parse", "HEAD") != src_commit or git("status", "--porcelain", "--untracked-files=no"):
        raise SystemExit("package from a clean checkout at --source-commit (documents must match the tagged source)")
    out.mkdir(parents=True)
    STAGE = Path(tempfile.mkdtemp(prefix="pkg_closeout_"))
    inv: dict = {}
    v2sums = {l.split()[1]: l.split()[0] for l in (V2 / "SHA256SUMS").read_text().splitlines() if l.strip()}
    v2inv = json.loads((V2 / "archive_inventories.json").read_text())

    # ---- 1. unchanged copies of v2.0.0 archives
    copied = []
    for n in COPY_FROM_V2:
        if sha(V2 / n) != v2sums[n]:
            raise SystemExit(f"{n}: downloaded file does not match the v2.0.0 SHA256SUMS")
        shutil.copy2(V2 / n, out / n)
        if n in v2inv:
            inv[n] = v2inv[n]
        copied.append({"name": n, "sha256": v2sums[n], "copied_from": "v2.0.0"})
    # ---- 2. v2.0.0 originals (byte-identical) in one archive
    make_tar(out / "v2.0.0-originals.tar.gz", [(V2 / n, f"v2.0.0/{n}") for n in V2_ORIGINALS], inv, redact=False)
    # ---- 3. new closeout evidence
    rep = (tree(W / "sim/repeatability", "closeout/sim/repeatability") + tree(W / "sim/throughput", "closeout/sim/throughput")
           + [(p, f"closeout/ledger/{p.name}") for p in sorted((W / "ledger").glob("*.jsonl"))
              if p.name.startswith(("b900_", "b23_", "throughput_"))]
           + [(p, f"closeout/logs/{p.name}") for p in sorted((W / "logs").glob("*.log"))
              if p.name.startswith(("b900_", "b23_", "throughput_"))]
           + [(p, f"closeout/env/{p.name}") for p in sorted((W / "env").glob("*"))
              if p.name.startswith(("repeatability", "throughput"))]
           + [(p, f"closeout/records/{p.name}") for p in sorted((W / "records").glob("*.json"))
              if p.name.startswith(("repeatability", "throughput", "checkout", "download"))]
           + [(p, f"closeout/lsf_logs/{p.name}") for p in sorted((W / "lsf_logs").glob("*.log"))
              if p.name.startswith(("rep_", "throughput", "setup"))])
    make_tar(out / "closeout-repeatability.tar.gz", rep, inv)
    neg = (tree(W / "sim/negative", "closeout/sim/negative")
           + [(p, f"closeout/logs/{p.name}") for p in sorted((W / "logs").glob("negative_*.log"))]
           + [(p, f"closeout/env/{p.name}") for p in sorted((W / "env").glob("negative*"))]
           + [(p, f"closeout/records/{p.name}") for p in sorted((W / "records").glob("negative.json"))]
           + [(p, f"closeout/lsf_logs/{p.name}") for p in sorted((W / "lsf_logs").glob("negative*.log"))])
    make_tar(out / "closeout-negative-controls.tar.gz", neg, inv)
    res = (tree(ROOT / "results/closeout", "results/closeout") + tree(ROOT / "report/closeout", "report/closeout")
           + tree(W / "regen", "closeout/regen"))
    make_tar(out / "closeout-results.tar.gz", res, inv)
    cfg = (tree(ROOT / "configs", "configs") + tree(ROOT / "docs", "docs") + tree(ROOT / "report", "report",
                                                                                  exclude=("deck",)))
    make_tar(out / "configs-and-docs.tar.gz", cfg, inv)
    srcp = STAGE / f"source-{a.tag}.tar.gz"
    subprocess.run(["git", "-C", str(ROOT), "archive", "--format=tar.gz", f"--prefix=CSCI645-Project-{a.tag}/",
                    "-o", str(srcp), src_commit], check=True)
    shutil.copy2(srcp, out / f"source-{a.tag}.tar.gz")
    with tarfile.open(srcp) as t:
        inv[f"source-{a.tag}.tar.gz"] = [{"path": m.name, "size_bytes": m.size} for m in t.getmembers() if m.isfile()]
    # ---- 4. documents
    docs = [(ROOT / "report/v2/report.md", "report.md"), (ROOT / "report/v2/report.pdf", "report.pdf"),
            (ROOT / "report/v2/deck/deck.pptx", "deck.pptx"), (ROOT / "report/v2/deck/deck.pdf", "deck.pdf"),
            (ROOT / "report/closeout/repeatability.md", "repeatability.md"),
            (ROOT / "docs/closeout/ERRATA.md", "ERRATA.md"), (ROOT / "docs/closeout/REPRODUCE.md", "REPRODUCE.md"),
            (ROOT / "docs/closeout/VERIFICATION.md", "VERIFICATION.md")]
    for s, n in docs:
        if not s.exists():
            raise SystemExit(f"missing {s}")
        shutil.copy2(redacted(s), out / n)
    # ---- 5. indices
    v2runs = json.loads((V2 / "runs.json").read_text())
    for r in v2runs:
        r["evidence"] = "original v2 (v2.0.0)"
    rman = json.loads((ROOT / "results/closeout/repeatability/run_manifest.json").read_text())
    led = {}
    for p in (W / "ledger").glob("*.jsonl"):
        for l in p.read_text().splitlines():
            x = json.loads(l)
            led.setdefault(x["task"], []).append({k: x.get(k) for k in ("attempt", "rc", "wall_s", "complete", "start")})
    runs = v2runs + [{"run_id": t["task"], "run_type": "supplementary_evaluation", "evidence": "closeout Stage 4",
                      "entry": t["entry"], "batch_size": t["batch_size"], "repeat": t["repeat"],
                      "process_seed": t["process_seed"], "scheduled": t["scheduled"],
                      "attempts": led.get(t["task"], []), "asset": "closeout-repeatability.tar.gz",
                      "member_prefix": f"closeout/sim/{t['output']}/"} for t in rman["tasks"]]
    runs += [{"run_id": f"throughput_b{b}", "run_type": "throughput_check (not a result)", "evidence": "closeout Stage 4",
              "attempts": led.get(f"throughput_b{b}", []), "asset": "closeout-repeatability.tar.gz",
              "member_prefix": f"closeout/sim/throughput/b{b}/"} for b in (900, 23)]
    runs += [{"run_id": "negative_controls", "run_type": "negative_control", "evidence": "closeout Stage 2",
              "asset": "closeout-negative-controls.tar.gz", "member_prefix": "closeout/sim/negative/"}]
    (out / "runs.json").write_text(json.dumps(runs, indent=1, default=str) + "\n")
    ck = json.loads((V2 / "checkpoints.json").read_text())
    for e in ck:
        e["copied_from_release"] = "v2.0.0"
        e["asset_sha256"] = v2sums[e["asset"]]
    (out / "checkpoints.json").write_text(json.dumps(ck, indent=1) + "\n")
    vids = json.loads((V2 / "videos.json").read_text())
    vplan = json.loads((ROOT / "configs/closeout/video_plan.json").read_text())
    for v in vids:
        v["copied_from_release"] = "v2.0.0"
        v["replay_command_v2.0.0_note"] = ("the v2.0.0 replay_command text names configs/v2/protocol.json and a <plan.json> "
                                          "placeholder; the videos were recorded with configs/v2/frozen/protocol.json "
                                          "(sidecar protocol_sha256 bd79ae51...); see ERRATA C8")
        v["replay_command"] = ("python3 scripts/closeout.py --work <work> video-replay --only " + v["video"]
                               + "  # plan: configs/closeout/video_plan.json, protocol configs/v2/frozen/protocol.json")
        if not any(p["video"] == v["video"] for p in vplan["videos"]):
            raise SystemExit(f"{v['video']} missing from configs/closeout/video_plan.json")
    (out / "videos.json").write_text(json.dumps(vids, indent=1, default=str) + "\n")
    inv_all = {k: inv[k] for k in sorted(inv)}
    (out / "archive_inventories.json").write_text(json.dumps(inv_all, indent=1) + "\n")
    kinds = [("checkpoints-", "checkpoints (copied from v2.0.0)"), ("raw-", "raw records (copied from v2.0.0)"),
             ("logs", "logs (copied from v2.0.0)"), ("videos.tar", "videos (copied from v2.0.0)"),
             ("report-v1", "corrected v1 report (copied from v2.0.0)"), ("v2.0.0-originals", "v2.0.0 documents and indices"),
             ("closeout-", "closeout evidence"), ("configs-and-docs", "configs/docs/report sources"),
             ("source-", "source snapshot"), ("report", "report"), ("deck", "presentation"),
             ("repeatability", "supplementary report"), ("ERRATA", "errata"), ("REPRODUCE", "reproduction guide"),
             ("VERIFICATION", "verification record")]
    assets = []
    for f in sorted(out.iterdir()):
        if f.name in ("manifest.json", "SHA256SUMS"):
            continue
        kind = next((v for k, v in kinds if f.name.startswith(k)), "index")
        assets.append({"name": f.name, "size_bytes": f.stat().st_size, "sha256": sha(f), "kind": kind,
                       **({"copied_from": "v2.0.0"} if f.name in COPY_FROM_V2 else {})})
    man = {"tag": a.tag, "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "release_source_commit": src_commit,
           "experiment_tag": "experiment-v2", "experiment_commit": "1d9d0e23eec346c1b1cb3c0c245a1e772df7bedf",
           "supplementary_evaluation_tag": "closeout-eval-v1", "supplementary_evaluation_commit": git("rev-parse", "closeout-eval-v1^{commit}"),
           "v2_release_tag": "v2.0.0", "v2_release_commit": "86b193a439539dd88a98a0283c06293c0a1ac8aa",
           "protocol_sha256": sha(ROOT / "configs/v2/frozen/protocol.json"),
           "copied_unchanged_from_v2.0.0": copied,
           "v1_reference": {"release": "https://github.com/ywen0511/CSCI645-Project/releases/tag/v1.0.0",
                            "note": "v1-only checkpoints and raw records are historical evidence in the immutable v1.0.0 release"},
           "superseded": [e for e in ck if e.get("superseded")],
           "assets": assets, "redaction": [t for _, t in REDACT] + [t for _, t in HOST_RES]}
    (out / "manifest.json").write_text(json.dumps(man, indent=1, default=str) + "\n")
    with open(out / "SHA256SUMS", "w") as f:
        for x in sorted(out.iterdir()):
            if x.name != "SHA256SUMS":
                f.write(f"{sha(x)}  {x.name}\n")
    shutil.rmtree(STAGE)
    tot = sum(x.stat().st_size for x in out.iterdir())
    print(f"{len(list(out.iterdir()))} assets, {tot / 1e6:.1f} MB, {sum(len(v) for v in inv.values())} archive members")


if __name__ == "__main__":
    main()
