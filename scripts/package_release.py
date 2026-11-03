#!/usr/bin/env python3
"""Package release assets (archives, indexes, manifest, SHA256SUMS) from existing files only.

Usage:
    python3 scripts/package_release.py --runs RUNS_DIR --summary results/summary --report report \
        --videos VIDEOS_DIR --logs LOG_DIR [--logs MORE ...] --tag v1.0.0 \
        --experiment-commit SHA --analysis-commit SHA --output release_assets

RUNS_DIR is the final-experiment folder (train/, validation/, eval/, invariants/). Nothing is invented: a
missing required input aborts packaging. Every archive also gets a member inventory (path, size, SHA-256)
in archive_inventories.json. Checkpoint archives are one per learned method and seed and contain every
periodic checkpoint (selected, final and resumable ``latest.pt`` included), the checkpoint ledger, run
metadata and checkpoint_metadata.json describing roles, hashes, transitions, normalization and replay.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OBS_SCHEMA = [
    "0:3 receiver grasp point (from object pose) minus receiver TCP [m, world]",
    "3:6 object-vs-receiver-hand orientation error (axis-angle) [rad]",
    "6:9 object linear velocity relative to receiver hand (finite difference) [m/s]",
    "9:12 object angular velocity relative to receiver hand (finite difference) [rad/s]",
    "12:15 giver TCP minus receiver TCP [m]",
    "15:17 giver and receiver gripper gaps [m]",
    "17:21 tanh(object-filtered finger normal force / 5 N): giver L, giver R, receiver L, receiver R",
    "21:28 receiver arm joint positions minus reset seed [rad]",
    "28:35 0.1 x receiver arm joint velocities [rad/s]",
    "35:38 nominal receiver target minus receiver TCP [m]",
    "38:39 episode time / 8 s",
    "39:42 previous residual / 0.02 m",
    "42:46 explicit contact-phase one-hot (giver only, both, receiver only, neither); zero for combined_no_phase",
]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def make_tar(dest: Path, members: list[tuple[Path, str]], inventories: dict) -> None:
    inv = []
    with tarfile.open(dest, "w:gz", compresslevel=6) as tar:
        for src, arc in members:
            if not src.exists():
                raise SystemExit(f"missing input for {dest.name}: {src}")
            tar.add(src, arcname=arc, recursive=False)
            if src.is_file():
                inv.append({"path": arc, "size_bytes": src.stat().st_size, "sha256": sha(src)})
    inventories[dest.name] = inv


def tree(src: Path, prefix: str, exclude=()) -> list[tuple[Path, str]]:
    out = []
    for p in sorted(src.rglob("*")):
        if p.is_file() and not any(x in p.parts or p.name.endswith(x) for x in exclude):
            out.append((p, f"{prefix}/{p.relative_to(src).as_posix()}"))
    return out


def add_json(tar_members: list, tmp: Path, name: str, obj) -> None:
    p = tmp / name.replace("/", "__")
    p.write_text(json.dumps(obj, indent=2, default=str))
    tar_members.append((p, name))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--summary", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--videos", required=True)
    ap.add_argument("--logs", action="append", default=[])
    ap.add_argument("--tag", required=True)
    ap.add_argument("--experiment-commit", required=True)
    ap.add_argument("--analysis-commit", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    runs, summ, rep, vids = Path(a.runs), Path(a.summary), Path(a.report), Path(a.videos)
    out = Path(a.output)
    out.mkdir(parents=True, exist_ok=False)
    tmp = out / ".staging"
    tmp.mkdir()
    proto_path = ROOT / "configs/frozen/protocol.json"
    protocol = json.loads(proto_path.read_text())
    sel_path = summ / "selection.json" if (summ / "selection.json").exists() else summ / "primary" / "selection.json"
    selection = json.loads(sel_path.read_text())
    inventories: dict = {}
    artifacts: list[dict] = []

    def register(path: Path, kind: str, **extra):
        artifacts.append({"path": path.name, "kind": kind, "size_bytes": path.stat().st_size, "sha256": sha(path), **extra})

    # ---- checkpoints ----
    ck_index, run_index = [], []
    for m in [x["id"] for x in protocol["methods"] if x["learned"]]:
        for s in protocol["training"]["seeds"]:
            rid = f"{m}_seed{s}"
            tdir = runs / "train" / rid
            ledger = [json.loads(x) for x in (tdir / "checkpoints.jsonl").read_text().splitlines() if x.strip()]
            sel = selection[rid]["selected"]
            members = [(p, f"{rid}/checkpoints/{p.name}") for p in sorted((tdir / "checkpoints").glob("*.pt"))]
            members += [(tdir / "checkpoints.jsonl", f"{rid}/checkpoints.jsonl"), (tdir / "run.json", f"{rid}/run.json"),
                        (tdir / "DONE.json", f"{rid}/DONE.json")]
            if (tdir / "run_resume.json").exists():
                members.append((tdir / "run_resume.json", f"{rid}/run_resume.json"))
            hashes = {p.name: sha(p) for p, _ in members if p.suffix == ".pt"}
            final_row = [r for r in ledger if r["tag"] == "final"][-1]
            meta = {
                "run_id": rid, "method": m, "seed": s,
                "roles": {"selected": f"{rid}/checkpoints/{sel['checkpoint']}.pt",
                          "final": f"{rid}/checkpoints/final.pt", "resume": f"{rid}/checkpoints/latest.pt"},
                "selected_checkpoint": sel["checkpoint"], "selected_transitions": sel["transitions"],
                "selected_validation_success": sel["success_rate"], "selected_validation_drop": sel["drop_rate"],
                "final_transitions": final_row["transitions"],
                "member_sha256": hashes, "periodic_checkpoints": [r["tag"] for r in ledger if r["tag"].startswith("step_")],
                "normalization": "observation normalizers (EmpiricalNormalization) are stored inside actor_state_dict/"
                                 "critic_state_dict and frozen at evaluation",
                "observation_dim": 46, "action_dim": 3, "action_mapping": "residual = 0.02 m * tanh(action)",
                "phase_channels_zeroed": m == "combined_no_phase", "observation_schema": OBS_SCHEMA,
                "contents": "actor/critic state dicts, optimizer state, iteration, infos (transitions, curriculum stage, "
                            "RNG states, config/protocol hashes, source commit)",
                "replay_command": (f"python scripts/evaluate.py --method {m} --training-seed {s} "
                                   f"--checkpoint {rid}/checkpoints/{sel['checkpoint']}.pt "
                                   f"--suite configs/frozen/suites/final.jsonl --run-id {rid} --output replay"),
                "resume_command": (f"python scripts/train.py --method {m} --seed {s} --protocol configs/frozen/protocol.json "
                                   f"--output runs/{rid} --resume {rid}/checkpoints/latest.pt"),
            }
            add_json(members, tmp, f"{rid}/checkpoint_metadata.json", meta)
            dest = out / f"checkpoints-{m}-seed{s}.tar.gz"
            make_tar(dest, members, inventories)
            register(dest, "checkpoints", method=m, seed=s)
            ck_index.append({**meta, "archive": dest.name, "archive_sha256": sha(dest)})
            run_index.append({"run_id": rid, "method": m, "seed": s, "type": "final",
                              "run_metadata": json.loads((tdir / "run.json").read_text()) | {"env_cfg": "see configs"},
                              "done": json.loads((tdir / "DONE.json").read_text())})

    # ---- results ----
    res = tree(runs / "eval", "results/eval") + tree(runs / "validation", "results/validation")
    if (runs / "eval_final_checkpoint").exists():  # declared secondary analysis
        res += tree(runs / "eval_final_checkpoint", "results/eval_final_checkpoint")
    res += tree(runs / "selection", "results/selection")
    res += tree(runs / "invariants", "results/invariants")
    for d in sorted((runs / "train").glob("*_seed*")):
        for f in ("train_log.jsonl", "checkpoints.jsonl", "run.json", "DONE.json"):
            if (d / f).exists():
                res.append((d / f, f"results/train/{d.name}/{f}"))
    res += tree(summ, "results/summary")
    res += [(proto_path, "results/protocol.json")]
    res += [(p, f"results/suites/{p.name}") for p in sorted((ROOT / "configs/frozen/suites").glob("*"))]
    dest = out / "results.tar.gz"
    make_tar(dest, res, inventories)
    register(dest, "results")

    # ---- logs ----
    logs = []
    for i, lp in enumerate(a.logs):
        logs += tree(Path(lp), f"logs/{Path(lp).name}", exclude=(".pt",))
    for d in sorted((runs / "train").glob("*_seed*")):
        logs += tree(d / "tensorboard", f"logs/tensorboard/{d.name}")
    dest = out / "logs.tar.gz"
    make_tar(dest, logs, inventories)
    register(dest, "logs")

    # ---- configs ----
    cfg = tree(ROOT / "configs", "configs") + [(ROOT / "docs/SETUP_REMOTE.md", "docs/SETUP_REMOTE.md"),
                                               (ROOT / "scripts/setup/build_env.sh", "scripts/setup/build_env.sh")]
    dest = out / "configs.tar.gz"
    make_tar(dest, cfg, inventories)
    register(dest, "configs")

    # ---- videos ----
    vids_index = [d for d in (json.loads(p.read_text()) for p in sorted(vids.glob("*.json")))
                  if isinstance(d, dict) and "video" in d]
    if not vids_index:
        raise SystemExit("no video sidecars found")
    dest = out / "videos.tar.gz"
    make_tar(dest, tree(vids, "videos"), inventories)
    register(dest, "videos")
    (out / "videos.json").write_text(json.dumps(vids_index, indent=2))
    register(out / "videos.json", "index")
    showcase = sorted(vids.glob("*showcase*.mp4"))
    for p in showcase[:1]:
        (out / p.name).write_bytes(p.read_bytes())
        register(out / p.name, "videos")

    # ---- report / reproduction / indexes ----
    for name in ("report.pdf", "report.md"):
        (out / name).write_bytes((rep / name).read_bytes())
        register(out / name, "report")
    (out / "REPRODUCE.md").write_bytes((ROOT / "docs/REPRODUCE.md").read_bytes())
    register(out / "REPRODUCE.md", "reproduction")
    (out / "checkpoints.json").write_text(json.dumps(ck_index, indent=2))
    register(out / "checkpoints.json", "index")
    (out / "runs.json").write_text(json.dumps(run_index, indent=2, default=str))
    register(out / "runs.json", "index")
    (out / "archive_inventories.json").write_text(json.dumps(inventories, indent=1))
    register(out / "archive_inventories.json", "index")

    manifest = {"schema_version": 1, "status": "complete", "experiment_source_commit": a.experiment_commit,
                "analysis_commit": a.analysis_commit, "protocol_sha256": sha(proto_path), "release_tag": a.tag,
                "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "artifacts": artifacts}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    lines = [f"{sha(out / 'manifest.json')}  manifest.json"] + [f"{x['sha256']}  {x['path']}" for x in artifacts]
    (out / "SHA256SUMS").write_text("\n".join(lines) + "\n")
    for p in tmp.iterdir():
        p.unlink()
    tmp.rmdir()
    total = sum(x["size_bytes"] for x in artifacts)
    print(f"packaged {len(artifacts)} artifacts, {total / 2**20:.1f} MiB -> {out}")
    for x in artifacts:
        if x["size_bytes"] > 1.9 * 2**30:
            raise SystemExit(f"{x['path']} exceeds the 2 GiB per-asset limit; split it")


if __name__ == "__main__":
    main()
