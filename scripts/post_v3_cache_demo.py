#!/usr/bin/env python3
"""Demonstrate on disposable CPU fixtures that the repaired v3 task runner cannot produce a false cache hit.

    python3 scripts/post_v3_cache_demo.py --work <new empty dir> --output results/post_v3/cache_demo.json

Every scenario drives the real command line (`scripts/v3_jobs.py run`) against a throwaway git repository
with a tiny CPU task that appends one line to a launch counter each time it actually executes. No released
artifact, checkpoint or record is read or modified. Scenarios:

  repeat_skip            completed task is skipped after content verification (no launch)
  edited_output_bytes    one byte of a completed output file changed -> integrity error, no launch
  directory_add/remove   member added to / removed from a completed output directory -> integrity error
  changed_checkpoint     an input checkpoint changed -> provenance error (completed outputs kept), no launch
  legacy_ledger          ledger without output fingerprints (pre-repair format) -> refused, no launch
  missing_output         a declared output deleted -> task runs again (resume)
  failed_latest_attempt  latest attempt rc != 0 -> task runs again, never skipped

The result records the runner's exit code, launch count and decisive message for each scenario.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/v3_jobs.py"

TASK_PY = r'''import argparse, json, pathlib, sys
ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--dir", default=None)
ap.add_argument("--checkpoint", default=None)
ap.add_argument("--counter", required=True)
ap.add_argument("--fail-flag", default=None)
a = ap.parse_args()
with open(a.counter, "a") as f:
    f.write("launch\n")
p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps({"value": 1}) + "\n")
if a.dir:
    d = pathlib.Path(a.dir); d.mkdir(parents=True, exist_ok=True)
    (d / "a.jsonl").write_text("row-a\n"); (d / "b.jsonl").write_text("row-b\n")
if a.fail_flag and pathlib.Path(a.fail_flag).exists():
    sys.exit(3)  # crash after writing every output: a failed attempt whose outputs look complete
'''


def sh(*cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def fixture(base: Path) -> dict:
    repo = base / "repo"
    repo.mkdir(parents=True)
    (repo / "task.py").write_text(TASK_PY)
    (repo / "checkpoint.pt").write_bytes(b"weights-v1")
    man = {"name": "cache_demo", "tasks": [{
        "id": "demo", "kind": "cpu",
        "argv": ["task.py", "--out", "$RUNS/out/result.json", "--dir", "$RUNS/out/records",
                 "--checkpoint", "checkpoint.pt", "--counter", "$RUNS/counter.txt", "--fail-flag", "$RUNS/FAIL"],
        "outputs": ["$RUNS/out/result.json", "$RUNS/out/records"]}]}
    (repo / "manifest.json").write_text(json.dumps(man, indent=1))
    for c in (["git", "init", "-q"], ["git", "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid",
                                      "add", "."],
              ["git", "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "commit", "-q", "-m", "fixture"]):
        r = sh(*c, cwd=repo)
        if r.returncode:
            raise SystemExit(r.stderr)
    return {"repo": repo}


def runner(repo: Path, runs: Path):
    r = sh(sys.executable, str(RUNNER), "run", "--manifest", str(repo / "manifest.json"), "--repo", str(repo),
           "--runs-root", str(runs), "--isaac-python", sys.executable, "--task-timeout-s", "120")
    text = r.stdout + r.stderr
    decisive = [l for l in text.splitlines() if any(k in l for k in
                ("skip demo", "run demo", "integrity mismatch", "provenance", "Unverifiable", "rc=", "failed"))]
    return r.returncode, decisive[-3:]


def launches(runs: Path) -> int:
    c = runs / "counter.txt"
    return len(c.read_text().splitlines()) if c.exists() else 0


def scenario(base: Path, name: str, mutate, expect: str, pre=None) -> dict:
    fx = fixture(base / name)
    repo, runs = fx["repo"], base / name / "runs"
    if pre:
        pre(repo, runs)
    rc1, _ = runner(repo, runs)
    first = launches(runs)
    note = mutate(repo, runs) if mutate else None
    before = launches(runs)
    rc2, msg = runner(repo, runs)
    after = launches(runs)
    out = {"scenario": name, "first_run_rc": rc1, "first_run_launches": first, "mutation": note,
           "second_run_rc": rc2, "second_run_new_launches": after - before,
           "decisive_output": [m.replace(str(base.resolve()), "<work>").replace(str(base), "<work>") for m in msg],
           "expected": expect}
    if expect == "skip":
        out["passed"] = rc1 == 0 and rc2 == 0 and after == before and any("skip demo" in m for m in msg)
    elif expect == "rerun_after_failure":
        out["passed"] = rc1 != 0 and after == before + 1 and rc2 == 0 and not any("skip demo" in m for m in msg)
    elif expect == "refuse":
        out["passed"] = rc1 == 0 and rc2 != 0 and after == before and not any("skip demo" in m for m in msg)
    else:  # rerun
        out["passed"] = after == before + 1 and not any("skip demo" in m for m in msg)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", required=True, help="new empty directory for disposable fixtures")
    ap.add_argument("--output", default=str(ROOT / "results/post_v3/cache_demo.json"))
    a = ap.parse_args()
    base = Path(a.work)
    base.mkdir(parents=True, exist_ok=True)
    if any(base.iterdir()):
        raise SystemExit(f"{base} is not empty")

    def edit_bytes(repo, runs):
        p = runs / "out/result.json"
        b = bytearray(p.read_bytes()); b[-2] ^= 1; p.write_bytes(bytes(b))
        return "flipped one bit of out/result.json"

    def dir_add(repo, runs):
        (runs / "out/records/extra.jsonl").write_text("unexpected\n")
        return "added out/records/extra.jsonl"

    def dir_remove(repo, runs):
        (runs / "out/records/b.jsonl").unlink()
        return "removed out/records/b.jsonl"

    def change_ckpt(repo, runs):
        (repo / "checkpoint.pt").write_bytes(b"weights-v2")
        for c in (["git", "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qam", "new weights"],):
            sh(*c, cwd=repo)
        return "replaced checkpoint.pt (committed, clean tree)"

    def legacy(repo, runs):
        lp = runs / "ledger/demo.jsonl"
        rows = [json.loads(l) for l in lp.read_text().splitlines()]
        last = rows[-1]
        last.pop("output_fingerprints", None)
        last.pop("cache_context", None)
        last["outputs"] = {k: (hashlib.sha256(Path(k).read_bytes()).hexdigest() if Path(k).is_file() else "dir")
                           for k in last["outputs"]}
        lp.write_text("".join(json.dumps(r) + "\n" for r in rows[:-1] + [last]))
        return "rewrote latest ledger row in the pre-repair format (file hashes only, no fingerprints/context)"

    def missing(repo, runs):
        (runs / "out/result.json").unlink()
        return "deleted out/result.json"

    def fail_first(repo, runs):
        runs.mkdir(parents=True, exist_ok=True)
        (runs / "FAIL").write_text("1")

    def failed_latest(repo, runs):
        (runs / "FAIL").unlink()
        led = [json.loads(l) for l in (runs / "ledger/demo.jsonl").read_text().splitlines()]
        return (f"attempt 1 wrote every output then exited rc {led[-1]['rc']} "
                f"(outputs_exist={led[-1]['outputs_exist']}); failure flag removed")

    results = [
        scenario(base, "repeat_skip", None, "skip"),
        scenario(base, "edited_output_bytes", edit_bytes, "refuse"),
        scenario(base, "directory_add", dir_add, "refuse"),
        scenario(base, "directory_remove", dir_remove, "refuse"),
        scenario(base, "changed_checkpoint", change_ckpt, "refuse"),
        scenario(base, "legacy_ledger", legacy, "refuse"),
        scenario(base, "missing_output", missing, "rerun"),
        scenario(base, "failed_latest_attempt", failed_latest, "rerun_after_failure", pre=fail_first),
    ]
    rec = {"runner": "scripts/v3_jobs.py", "runner_sha256": hashlib.sha256(RUNNER.read_bytes()).hexdigest(),
           "python": sys.version.split()[0], "fixtures": "disposable git repositories; no released artifact touched",
           "scenarios": results, "all_passed": all(r["passed"] for r in results)}
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(rec, indent=1) + "\n")
    for r in results:
        print(f"{r['scenario']:24s} passed={r['passed']} rc={r['second_run_rc']} new_launches={r['second_run_new_launches']}")
    raise SystemExit(0 if rec["all_passed"] else 1)


if __name__ == "__main__":
    main()
