#!/usr/bin/env python3
"""Run the complete frozen experiment with a persistent ledger (single machine, sequential).

Usage:
    python3 scripts/run_experiments.py --protocol configs/frozen/protocol.json --output runs/final --resume
    python3 scripts/run_experiments.py ... --only train      # stages: train, validate, select, evaluate, analyze

Each stage calls the documented entry points (train.py, evaluate.py, analyze.py) in fresh processes with the
same Python interpreter. Completed work is detected from DONE.json / existing records, so ``--resume`` never
duplicates training or evaluation records (evaluate.py itself resumes by case ID and rejects duplicates).
The ledger is ``<output>/ledger.json``. The reported experiments were dispatched as independent one-GPU jobs
that executed exactly these commands in parallel; see docs/REPRODUCE.md.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from csci645_handover.selection import score_validation_file, select, validation_candidates  # noqa: E402


def run(cmd: list[str], ledger: dict, key: str, path: Path) -> None:
    entry = ledger.setdefault(key, {})
    entry.update(command=" ".join(cmd), state="running", start_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    save(ledger, path)
    rc = subprocess.run(cmd, cwd=ROOT).returncode
    entry.update(state="completed" if rc == 0 else "failed", exit_code=rc,
                 end_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    save(ledger, path)
    if rc != 0:
        raise SystemExit(f"{key} failed with exit code {rc}; fix and rerun with --resume")


def save(ledger: dict, path: Path) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(ledger, indent=2))
    tmp.replace(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--protocol", default="configs/frozen/protocol.json")
    ap.add_argument("--output", required=True)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--only", default=None, choices=["train", "validate", "select", "evaluate", "analyze"])
    ap.add_argument("--python", default=sys.executable)
    a = ap.parse_args()
    proto = json.loads(Path(a.protocol).read_text())
    if proto.get("status") != "frozen":
        raise SystemExit("run_experiments.py only runs a frozen protocol")
    out = Path(a.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    lpath = out / "ledger.json"
    ledger = json.loads(lpath.read_text()) if (a.resume and lpath.exists()) else {}
    py = a.python
    learned = [m["id"] for m in proto["methods"] if m["learned"]]
    scripted = [m["id"] for m in proto["methods"] if not m["learned"]]
    seeds = proto["training"]["seeds"]
    suites = ROOT / "configs/frozen/suites"
    stages = [a.only] if a.only else ["train", "validate", "select", "evaluate", "analyze"]

    for m in learned:
        for s in seeds:
            rid = f"{m}_seed{s}"
            tdir = out / "train" / rid
            if "train" in stages and not (tdir / "DONE.json").exists():
                cmd = [py, "scripts/train.py", "--method", m, "--seed", str(s), "--protocol", a.protocol,
                       "--run-type", "final", "--output", str(tdir)]
                if (tdir / "checkpoints/latest.pt").exists():
                    cmd += ["--resume", str(tdir / "checkpoints/latest.pt")]
                run(cmd, ledger, f"train/{rid}", lpath)
            if "validate" in stages:
                cands = validation_candidates(tdir / "checkpoints.jsonl")
                cmd = [py, "scripts/evaluate.py", "--method", m, "--training-seed", str(s), "--protocol", a.protocol,
                       "--checkpoint", *[str(tdir / c["path"]) for c in cands],
                       "--suite", str(suites / "validation.jsonl"), "--run-id", rid, "--output", str(out / "validation")]
                run(cmd, ledger, f"validate/{rid}", lpath)
            if "select" in stages:
                scored = [score_validation_file(f) for f in sorted((out / "validation").glob(f"{rid}__step_*.jsonl"))]
                best = select(scored)
                (out / "selection").mkdir(exist_ok=True)
                (out / "selection" / f"{rid}.json").write_text(json.dumps({"selected": best, "candidates": scored,
                                                                           "rule": proto["training"]["checkpoint_selection"]}, indent=2))
                ledger[f"select/{rid}"] = {"state": "completed", "selected": best["checkpoint"]}
                save(ledger, lpath)
            if "evaluate" in stages:
                sel = json.loads((out / "selection" / f"{rid}.json").read_text())["selected"]
                cmd = [py, "scripts/evaluate.py", "--method", m, "--training-seed", str(s), "--protocol", a.protocol,
                       "--checkpoint", str(tdir / "checkpoints" / f"{sel['checkpoint']}.pt"),
                       "--suite", str(suites / "final.jsonl"), "--run-id", rid, "--output", str(out / "eval")]
                run(cmd, ledger, f"evaluate/{rid}", lpath)
    if "evaluate" in stages:
        for m in scripted:
            cmd = [py, "scripts/evaluate.py", "--method", m, "--protocol", a.protocol,
                   "--suite", str(suites / "final.jsonl"), "--run-id", m, "--output", str(out / "eval")]
            run(cmd, ledger, f"evaluate/{m}", lpath)
    if "analyze" in stages:
        cmd = [py, "scripts/build_run_index.py", "--runs", str(out), "--output", str(out / "run_index.json")]
        run(cmd, ledger, "index", lpath)
        cmd = [py, "scripts/analyze.py", "--run-index", str(out / "run_index.json"), "--output", str(out / "summary")]
        run(cmd, ledger, "analyze", lpath)
    print(f"ledger: {lpath}")


if __name__ == "__main__":
    main()
