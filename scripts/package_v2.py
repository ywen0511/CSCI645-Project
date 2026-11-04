#!/usr/bin/env python3
"""Package the v2 release assets from existing files only (CPU; standard library).

    python3 scripts/package_v2.py --v2-root <runs>/v2 --videos <videos dir> --tag v2.0.0 \
        --experiment-commit <sha of experiment-v2> --analysis-commit <sha> --output release_v2 \
        --redact /path/to/private/work=<WORK> --redact /home/user=<HOME>

--v2-root is the v2 run root with ``final/{train,validation,eval,matrices}``, ``pilot/{train,eval}``, ``dev/``,
``audit/``, ``stage0/`` and ``logs/``. Repository files (results/v2, configs, docs/v2, report/v2) come from this
checkout. Every archive gets a member inventory (path, size, SHA-256) in ``archive_inventories.json``; text
members are redacted (machine-specific path prefixes and host names). A missing required input aborts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tarfile
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = {".json", ".jsonl", ".log", ".txt", ".md", ".csv", ".sh", ".yaml"}
REDACT: list[tuple[str, str]] = []
HOST_RES: list[tuple[re.Pattern, str]] = []
STAGE: Path | None = None


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


def make_tar(dest: Path, members: list[tuple[Path, str]], inv: dict) -> None:
    rows = []
    with tarfile.open(dest, "w:gz", compresslevel=6) as tar:
        for src, arc in members:
            if not src.is_file():
                raise SystemExit(f"missing input for {dest.name}: {src}")
            r = redacted(src)
            ti = tar.gettarinfo(str(r), arcname=arc)
            ti.uid = ti.gid = 0
            ti.uname = ti.gname = ""
            ti.mtime = int(src.stat().st_mtime)
            with open(r, "rb") as f:
                tar.addfile(ti, f)
            rows.append({"path": arc, "size_bytes": r.stat().st_size, "sha256": sha(r)})
    inv[dest.name] = rows


def tree(base: Path, prefix: str, exclude=()) -> list[tuple[Path, str]]:
    if not base.exists():
        raise SystemExit(f"missing directory {base}")
    out = []
    for p in sorted(base.rglob("*")):
        if p.is_file() and not any(x in p.parts for x in exclude):
            out.append((p, f"{prefix}/{p.relative_to(base).as_posix()}"))
    return out


def main():
    global STAGE
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--v2-root", required=True)
    ap.add_argument("--videos", required=True)
    ap.add_argument("--tag", default="v2.0.0")
    ap.add_argument("--experiment-commit", required=True)
    ap.add_argument("--analysis-commit", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--redact", action="append", default=[], help="OLD=TOKEN")
    ap.add_argument("--redact-regex", action="append", default=[], help="REGEX=TOKEN (e.g. internal host names)")
    a = ap.parse_args()
    for r in a.redact:
        old, tok = r.split("=", 1)
        REDACT.append((old, tok))
    for r in a.redact_regex:
        rx, tok = r.rsplit("=", 1)
        HOST_RES.append((re.compile(rx), tok))
    V = Path(a.v2_root)
    out = Path(a.output)
    if out.exists():
        raise SystemExit(f"{out} exists; refusing to overwrite")
    out.mkdir(parents=True)
    STAGE = Path(tempfile.mkdtemp(prefix="pkg_v2_"))
    P = json.loads((ROOT / "configs/v2/frozen/protocol.json").read_text())
    sel = json.loads((ROOT / "results/v2/final/selection/selection.json").read_text())
    inv: dict = {}
    ckpt_index, runs_index = [], []

    # ---- final checkpoints: one archive per run
    for m in P["training"]["methods"]:
        for s in P["training"]["seeds"]:
            rid = f"{m}_seed{s}"
            rd = V / "final/train" / rid
            ledger = [json.loads(x) for x in (rd / "checkpoints.jsonl").read_text().splitlines() if x.strip()]
            run = json.loads((rd / "run.json").read_text())
            done = json.loads((rd / "DONE.json").read_text())
            selsrc = json.loads((ROOT / "results/v2/final/selection" / f"{rid}.json").read_text())
            files = sorted((rd / "checkpoints").glob("*.pt"))
            meta = {
                "run_id": rid, "method": m, "seed": s, "run_type": "final", "protocol": "configs/v2/frozen/protocol.json",
                "protocol_sha256": run["protocol_sha256"], "config_hash": run["config_hash"],
                "source_commit": run["git"]["commit"], "source_dirty": run["git"]["dirty"], "actor_init": run.get("actor_init"),
                "requested_transitions": run["requested_transitions"], "realized_transitions": done["transitions"],
                "scored_transitions": done.get("scored_transitions_this_process"),
                "roles": {"untrained": "step_000000000.pt", "selected": f"{sel[rid]['selected']}.pt", "final": "final.pt", "resume": "latest.pt"},
                "validation_candidates": selsrc["candidates"],
                "member_sha256": {f.name: sha(f) for f in files},
                "schema": "RSL-RL 5.5.1 OnPolicyRunner.save: actor/critic state dicts (incl. empirical observation normalizer), "
                          "optimizer state, iteration, infos (transitions, seed, method, config/protocol hashes, curriculum stage, RNG states)",
                "observation": "46-dim vector, see configs/v2/frozen/protocol.json task_resolved and src/csci645_handover/tasks/handover_env.py",
                "replay": f"python scripts/eval_matrix.py --matrix <matrix with entry {{method: {m}, checkpoint: {rid}/checkpoints/<tag>.pt}}> --output <dir> --checkpoint-root <extracted>",
            }
            mp = STAGE / f"{rid}_checkpoint_metadata.json"
            mp.write_text(json.dumps(meta, indent=1, default=str))
            members = [(f, f"{rid}/checkpoints/{f.name}") for f in files]
            for name in ("checkpoints.jsonl", "run.json", "run_resume.json", "train_log.jsonl", "DONE.json"):
                if (rd / name).exists():
                    members.append((rd / name, f"{rid}/{name}"))
            members.append((mp, f"{rid}/checkpoint_metadata.json"))
            asset = f"checkpoints-{m}-seed{s}.tar.gz"
            make_tar(out / asset, members, inv)
            for row in ledger:
                ckpt_index.append({"run_id": rid, "run_type": "final", "tag": row["tag"], "transitions": row["transitions"],
                                   "asset": asset, "member": f"{rid}/{row['path']}", "ledger_sha256": row["sha256"]})
            for role, fname in meta["roles"].items():
                ckpt_index.append({"run_id": rid, "run_type": "final", "role": role, "asset": asset,
                                   "member": f"{rid}/checkpoints/{fname}", "sha256": meta["member_sha256"][fname]})
            runs_index.append({"run_id": rid, "run_type": "final", "method": m, "seed": s, "status": "completed",
                               "realized_transitions": done["transitions"], "scored_transitions": done.get("scored_transitions_this_process"),
                               "selected": sel[rid]["selected"], "checkpoint_asset": asset, "source_commit": run["git"]["commit"],
                               "resumed": (rd / "run_resume.json").exists()})
    # ---- pilot checkpoints and logs (all pilot runs incl. smoke), labelled separately
    pm = []
    for rd in sorted((V / "pilot/train").iterdir()):
        if not rd.is_dir():
            continue
        pm += [(p, f"pilot/{rd.name}/{p.relative_to(rd).as_posix()}") for p in sorted(rd.rglob("*"))
               if p.is_file() and "tensorboard" not in p.parts]
        run = json.loads((rd / "run.json").read_text())
        led = [json.loads(x) for x in (rd / "checkpoints.jsonl").read_text().splitlines() if x.strip()]
        runs_index.append({"run_id": rd.name, "run_type": run.get("run_type"), "method": run["method"], "seed": run["seed"],
                           "protocol": run["protocol"], "actor_init": run.get("actor_init"),
                           "realized_transitions": max(r["transitions"] for r in led), "status": "completed",
                           "checkpoint_asset": "checkpoints-pilot.tar.gz", "resumed": (rd / "run_resume.json").exists()})
        for row in led:
            ckpt_index.append({"run_id": rd.name, "run_type": run.get("run_type"), "tag": row["tag"], "transitions": row["transitions"],
                               "asset": "checkpoints-pilot.tar.gz", "member": f"pilot/{rd.name}/{row['path']}", "ledger_sha256": row["sha256"]})
    make_tar(out / "checkpoints-pilot.tar.gz", pm, inv)

    # ---- raw records
    make_tar(out / "raw-final-eval.tar.gz", tree(V / "final/eval", "final/eval") + tree(V / "final/matrices", "final/matrices"), inv)
    make_tar(out / "raw-validation.tar.gz", tree(V / "final/validation", "final/validation"), inv)
    make_tar(out / "raw-development.tar.gz", tree(V / "dev", "dev"), inv)
    make_tar(out / "raw-pilot-eval.tar.gz", tree(V / "pilot/eval", "pilot/eval"), inv)
    make_tar(out / "raw-audit.tar.gz", tree(V / "audit", "audit") + tree(V / "stage0", "stage0"), inv)
    make_tar(out / "logs.tar.gz", tree(V / "logs", "logs"), inv)
    # ---- videos
    vd = Path(a.videos)
    vids = sorted(vd.glob("*.mp4"))
    if len(vids) < 10:
        raise SystemExit(f"only {len(vids)} videos")
    vindex = []
    vm = []
    for v in vids:
        side = v.with_suffix(".json")
        if not side.exists():
            raise SystemExit(f"missing sidecar {side}")
        vm += [(v, f"videos/{v.name}"), (side, f"videos/{side.name}")]
        sc = json.loads(redacted(side).read_text())
        vindex.append({"video": v.name, "member": f"videos/{v.name}", "sha256": sha(v), "size_bytes": v.stat().st_size, **sc})
    make_tar(out / "videos.tar.gz", vm, inv)
    (out / "videos.json").write_text(json.dumps(vindex, indent=1, default=str) + "\n")
    # ---- repository material
    make_tar(out / "results.tar.gz", tree(ROOT / "results/v2", "results/v2"), inv)
    cfg = tree(ROOT / "configs/v2", "configs/v2") + tree(ROOT / "configs/frozen", "configs/frozen") + tree(ROOT / "docs/v2", "docs/v2")
    make_tar(out / "configs-and-docs.tar.gz", cfg, inv)
    for src, name in ((ROOT / "report/v2/report.pdf", "report.pdf"), (ROOT / "report/v2/report.md", "report.md"),
                      (ROOT / "report/v2/deck/deck.pdf", "deck.pdf"), (ROOT / "report/v2/deck/deck.pptx", "deck.pptx"),
                      (ROOT / "report/report.pdf", "report-v1-corrected.pdf"), (ROOT / "docs/v2/REPRODUCE.md", "REPRODUCE.md")):
        if not src.exists():
            raise SystemExit(f"missing {src}")
        shutil.copy2(redacted(src), out / name)
    (out / "runs.json").write_text(json.dumps(runs_index, indent=1, default=str) + "\n")
    (out / "checkpoints.json").write_text(json.dumps(ckpt_index, indent=1) + "\n")
    (out / "archive_inventories.json").write_text(json.dumps(inv, indent=1) + "\n")
    kinds = {"checkpoints": "checkpoints", "raw": "raw records", "logs": "logs", "videos": "videos", "results": "summaries/figures",
             "configs": "configs/docs", "report": "report", "deck": "presentation", "REPRODUCE": "reproduction"}
    assets = []
    for f in sorted(out.iterdir()):
        if f.name in ("manifest.json", "SHA256SUMS"):
            continue
        kind = next((v for k, v in kinds.items() if f.name.startswith(k)), "index")
        assets.append({"name": f.name, "size_bytes": f.stat().st_size, "sha256": sha(f), "kind": kind})
    man = {"tag": a.tag, "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "experiment_tag": "experiment-v2", "experiment_commit": a.experiment_commit, "analysis_commit": a.analysis_commit,
           "protocol_sha256": sha(ROOT / "configs/v2/frozen/protocol.json"),
           "v1_reference": {"release": "https://github.com/ywen0511/CSCI645-Project/releases/tag/v1.0.0",
                            "note": "v1 checkpoints and raw records are not re-uploaded; they are referenced by this immutable release and its SHA256SUMS"},
           "assets": assets, "redaction": [t for _, t in REDACT] + [t for _, t in HOST_RES]}
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    with open(out / "SHA256SUMS", "w") as f:
        for x in sorted(out.iterdir()):
            if x.name != "SHA256SUMS":
                f.write(f"{sha(x)}  {x.name}\n")
    shutil.rmtree(STAGE)
    tot = sum(x.stat().st_size for x in out.iterdir())
    print(f"{len(list(out.iterdir()))} assets, {tot / 1e6:.1f} MB, {sum(len(v) for v in inv.values())} archive members")


if __name__ == "__main__":
    main()
