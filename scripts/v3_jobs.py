#!/usr/bin/env python3
"""Run v3 task manifests with a hash-checked ledger (standard library only).

    python3 scripts/v3_jobs.py run --manifest results/v3/jobs/<name>.json --shard 0/4 \
        --isaac-python /path/to/isaaclab/python [--runs-root runs/v3]

A manifest is {"name": ..., "tasks": [{"id", "argv": [script, args...], "inputs": [repo-relative paths],
"outputs": [paths whose existence marks completion], "kind": "isaac"|"cpu"|"shell"}]}. Paths starting with
``$RUNS`` are resolved against --runs-root. Each task runs in a fresh process from the repository root
(simulator tasks through scripts/cluster/isaac_run.sh). A task is skipped only if every output exists AND its
last successful ledger entry has the same input hashes, argv and source commit; otherwise it runs again (the
scripts themselves resume/reject partial outputs). Every attempt is appended to
<runs-root>/ledger/<task id>.jsonl with command, source commit, input/output SHA-256, timestamps and exit code.
``merge`` concatenates all ledgers into results/v3/task_ledger.jsonl (paths relative, private prefixes removed).
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(p: Path) -> str | None:
    if not p.exists() or not p.is_file():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


EXEC = ROOT  # checkout whose code runs the tasks (--repo); manifests/matrices may come from this delivery checkout


def git_state(repo: Path | None = None) -> dict:
    repo = repo or EXEC
    c = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    d = subprocess.run(["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=no"],
                       capture_output=True, text=True).stdout.strip()
    return {"commit": c, "dirty": bool(d)}


def utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(s: str, runs: Path) -> str:
    return s.replace("$RUNS", str(runs)).replace("$DELIVERY", str(ROOT)).replace("$PY", os.environ.get("V3_ISAAC_PYTHON", sys.executable))


SHUTDOWN_MARK = "SimulationContext cleared"


def supervise(cmd, log, outs, timeout_s: float):
    """Run cmd in its own process group. Isaac Sim sometimes hangs during Kit shutdown after all work is
    written ("SimulationContext cleared" printed, process never exits). If that happens and every declared
    output exists, the group is killed after a grace period and the task counts as complete; the event is
    recorded. A task that exceeds timeout_s is killed and fails (rc 124)."""
    import signal
    import time

    t0 = time.time()
    seen = None
    with open(log, "w") as f:
        p = subprocess.Popen(cmd, cwd=EXEC, stdout=f, stderr=subprocess.STDOUT, start_new_session=True,
                             env={**os.environ, "REPO": str(EXEC)})
        while True:
            try:
                rc = p.wait(timeout=5)
                return rc, None
            except subprocess.TimeoutExpired:
                pass
            if seen is None and SHUTDOWN_MARK in Path(log).read_text(errors="replace")[-4000:]:
                seen = time.time()
            if seen is not None and time.time() - seen > 90:
                os.killpg(p.pid, signal.SIGKILL)
                p.wait()
                ok = all(o.exists() for o in outs)
                return (0 if ok else 1), {"event": "killed after Kit shutdown hang", "seconds_after_shutdown_mark": 90,
                                          "outputs_complete": ok}
            if time.time() - t0 > timeout_s:
                os.killpg(p.pid, signal.SIGKILL)
                p.wait()
                return 124, {"event": "task timeout", "timeout_s": timeout_s}


def run(a):
    global EXEC
    EXEC = Path(a.repo).resolve() if a.repo else ROOT
    man = json.loads(Path(a.manifest).read_text())
    runs = Path(a.runs_root).resolve()
    led_dir = runs / "ledger"
    led_dir.mkdir(parents=True, exist_ok=True)
    i, n = (int(x) for x in a.shard.split("/"))
    tasks = [t for k, t in enumerate(man["tasks"]) if k % n == i]
    if a.only:
        keep = set(a.only.split(","))
        tasks = [t for t in tasks if t["id"] in keep]
    os.environ["V3_ISAAC_PYTHON"] = a.isaac_python
    g = git_state()
    if g["dirty"] and not a.allow_dirty:
        raise SystemExit("v3 jobs require a clean committed source tree")
    failed = []
    for t in tasks:
        argv = [resolve(x, runs) for x in t["argv"]]
        inputs = {p: sha((EXEC / resolve(p, runs)) if (EXEC / resolve(p, runs)).exists() else (ROOT / resolve(p, runs)))
                  for p in t.get("inputs", [])}
        outs = [Path(resolve(p, runs)) for p in t.get("outputs", [])]
        lp = led_dir / f"{t['id']}.jsonl"
        hist = [json.loads(l) for l in lp.read_text().splitlines()] if lp.exists() else []
        last_ok = next((h for h in reversed(hist) if h["rc"] == 0), None)
        if outs and all(o.exists() for o in outs) and last_ok and last_ok["inputs"] == inputs \
                and last_ok["argv"] == t["argv"] and last_ok["source_commit"] == g["commit"]:
            print(f"[v3_jobs] skip {t['id']} (complete, inputs unchanged)", flush=True)
            continue
        attempts = len(hist)
        if attempts >= a.max_attempts:
            print(f"[v3_jobs] {t['id']}: {attempts} attempts already; not retrying", flush=True)
            failed.append(t["id"])
            continue
        log = runs / "logs" / f"{t['id']}.attempt{attempts + 1}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        kind = t.get("kind", "isaac")
        if kind == "isaac":
            cmd = ["bash", str(EXEC / "scripts/cluster/isaac_run.sh"), a.isaac_python, *argv]
        elif kind == "cpu":
            cmd = [a.isaac_python, *argv]
        else:
            cmd = ["bash", "-c", " ".join(argv)]
        t0 = utc()
        print(f"[v3_jobs] run {t['id']}: {' '.join(argv)}", flush=True)
        rc, watchdog = supervise(cmd, log, outs, a.task_timeout_s)
        rec = {"task": t["id"], "manifest": man["name"], "attempt": attempts + 1, "argv": t["argv"], "kind": kind,
               "exec_repo": "experiment" if EXEC != ROOT else "delivery", "delivery_commit": git_state(ROOT)["commit"],
               "start_utc": t0, "end_utc": utc(), "rc": rc, "source_commit": g["commit"], "source_dirty": g["dirty"],
               "inputs": inputs, "outputs": {str(o): sha(o) if o.is_file() else ("dir" if o.is_dir() else None) for o in outs},
               "outputs_exist": all(o.exists() for o in outs), "log": str(log), "host": socket.gethostname(),
               "watchdog": watchdog,
               "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES")}
        with open(lp, "a") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"[v3_jobs] {t['id']} rc={rc}", flush=True)
        if rc != 0 or not rec["outputs_exist"]:
            failed.append(t["id"])
    print(json.dumps({"shard": a.shard, "tasks": len(tasks), "failed": failed}), flush=True)
    raise SystemExit(1 if failed else 0)


def merge(a):
    runs = Path(a.runs_root).resolve()
    rows = []
    for p in sorted((runs / "ledger").glob("*.jsonl")):
        for l in p.read_text().splitlines():
            r = json.loads(l)
            s = json.dumps(r).replace(str(runs), "$RUNS").replace(str(ROOT), "$REPO")
            r = json.loads(s)
            r["host"] = "<cluster-node>"
            rows.append(r)
    rows.sort(key=lambda r: (r["start_utc"], r["task"], r["attempt"]))
    out = ROOT / "results/v3/task_ledger.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    print(f"merged {len(rows)} attempts into {out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--manifest", required=True)
    r.add_argument("--shard", default="0/1")
    r.add_argument("--only", default="")
    r.add_argument("--repo", default=None, help="execution checkout (clean experiment tag); default: this checkout")
    r.add_argument("--isaac-python", default=os.environ.get("CLOSEOUT_ISAAC_PYTHON", sys.executable))
    r.add_argument("--runs-root", default=str(ROOT / "runs/v3"))
    r.add_argument("--max-attempts", type=int, default=3)
    r.add_argument("--allow-dirty", action="store_true")
    r.add_argument("--task-timeout-s", type=float, default=5400.0)
    m = sub.add_parser("merge")
    m.add_argument("--runs-root", default=str(ROOT / "runs/v3"))
    a = ap.parse_args()
    {"run": run, "merge": merge}[a.cmd](a)


if __name__ == "__main__":
    main()
