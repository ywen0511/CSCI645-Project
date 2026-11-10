#!/usr/bin/env python3
"""Render report/v4/report_template.md -> report/v4/report.md by substituting {{key}} from
results/v4/report_values.json, and write results/v4/number_audit.json (every substituted claim -> source).

    python3 scripts/v4_render_report.py [--template report/v4/report_template.md] [--extra report/v4/speaker_notes_template.md]

Fails on an unknown key or a leftover placeholder. Literal numbers that are design constants (budgets, case
counts, seeds) are written directly in the template; every measured result must come through a key.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEY = re.compile(r"\{\{([A-Za-z0-9_.\-]+)\}\}")


def render(tpl: Path, out: Path, V: dict, audit: list):
    text = tpl.read_text()
    missing = sorted({k for k in KEY.findall(text) if k not in V})
    if missing:
        raise SystemExit(f"{tpl}: unknown keys {missing}")
    for k in KEY.findall(text):
        audit.append({"document": str(out.relative_to(ROOT)), "key": k, "text": V[k]["text"] if not k.startswith("table.") else "(table)",
                      "source": V[k]["source"], "field": V[k]["field"]})
    res = KEY.sub(lambda m: V[m.group(1)]["text"], text)
    if "{{" in res:
        raise SystemExit("leftover placeholder")
    out.write_text(res)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--template", default=str(ROOT / "report/v4/report_template.md"))
    ap.add_argument("--extra", action="append", default=[], help="other templates (*_template.md -> *.md)")
    a = ap.parse_args()
    V = json.loads((ROOT / "results/v4/report_values.json").read_text())
    audit = []
    for t in [a.template] + a.extra:
        t = Path(t)
        render(t, t.with_name(t.name.replace("_template", "")), V, audit)
    slides = ROOT / "results/v4/slide_numbers.json"
    if slides.exists():
        audit += json.loads(slides.read_text())
    (ROOT / "results/v4/number_audit.json").write_text(json.dumps(audit, indent=1) + "\n")
    print(f"{len(audit)} audited numeric claims")


if __name__ == "__main__":
    main()
