#!/usr/bin/env python3
"""Regenerate every V5 analysis table and figure from raw records (e.g. an extracted release download) and compare
with the committed results (CPU; numpy + matplotlib, the pinned analysis environment).

    python3 scripts/v5_regen.py --runs <extracted release dir> --work <empty dir> [--v4-raw-final <raw-final.tar.gz>]

Steps (outputs into <work>/): Study A preregistered analysis + taxonomy; slip probe summary; Study B checkpoint
selection (validation records + checkpoint hashes), development-fitted constants, preregistered analysis, then
figures. Compares every generated JSON/MD file with the committed file under results/v5/ (identical bytes,
numerically equal within a relative tolerance of 1e-9 ("float_only"), or different) and every figure PNG byte for
byte. Exit 1 on any different table, failed step or different figure.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def close(a, b, path="", out=None, tol=1e-9):
    out = [] if out is None else out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(f"{path}.{k}: missing on one side")
            else:
                close(a[k], b[k], f"{path}.{k}", out, tol)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}: length {len(a)} vs {len(b)}")
        for i, (x, y) in enumerate(zip(a, b)):
            close(x, y, f"{path}[{i}]", out, tol)
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        if not (a == b or (math.isfinite(a) and math.isfinite(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b)))):
            out.append(f"{path}: {a} vs {b}")
    elif a != b:
        out.append(f"{path}: {str(a)[:60]} vs {str(b)[:60]}")
    return out


FIT = """
import sys, json
from pathlib import Path
sys.path.insert(0, {scripts!r})
import v5_slip_study as s
work = Path({work!r})
(work / "results/v5/slip/mechanisms").mkdir(parents=True, exist_ok=True)
s.ROOT = work
s.fit_constants(Path({devfit!r}))
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", required=True, help="extracted release: study_a/, development/, validation/, final/, ...")
    ap.add_argument("--work", required=True)
    ap.add_argument("--v4-raw-final", default=None)
    ap.add_argument("--output", default=None)
    a = ap.parse_args()
    X, W = Path(a.runs).resolve(), Path(a.work).resolve()
    W.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    sa_entries = ",".join(c["id"] for c in json.loads((ROOT / "configs/v5/calibration/analysis_plan.json").read_text())["configurations"])
    analysis = [py, "scripts/v5_slip_analysis.py", "--runs", str(X), "--out", str(W / "results/v5/slip/analysis")]
    if a.v4_raw_final:
        analysis += ["--v4-raw-final", str(Path(a.v4_raw_final).resolve())]
    steps = {
        "study_a": [py, "scripts/v5_calibration_analysis.py", "--records", str(X / "study_a/primary"), "--repeat",
                    str(X / "study_a/repeat"), "--out", str(W / "results/v5/calibration")],
        "study_a_taxonomy": [py, "scripts/v5_taxonomy_records.py", "--records", str(X / "study_a/primary"), "--entries",
                             sa_entries, "--title", "V5 Study A", "--out", str(W / "results/v5/calibration/taxonomy")],
        "probe": [py, "scripts/v5_probe_summary.py", "--runs", str(X / "development/probe"), "--out",
                  str(W / "results/v5/slip/probe/summary.json")],
        "selection": [py, "scripts/v5_slip_study.py", "select", "--validation", str(X / "validation"), "--checkpoint-root",
                      str(X / "formal/train"), "--output", str(W / "results/v5/slip/selection")],
        "constants": [py, "-c", FIT.format(scripts=str(ROOT / "scripts"), work=str(W), devfit=str(X / "mechanisms/devfit"))],
        "analysis": analysis,
    }
    rec = {"runs": "<extracted>", "steps": {}, "files": {}}
    fail = []
    for name, cmd in steps.items():
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        rec["steps"][name] = {"command": " ".join(c.replace(str(X), "<extracted>").replace(str(W), "<work>") for c in cmd[1:])
                              if name != "constants" else "fit_constants(<extracted>/mechanisms/devfit)",
                              "exit_code": r.returncode}
        if r.returncode:
            rec["steps"][name]["stderr_tail"] = r.stderr[-1500:]
            fail.append(name)
    fig_cmd = [py, "scripts/v5_figures.py", "--study-a", str(W / "results/v5/calibration/summary.json"), "--probe-traces",
               str(X / "development/probe/mechanisms_r2/traces/calibrated_M6.json"), "--study-b",
               str(W / "results/v5/slip/analysis/summary.json"), "--train", str(X / "formal/train"), "--selection",
               str(W / "results/v5/slip/selection"), "--output", str(W / "results/v5/figures")]
    fig = subprocess.run(fig_cmd, cwd=ROOT, capture_output=True, text=True)
    figs = {p.name: (p.read_bytes() == (ROOT / "results/v5/figures" / p.name).read_bytes()
                     if (ROOT / "results/v5/figures" / p.name).exists() else "not committed")
            for p in sorted((W / "results/v5/figures").glob("*.png"))}
    rec["steps"]["figures"] = {"exit_code": fig.returncode, "figures_identical": figs}
    if fig.returncode or not figs or any(v is not True for v in figs.values()):
        fail.append("figures")
    counts = {"identical": 0, "float_only": 0, "different": 0, "missing": 0}
    for gen in sorted((W / "results/v5").rglob("*")):
        if not gen.is_file() or gen.suffix not in (".json", ".md"):
            continue
        rel = gen.relative_to(W)
        com = ROOT / rel
        if not com.exists():
            rec["files"][str(rel)] = "not committed"
            counts["missing"] += 1
            continue
        if gen.read_bytes() == com.read_bytes():
            rec["files"][str(rel)] = "identical"
            counts["identical"] += 1
            continue
        d = close(json.loads(gen.read_text()), json.loads(com.read_text())) if gen.suffix == ".json" else ["text differs"]
        if d:
            rec["files"][str(rel)] = {"status": "different", "first": d[:10], "n": len(d)}
            counts["different"] += 1
        else:
            rec["files"][str(rel)] = "float_only"
            counts["float_only"] += 1
    rec["counts"] = counts
    rec["ok"] = not fail and counts["different"] == 0
    rec["failed_steps"] = fail
    out = Path(a.output) if a.output else W / "regen.json"
    out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({"ok": rec["ok"], "counts": counts, "failed_steps": fail}))
    raise SystemExit(0 if rec["ok"] else 1)


if __name__ == "__main__":
    main()
