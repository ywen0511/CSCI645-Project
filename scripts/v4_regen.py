#!/usr/bin/env python3
"""Regenerate every V4 analysis table and figure from raw records (e.g. an extracted release download) and compare
with the committed results (CPU; numpy + matplotlib).

    python3 scripts/v4_regen.py --runs <extracted release dir> --work <empty dir> [--output <work>/regen.json]

Runs, each into <work>/: checkpoint selection (validation records + checkpoint hashes), main analysis (final
index), mechanisms and repeatability, then figures. Compares every generated JSON/CSV file with the committed file
under results/v4/ (identical bytes, numerically equal within a relative tolerance of 1e-9, or different), and every
figure PNG byte for byte. Exit 1 on any different table, failed step or different figure.
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", required=True, help="directory holding final/, validation/, zero_policy/, ... (extracted archives)")
    ap.add_argument("--work", required=True)
    ap.add_argument("--output", default=None)
    a = ap.parse_args()
    X, W = Path(a.runs).resolve(), Path(a.work).resolve()
    W.mkdir(parents=True, exist_ok=True)
    idx = "configs/v4/final_matrix_index.json"  # relative to the repository (cwd of every step)
    py = sys.executable
    steps = {
        "selection": [py, "scripts/v4_select_checkpoints.py", "--validation", str(X / "validation"), "--checkpoint-root",
                      str(X / "formal/train"), "--output", str(W / "selection")],
        "summary": [py, "scripts/v4_analyze.py", "--index", idx, "--root", str(X), "--output", str(W / "summary")],
        "constants": [py, "scripts/v4_fit_constants.py", "--devfit", str(X / "mechanisms/devfit"), "--output",
                      str(W / "mechanisms/constant_fits.json")],
        "mechanisms": [py, "scripts/v4_mechanisms.py", "--runs", str(X), "--output", str(W / "mechanisms")],
        "traces6": [py, "scripts/v4_traces6.py", "--runs", str(X), "--output", str(W / "traces6/summary.json")],
    }
    rec = {"runs": "<extracted>", "steps": {}, "files": {}}
    fail = []
    for name, cmd in steps.items():
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        rec["steps"][name] = {"command": " ".join(c.replace(str(X), "<extracted>").replace(str(W), "<work>") for c in cmd[1:]),
                              "exit_code": r.returncode}
        if r.returncode:
            rec["steps"][name]["stderr_tail"] = r.stderr[-1500:]
            fail.append(name)
    fig = subprocess.run([py, "scripts/v4_figures.py", "--summary", str(W / "summary"), "--runs", str(X), "--train",
                          str(X / "formal/train"), "--index", idx, "--output", str(W / "figures")], cwd=ROOT, capture_output=True, text=True)
    figs = {p.name: (p.read_bytes() == (ROOT / "results/v4/figures" / p.name).read_bytes()
                     if (ROOT / "results/v4/figures" / p.name).exists() else "not committed")
            for p in sorted((W / "figures").glob("*.png"))}
    rec["steps"]["figures"] = {"exit_code": fig.returncode, "figures_identical": figs}
    if fig.returncode or not figs or any(v is not True for v in figs.values()):
        fail.append("figures")
    counts = {"identical": 0, "float_only": 0, "different": 0, "missing": 0}
    for name in sorted({"selection", "summary", "mechanisms", "traces6"}):
        for gen in sorted((W / name).rglob("*")):
            if not gen.is_file() or gen.suffix not in (".json", ".csv"):
                continue
            rel = gen.relative_to(W)
            com = ROOT / "results/v4" / rel
            if not com.exists():
                rec["files"][str(rel)] = "not committed"
                counts["missing"] += 1
                continue
            if gen.read_bytes() == com.read_bytes():
                rec["files"][str(rel)] = "identical"
                counts["identical"] += 1
                continue
            if gen.suffix == ".json":
                d = close(json.loads(gen.read_text()), json.loads(com.read_text()))
            else:
                ga = [l.split(",") for l in gen.read_text().splitlines()]
                ca = [l.split(",") for l in com.read_text().splitlines()]
                conv = lambda t: [[float(x) if x.replace(".", "", 1).replace("-", "", 1).replace("e", "", 1).replace("+", "").isdigit() else x for x in r] for r in t]  # noqa: E731
                d = close(conv(ga), conv(ca))
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
