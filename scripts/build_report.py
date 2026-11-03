#!/usr/bin/env python3
"""Assemble report/report.md from its parts and render report/report.pdf (Markdown -> HTML -> headless Chrome).

Usage: python3 scripts/build_report.py [--chrome google-chrome]
Requires the `markdown` Python package and a Chrome/Chromium binary for the PDF.
"""

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS = ["report_front.md", "report_methods.md", "report_results.md", "report_tail.md"]
CSS = """
body { font-family: 'DejaVu Serif', Georgia, serif; font-size: 10.5pt; line-height: 1.38; max-width: 7.0in;
       margin: 0 auto; color: #111; }
h1 { font-size: 17pt; margin-bottom: 0.1em; } h2 { font-size: 13pt; margin-top: 1.2em;
     border-bottom: 1px solid #bbb; } h3 { font-size: 11.5pt; }
.meta { color: #444; margin-bottom: 1.2em; }
table { border-collapse: collapse; font-size: 9pt; margin: 0.6em 0; } th, td { border: 1px solid #aaa;
        padding: 2px 6px; } th { background: #eee; }
img { max-width: 100%; } code { font-size: 9pt; } p, li { text-align: justify; }
@page { size: letter; margin: 0.75in; }
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chrome", default="google-chrome")
    a = ap.parse_args()
    import markdown

    rep = ROOT / "report"
    text = "\n\n".join((rep / p).read_text() for p in PARTS)
    (rep / "report.md").write_text(text)
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    meta = dict(re.findall(r'^(\w+): "(.*)"$', m.group(1), re.M)) if m else {}
    body = text[m.end():] if m else text
    html_body = markdown.markdown(body, extensions=["tables", "fenced_code"])
    head = (f"<h1>{meta.get('title', '')}</h1><div class='meta'>{meta.get('subtitle', '')}<br>"
            f"{meta.get('author', '')} &middot; {meta.get('date', '')}</div>")
    html = f"<!doctype html><html><head><meta charset='utf-8'><title>{meta.get('title','Report')}</title>" \
           f"<style>{CSS}</style></head><body>{head}{html_body}</body></html>"
    (rep / "report.html").write_text(html)
    subprocess.run([a.chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={rep / 'report.pdf'}", (rep / "report.html").as_uri()], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"wrote {rep / 'report.md'} and {rep / 'report.pdf'}")


if __name__ == "__main__":
    main()
