#!/usr/bin/env python3
"""Check the numbers written in the report against the machine-readable summaries (CPU, standard library).

    python3 scripts/closeout_check_numbers.py [--report report/v2/report.md] [--output results/closeout/number_check.json]

Checked: every cell of the report's main results table (§5.1) and primary comparison table (§5.2) against
results/v2/summary/summary.json; the summary-bullet headline numbers; every cell of the supplementary
repeatability table (§5.5) against results/closeout/repeatability/comparisons.csv and summary.json. A number
matches when it equals the summary value rounded to the printed precision. Exit code 1 on any mismatch.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NUM = re.compile(r"[−+-]?\d+(?:\.\d+)?")


def f(x: str) -> float:
    return float(x.replace("−", "-").replace("+", ""))


def dec(x: str) -> int:
    return len(x.split(".")[1]) if "." in x else 0


def table_after(md: str, heading: str) -> list[list[str]]:
    i = md.index(heading)
    lines = md[i:].splitlines()
    rows, started = [], False
    for l in lines[1:]:
        if l.startswith("|"):
            started = True
            if not re.match(r"^\|[-| ]+\|$", l):
                rows.append([c.strip() for c in l.strip("|").split("|")])
        elif started:
            break
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", default=str(ROOT / "report/v2/report.md"))
    ap.add_argument("--output", default=str(ROOT / "results/closeout/number_check.json"))
    a = ap.parse_args()
    md = Path(a.report).read_text()
    S = json.loads((ROOT / "results/v2/summary/summary.json").read_text())
    pe = S["per_entry"]
    comp = {(c["comparison"], c["role"], c["cases"]): c for c in S["comparisons"] if c["metric"] == "success"}
    checks, bad = [], []

    def check(label, printed, value):
        ok = abs(round(value, dec(printed)) - f(printed)) < 1e-9
        checks.append({"what": label, "printed": printed, "computed": value, "ok": ok})
        if not ok:
            bad.append(checks[-1])

    def rate(e, g):
        return 100 * pe[e][g]["success_rate_valid"]

    def learned(m, role, g):
        return sum(rate(f"{m}_seed{s}__{role}", g) for s in (11, 22, 33)) / 3

    rows = {
        "nominal": lambda g: rate("nominal", g), "nominal + 9 mm": lambda g: rate("const_nominal", g),
        "geometry 1 cm (v1 setting)": lambda g: rate("geometry_1cm", g), "geometry 1.5 cm": lambda g: rate("geometry_1p5cm", g),
        "geometry 1.5 cm + 10 mm": lambda g: rate("const_geometry_1p5cm", g),
        "residual, selected (mean of 3 seeds)": lambda g: learned("residual", "selected", g),
        "residual, final": lambda g: learned("residual", "final", g),
        "combined, selected": lambda g: learned("combined", "selected", g),
        "combined, final": lambda g: learned("combined", "final", g),
        "combined, untrained (step 0)": lambda g: learned("combined", "untrained", g),
        "combined_no_phase, selected": lambda g: learned("combined_no_phase", "selected", g)}
    t = table_after(md, "### 5.1 Main results")
    groups = ["inner", "outer", "extrapolation", "all"]
    for r in t[1:]:
        fn = rows[r[0]]
        for g, cell in zip(groups, r[1:]):
            check(f"5.1 {r[0]} / {g}", NUM.search(cell.replace("*", "")).group(0), fn(g))
    names = {"combined − geometry 1.5 cm": "combined - geometry_1p5cm",
             "combined − (geometry 1.5 cm + 10 mm)": "combined - const_geometry_1p5cm",
             "residual − nominal": "residual - nominal", "residual − (nominal + 9 mm)": "residual - const_nominal",
             "combined − combined_no_phase": "combined - combined_no_phase"}
    t = table_after(md, "### 5.2 Primary and declared secondary comparisons")
    for r in t[1:]:
        key = names[r[0]]
        for role, cell in (("selected", r[1]), ("final", r[3])):
            nums = NUM.findall(cell.replace("*", ""))
            c = comp[(key, role, "all")]
            for lab, p, v in zip(("diff", "ci_low", "ci_high"), nums, (c["diff"], c["ci_low"], c["ci_high"])):
                check(f"5.2 {r[0]} / {role} / {lab}", p, 100 * v)
    # headline numbers in the summary bullets
    for printed, value, lab in (("65.2", rate("nominal", "all"), "nominal all"),
                                ("82.6", learned("residual", "selected", "all"), "residual all"),
                                ("96.1", learned("combined", "selected", "all"), "combined all"),
                                ("96.5", rate("geometry_1p5cm", "all"), "geometry 1.5 all"),
                                ("99.2", rate("const_geometry_1p5cm", "all"), "geometry+const all"),
                                ("69.3", rate("const_nominal", "all"), "nominal+const all")):
        if printed not in md:
            bad.append({"what": f"summary {lab}", "printed": None, "computed": value, "ok": False})
        check(f"summary {lab}", printed, value)
    # supplementary table
    cp = ROOT / "results/closeout/repeatability/comparisons.csv"
    if "### 5.5" in md and cp.exists():
        C = list(csv.DictReader(open(cp)))
        t = table_after(md, "### 5.5")
        hdr = t[0]
        for r in t[1:]:
            lay = r[0]
            m = re.match(r"(?:batch )?(\d+|v2\.0\.0.*?), (repeat (\d)|mean of 3 repeats)", lay)
            if lay.startswith("v2.0.0"):
                b, rp = "archived (900, seed 0)", "v2.0.0"
            elif m:
                b, rp = m.group(1), (m.group(3) or "mean of repeats")
            else:
                continue
            for col, cell in zip(hdr[1:], r[1:]):
                role = "final" if "final" in col else "selected"
                name = "combined - const_geometry_1p5cm" if "const" in col or "10 mm" in col else "combined - geometry_1p5cm"
                row = next(x for x in C if x["batch_size"] == b and x["repeat"] == rp and x["role"] == role
                           and x["comparison"] == name)
                nums = NUM.findall(cell.replace("*", ""))
                for lab, p, k in zip(("diff", "lo", "hi"), nums, ("diff_pp", "ci_low_pp", "ci_high_pp")):
                    check(f"5.5 {lay} / {col} / {lab}", p, float(row[k]))
    out = {"report": Path(a.report).relative_to(ROOT).as_posix(), "checked": len(checks), "mismatches": bad,
           "ok": not bad}
    Path(a.output).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"checked": len(checks), "mismatches": len(bad), "first": bad[:5]}, indent=1))
    raise SystemExit(0 if not bad else 1)


if __name__ == "__main__":
    main()
