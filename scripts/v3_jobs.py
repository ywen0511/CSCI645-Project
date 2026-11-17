#!/usr/bin/env python3
"""Run v3 task manifests with a hash-checked ledger (standard library only).

    python3 scripts/v3_jobs.py run --manifest results/v3/jobs/<name>.json --shard 0/4 \
        --isaac-python /path/to/isaaclab/python [--runs-root runs/v3]

A manifest is {"name": ..., "tasks": [{"id", "argv": [script, args...], "inputs": [repo-relative paths],
"outputs": [paths whose contents must match the successful ledger], "kind": "isaac"|"cpu"|"shell"}]}. Paths starting with
``$RUNS`` are resolved against --runs-root. Each task runs in a fresh process from the repository root
(simulator tasks through scripts/cluster/isaac_run.sh). A task is skipped only if every output exists AND its
latest attempt succeeded and has matching output fingerprints, input hashes, resolved argv and source; otherwise
missing work runs again, while changed/unverifiable completed outputs cause an explicit integrity error (the
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


def fingerprint(path: Path):
    """Hash files and directory membership/content; never bless a directory merely because it exists."""
    if path.is_symlink():
        raise ValueError(f"Output is a symlink, declare the actual artifact path: {path}")
    if path.is_file():
        return {"kind": "file", "bytes": path.stat().st_size, "sha256": sha(path)}
    if path.is_dir():
        members = {}
        for member in sorted(path.rglob("*")):
            if member.is_symlink():
                raise ValueError(f"Output directory contains a symlink: {member}")
            if member.is_file():
                members[member.relative_to(path).as_posix()] = fingerprint(member)
            elif member.is_dir():
                members[member.relative_to(path).as_posix() + "/"] = {"kind": "directory"}
            else:
                raise ValueError(f"Unsupported output member: {member}")
        digest = hashlib.sha256(json.dumps(members, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return {"kind": "directory", "members": len(members), "sha256": digest}
    return None


def cache_valid(last, inputs, argv, source_commit, outs, context):
    """A corrupt completed output is a hard error, not a request to overwrite evidence.

    Legacy file hashes can detect corruption, but legacy records lack dependency/context
    coverage and are not eligible for skipping. Use a fresh runs directory to verify old releases.
    """
    if not last or last.get("rc") != 0 or not last.get("outputs_exist"):
        return False
    complete = bool(outs)
    for output in outs:
        current = fingerprint(output)
        if current is None:
            complete = False
            continue
        saved = last.get("output_fingerprints", {}).get(str(output))
        if saved is None:
            old = last.get("outputs", {}).get(str(output))
            if current["kind"] != "file" or not isinstance(old, str) or len(old) != 64:
                raise ValueError(f"Unverifiable completed output: {output}; use a fresh runs directory")
            matches = old == current["sha256"]
        else:
            matches = saved == current
        if not matches:
            raise ValueError(f"Output integrity mismatch: {output}; preserve it and use a fresh runs directory")
    same = (last.get("inputs") == inputs and last.get("argv") == argv
            and last.get("source_commit") == source_commit and last.get("cache_context") == context)
    if complete and (not same or not last.get("output_fingerprints")):
        raise ValueError("Completed outputs have changed or legacy provenance; preserve them and use a fresh runs directory")
    return complete and same


def resolve_json(value, runs):
    if isinstance(value, str):
        return resolve(value, runs)
    if isinstance(value, list):
        return [resolve_json(v, runs) for v in value]
    if isinstance(value, dict):
        return {k: resolve_json(v, runs) for k, v in value.items()}
    return value


def input_hashes(task, argv, runs):
    """Cover declared inputs AND evaluation matrix dependencies/checkpoints before any cache skip."""
    inputs = {}

    def add(value):
        p = Path(resolve(value, runs))
        if not p.is_absolute():
            p = EXEC / p if (EXEC / p).exists() else ROOT / p
        if not p.is_file():
            raise ValueError(f"Required input file missing: {p}")
        inputs[str(p.resolve())] = sha(p)
        return p

    for value in task.get("inputs", []):
        add(value)
    if task.get("kind", "isaac") in ("cpu", "isaac") and argv and argv[0].endswith(".py"):
        add(argv[0])
    for k, value in enumerate(argv[:-1]):
        if value in ("--protocol", "--suite", "--checkpoint", "--resume", "--before", "--after", "--eval-records"):
            add(argv[k + 1])
        if value in ("--matrix", "--plan"):
            p = add(argv[k + 1])
            data = json.loads(p.read_text())
            entries = data if isinstance(data, list) else data.get("entries", [])
            if isinstance(data, dict):
                for field in ("protocol", "suite"):
                    if data.get(field):
                        add(data[field])
            only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else set()
            ckroot = Path(argv[argv.index("--checkpoint-root") + 1]) if "--checkpoint-root" in argv else None
            for entry in entries:
                if only and entry.get("id") not in only:
                    continue
                if entry.get("checkpoint"):
                    cp = Path(entry["checkpoint"])
                    add(str(ckroot / cp if ckroot is not None and not cp.is_absolute() else cp))
                if entry.get("eval_records"):
                    add(entry["eval_records"])
    return inputs


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
    if n < 1 or not 0 <= i < n:
        raise ValueError("--shard must be I/N with N >= 1 and 0 <= I < N")
    tasks = [t for k, t in enumerate(man["tasks"]) if k % n == i]
    if a.only:
        keep = set(a.only.split(","))
        unknown = keep - {t["id"] for t in man["tasks"]}
        if unknown:
            raise ValueError(f"Unknown task IDs: {sorted(unknown)}")
        tasks = [t for t in tasks if t["id"] in keep]
    os.environ["V3_ISAAC_PYTHON"] = a.isaac_python
    g = git_state()
    if g["dirty"] and not a.allow_dirty:
        raise SystemExit("v3 jobs require a clean committed source tree")
    failed = []
    for t in tasks:
        argv = [resolve(x, runs) for x in t["argv"]]
        for k, x in enumerate(argv):  # JSON inputs from the delivery checkout may reference $DELIVERY/$RUNS paths
            if not x.endswith(".json") or (k and argv[k - 1] == "--output"):
                continue
            mp = Path(x) if Path(x).is_absolute() else (EXEC / x if (EXEC / x).exists() else ROOT / x)
            if mp.exists():
                text = mp.read_text()
                if "$DELIVERY" in text or "$RUNS" in text:
                    rp = runs / "_resolved" / f"{t['id']}__{mp.name}"
                    rp.parent.mkdir(parents=True, exist_ok=True)
                    rp.write_text(json.dumps(resolve_json(json.loads(text), runs), indent=2) + "\n")
                    argv[k] = str(rp)
        inputs = input_hashes(t, argv, runs)
        outs = [Path(resolve(p, runs)) for p in t.get("outputs", [])]
        context = {"resolved_argv": argv, "kind": t.get("kind", "isaac"),
                   "interpreter": a.isaac_python, "runner_sha256": sha(Path(__file__))}
        if a.dry_run:
            print(json.dumps({"task": t["id"], "dry_run": True, "argv": argv, "inputs": inputs,
                              "outputs": [str(p) for p in outs], "execution_commit": g["commit"]}), flush=True)
            continue
        lp = led_dir / f"{t['id']}.jsonl"
        hist = [json.loads(l) for l in lp.read_text().splitlines()] if lp.exists() else []
        if cache_valid(hist[-1] if hist else None, inputs, t["argv"], g["commit"], outs, context):
            print(f"[v3_jobs] skip {t['id']} (inputs and output contents verified)", flush=True)
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
               "output_fingerprints": {str(o): fingerprint(o) for o in outs}, "cache_context": context,
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
    """Merge per-task ledgers of one or more runs roots; absolute run/checkout paths are redacted to $RUNS/$REPO."""
    import re

    leaks = [r"/data/rtxw01", r"/home/(?!conda/)[a-z0-9_]+/", r"dcwip\w+", r"\.gm\.com", r"kztrgg", r"nbak/robot_intel"]
    rows = []
    for root in a.runs_root:
        runs = Path(root).resolve()
        for p in sorted((runs / "ledger").glob("*.jsonl")):
            for l in p.read_text().splitlines():
                s = json.dumps(json.loads(l)).replace(str(runs), "$RUNS").replace(str(ROOT), "$REPO")
                # paths written on the cluster: <anything>/v3/<runs root name> -> $RUNS; other checkouts -> $REPO
                s = re.sub(r"(?:/[A-Za-z0-9_.\-]+)+/v3/" + re.escape(runs.name) + r"(?=[/\"])", "$RUNS", s)
                s = re.sub(r"(?:/[A-Za-z0-9_.\-]+)+/projs/code/[A-Za-z0-9_.\-]+(?=[/\"])", "$REPO", s)
                r = json.loads(s)
                r["host"] = "<cluster-node>"
                r["runs_root"] = runs.name
                rows.append(r)
    rows.sort(key=lambda r: (r["start_utc"], r["task"], r["attempt"]))
    text = "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)
    hits = sorted({m.group(0) for pat in leaks for m in re.finditer(pat, text)})
    if hits:
        raise SystemExit(f"private paths/hosts left after redaction: {hits}")
    out = ROOT / "results/v3/task_ledger.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    print(f"merged {len(rows)} attempts from {len(a.runs_root)} runs roots into {out}")


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
    r.add_argument("--dry-run", action="store_true", help="Resolve inputs/paths and validate dependencies without launching tasks")
    r.add_argument("--task-timeout-s", type=float, default=5400.0)
    m = sub.add_parser("merge")
    m.add_argument("--runs-root", action="append", required=True, help="repeatable; e.g. candidate then formal")
    a = ap.parse_args()
    {"run": run, "merge": merge}[a.cmd](a)


if __name__ == "__main__":
    main()
