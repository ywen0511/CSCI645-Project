#!/usr/bin/env python3
"""Render report/v4/report.md to PDF via HTML + headless Chrome.

    python3 scripts/v4_build_report.py [--chrome google-chrome]

Requires the `markdown` package and Chrome/Chromium. Writes report/v4/report.html and report/v4/report.pdf.
"""

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GITHUB = "https://github.com/ywen0511/CSCI645-Project"
REF = "v4.0.0"  # release tag of this report
CSS = """
body { font-family: 'DejaVu Serif', Georgia, serif; font-size: 10pt; line-height: 1.36; max-width: 7.0in; margin: 0 auto; color: #111; }
h1 { font-size: 16pt; margin-bottom: 0.1em; } h2 { font-size: 12.5pt; margin-top: 1.1em; border-bottom: 1px solid #bbb; }
h3 { font-size: 11pt; } .meta { color: #444; margin-bottom: 1.1em; }
table { border-collapse: collapse; font-size: 7.4pt; margin: 0.5em 0; page-break-inside: auto; } tr { page-break-inside: avoid; }
th, td { border: 1px solid #aaa; padding: 1px 3px; } th { background: #eee; }
img { max-width: 100%; page-break-inside: avoid; } code { font-size: 8.5pt; } p, li { text-align: justify; }
@page { size: letter; margin: 0.7in; }
"""


def render(md_path: Path, chrome: str) -> Path:
    import markdown

    text = md_path.read_text()
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    meta = dict(re.findall(r'^(\w+): "(.*)"$', m.group(1), re.M)) if m else {}
    body = text[m.end():] if m else text
    html_body = markdown.markdown(body, extensions=["tables", "fenced_code"])
    # Relative links would be printed as absolute file:// URIs of the build machine; point them to GitHub instead.
    base = md_path.parent.relative_to(ROOT).as_posix()

    def gh(m):
        href = m.group(1)
        if re.match(r"^[a-z]+:", href) or href.startswith("#"):
            return m.group(0)
        path, _, frag = href.partition("#")
        full = (Path(base) / path).as_posix()
        parts = []
        for x in full.split("/"):
            if x == "..":
                parts.pop()
            elif x not in ("", "."):
                parts.append(x)
        url = f"{GITHUB}/{'tree' if path.endswith('/') else 'blob'}/{REF}/{'/'.join(parts)}" + (f"#{frag}" if frag else "")
        return f'href="{url}"'

    html_body = re.sub(r'href="([^"]+)"', gh, html_body)
    head = (f"<h1>{meta.get('title', '')}</h1><div class='meta'>{meta.get('subtitle', '')}<br>{meta.get('author', '')}"
            f" &middot; {meta.get('date', '')}</div>") if meta else ""
    html = (f"<!doctype html><html><head><meta charset='utf-8'><title>{meta.get('title', md_path.stem)}</title>"
            f"<style>{CSS}</style></head><body>{head}{html_body}</body></html>")
    out_html = md_path.with_suffix(".html")
    out_html.write_text(html)
    pdf = md_path.with_suffix(".pdf")
    subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf}",
                    out_html.as_uri()], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return pdf


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chrome", default="google-chrome")
    a = ap.parse_args()
    for name in ("report.md",):
        print("wrote", render(ROOT / "report/v4" / name, a.chrome))


if __name__ == "__main__":
    main()
