#!/usr/bin/env python3
"""Compare regenerated v2 summaries with the archived ones (CPU only, standard library).

    python3 scripts/closeout_regen_compare.py --regen <work>/regen --archived results/v2 --output comparison.json

Pairs: regen/final/selection <-> results/v2/final/selection, regen/summary <-> results/v2/summary,
regen/diagnostics <-> results/v2/diagnostics, regen/pilot <-> results/v2/pilot. Each archived file is classified
as identical (bytes), float_only (same structure, same text and integer fields, numbers differ by at most
1e-9 relative or in the last printed digit), substantive (any count, label or structural difference, or a
larger numeric change), figure (PNG: compared by image size only; bytes depend on library builds) or
not_regenerated (no regenerated counterpart).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import struct
from pathlib import Path

PAIRS = [("final/selection", "final/selection"), ("summary", "summary"), ("diagnostics", "diagnostics"),
         ("pilot", "pilot")]
NUM = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")


def png_size(p: Path):
    b = p.read_bytes()[:24]
    return struct.unpack(">II", b[16:24]) if b[:8] == b"\x89PNG\r\n\x1a\n" else None


def flatten(o, pre=""):
    if isinstance(o, dict):
        for k in sorted(o):
            yield from flatten(o[k], f"{pre}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from flatten(v, f"{pre}[{i}]")
    else:
        yield pre, o


def cmp_values(a: list, b: list) -> dict:
    """a, b: lists of (path, value). Returns worst numeric relative diff and structural/text/int mismatches."""
    if [p for p, _ in a] != [p for p, _ in b]:
        return {"structure": False}
    worst, bad = 0.0, []
    for (p, x), (_, y) in zip(a, b):
        if x == y:
            continue
        fx, fy = to_num(x), to_num(y)
        if fx is None or fy is None:
            bad.append((p, x, y))
            continue
        if float(fx).is_integer() and float(fy).is_integer() and "." not in str(x) + str(y):
            bad.append((p, x, y))
            continue
        rel = abs(fx - fy) / max(abs(fx), abs(fy), 1e-300)
        worst = max(worst, rel)
    return {"structure": True, "worst_rel": worst, "mismatch": bad[:10], "n_mismatch": len(bad)}


def to_num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return None
    return None


def tokens(text: str) -> list:
    """Text -> [(position, token)] where numbers become floats (for Markdown/CSV tables)."""
    out = []
    for i, part in enumerate(re.split(r"(" + NUM.pattern + r")", text)):
        out.append((f"t{i}", part if i % 2 == 0 else part))
    return out


def classify(a: Path, b: Path) -> dict:
    if a.read_bytes() == b.read_bytes():
        return {"class": "identical"}
    if a.suffix == ".png":
        return {"class": "figure", "size_equal": png_size(a) == png_size(b)}
    if a.suffix == ".json":
        r = cmp_values(list(flatten(json.loads(a.read_text()))), list(flatten(json.loads(b.read_text()))))
    elif a.suffix == ".csv":
        ra = list(csv.reader(io.StringIO(a.read_text())))
        rb = list(csv.reader(io.StringIO(b.read_text())))
        r = cmp_values([(f"{i}/{j}", v) for i, row in enumerate(ra) for j, v in enumerate(row)],
                       [(f"{i}/{j}", v) for i, row in enumerate(rb) for j, v in enumerate(row)])
    else:
        r = cmp_values(tokens(a.read_text()), tokens(b.read_text()))
    if not r.get("structure"):
        return {"class": "substantive", "reason": "structure differs"}
    if r["n_mismatch"]:
        return {"class": "substantive", "reason": "text/integer fields differ", "examples": r["mismatch"]}
    # last printed digit: a 1-ulp-in-print change of a 6-digit number is < 1e-5 relative
    return {"class": "float_only" if r["worst_rel"] < 1e-5 else "substantive",
            "worst_relative_difference": r["worst_rel"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--regen", required=True)
    ap.add_argument("--archived", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    R, A = Path(a.regen), Path(a.archived)
    files, summ = {}, {}
    for rr, ar in PAIRS:
        for f in sorted((A / ar).rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(A).as_posix()
            g = R / rr / f.relative_to(A / ar)
            res = classify(g, f) if g.exists() else {"class": "not_regenerated"}
            res["sha256_archived"] = hashlib.sha256(f.read_bytes()).hexdigest()
            if g.exists():
                res["sha256_regenerated"] = hashlib.sha256(g.read_bytes()).hexdigest()
            files[rel] = res
            summ[res["class"]] = summ.get(res["class"], 0) + 1
    out = {"summary": summ, "substantive": [k for k, v in files.items() if v["class"] == "substantive"],
           "not_regenerated": [k for k, v in files.items() if v["class"] == "not_regenerated"], "files": files}
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("summary", "substantive", "not_regenerated")}, indent=1))


if __name__ == "__main__":
    main()
