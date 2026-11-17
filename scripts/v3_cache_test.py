#!/usr/bin/env python3
"""Acceptance check 10: evaluation resume only re-executes genuinely missing cases, and stale records are
rejected (CPU orchestration; each evaluation is a fresh simulator process). Works on disposable copies only.

    python3 scripts/v3_cache_test.py --isaac-python <py> \
        --matrix configs/v3/acceptance/a1_b8.json --entry geometry_1p5cm \
        --ckpt-matrix configs/v3/acceptance/a2_combined_robust_ff.json --ckpt-entry combined_robust_ff_step0 \
        --checkpoint-root <runs>/smoke --work <runs>/acceptance/cache_test --output <runs>/acceptance/cache_test.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from v3_jobs import supervise  # noqa: E402


def evaluate(py, matrix, entry, out, ckroot, log):
    cmd = ["bash", str(ROOT / "scripts/cluster/isaac_run.sh"), py, "scripts/eval_matrix.py", "--matrix", matrix,
           "--only", entry, "--output", str(out), "--seed", "6455501"] + (["--checkpoint-root", ckroot] if ckroot else [])
    rc, wd = supervise(cmd, log, [out / f"{entry}.jsonl"], 1800)
    return rc, wd, log.read_text(errors="replace")


def lines(p):
    return [l for l in p.read_text().splitlines() if l.strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ("isaac-python", "matrix", "entry", "ckpt-matrix", "ckpt-entry", "checkpoint-root", "work", "output"):
        ap.add_argument(f"--{k}", required=True)
    a = ap.parse_args()
    W = Path(a.work)
    if W.exists():
        shutil.rmtree(W)  # disposable folder owned by this test
    W.mkdir(parents=True)
    # fresh baselines at THIS source commit (records from another commit would correctly be rejected as stale)
    base = W / "baseline"
    rc0, wd0, _ = evaluate(a.isaac_python, a.matrix, a.entry, base, None, W / "baseline.log")
    ckbase = W / "baseline_ckpt"
    rc1, wd1, _ = evaluate(a.isaac_python, a.ckpt_matrix, a.ckpt_entry, ckbase, a.checkpoint_root, W / "baseline_ckpt.log")
    a.source, a.ckpt_source = str(base), str(ckbase)
    src = Path(a.source) / f"{a.entry}.jsonl"
    original = lines(src)
    res, checks = {"cases": len(original)}, {}

    # (a) truncation: remove the last 3 records -> exactly those 3 are re-executed
    d = W / "truncated"
    shutil.copytree(a.source, d)
    (d / f"{a.entry}.jsonl").write_text("\n".join(original[:-3]) + "\n")
    rc, wd, log = evaluate(a.isaac_python, a.matrix, a.entry, d, None, W / "truncated.log")
    after = lines(d / f"{a.entry}.jsonl")
    msg = f"{len(original) - 3} existing, 3 to run"
    checks["truncated_reexecutes_only_missing"] = "MATRIX_DONE" in log and msg in log and len(after) == len(original) and \
        sorted(json.loads(x)["case_id"] for x in after) == sorted(json.loads(x)["case_id"] for x in original)
    res["truncated"] = {"rc": rc, "watchdog": wd, "expected_log": msg, "records_after": len(after)}

    # (b..d) tampered records are rejected (no silent reuse, no rewrite)
    for name, field, value, matrix, entry, source, ck in (
            ("config_hash", "config_hash", "0" * 64, a.matrix, a.entry, a.source, None),
            ("case_observation_error", "observation_error", {"seed": 1, "bias_xyz_m": [0, 0, 0], "noise_std_m": 0, "delay_steps": 0},
             a.matrix, a.entry, a.source, None),
            ("checkpoint_sha256", "checkpoint_sha256", "f" * 64, a.ckpt_matrix, a.ckpt_entry, a.ckpt_source, a.checkpoint_root)):
        d = W / f"tamper_{name}"
        shutil.copytree(source, d)
        p = d / f"{entry}.jsonl"
        rows = lines(p)
        r0 = json.loads(rows[0])
        r0[field] = value
        rows[0] = json.dumps(r0, sort_keys=True)
        p.write_text("\n".join(rows) + "\n")
        before = p.read_bytes()
        rc, wd, log = evaluate(a.isaac_python, matrix, entry, d, ck, W / f"tamper_{name}.log")
        stale = ("stale" in log or "mismatched" in log)
        # judged by the log, not rc: a Kit shutdown hang after the abort can be killed by the watchdog with rc 0
        checks[f"tampered_{name}_rejected"] = ("episodes scheduled" in log and " to run" not in log
                                               and "MATRIX_DONE" not in log and p.read_bytes() == before)
        res[f"tamper_{name}"] = {"rc": rc, "watchdog": wd, "error_text_seen": stale, "file_unchanged": p.read_bytes() == before}
    res["checks"], res["ok"] = checks, all(checks.values())
    res["note"] = ("matrix_status.json alone is never trusted: eval_matrix re-validates every existing record against the "
                   "suite, sensor realization, config/controller/checkpoint hashes and source commit")
    Path(a.output).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
