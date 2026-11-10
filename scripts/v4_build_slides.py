#!/usr/bin/env python3
"""Build the V4 presentation: report/v4/slides.pptx (editable), slides.pdf (LibreOffice), speaker_notes.md,
and results/v4/slide_numbers.json (every number on a slide or in its notes -> report_values key and source).

    python3 scripts/v4_build_slides.py [--soffice libreoffice]

Requires python-pptx. All measured numbers come from results/v4/report_values.json (scripts/v4_report_values.py);
design constants (budgets, case counts, seeds) are written directly.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "report/v4"
DARK = RGBColor(0x1F, 0x2A, 0x44)
ACC = RGBColor(0x2E, 0x6F, 0xB7)
GREY = RGBColor(0x55, 0x55, 0x55)
V = json.loads((ROOT / "results/v4/report_values.json").read_text())
AUDIT: list[dict] = []
CUR = {"slide": 0}


def n(key: str) -> str:
    """Formatted value of a report_values key; logged in the slide number audit."""
    v = V[key]
    AUDIT.append({"document": "report/v4/slides.pptx", "slide": CUR["slide"], "key": key, "text": v["text"],
                  "source": v["source"], "field": v["field"]})
    return v["text"]


def title(slide, text, sub=None):
    tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.25), Inches(12.3), Inches(0.9))
    tb.text_frame.word_wrap = True
    p = tb.text_frame.paragraphs[0]
    p.text = text
    p.font.size, p.font.bold, p.font.color.rgb = Pt(28), True, DARK
    if sub:
        p2 = tb.text_frame.add_paragraph()
        p2.text = sub
        p2.font.size, p2.font.color.rgb = Pt(15), ACC


def bullets(slide, items, x=0.5, y=1.45, w=12.3, h=5.6, size=17):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, it in enumerate(items):
        level = 1 if it.startswith("  ") else 0
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = ("– " if level else "• ") + it.strip()
        p.level = level
        p.font.size = Pt(size - 3 * level)
        p.space_after = Pt(6)


def table(slide, rows, x, y, w, h, size=12, first_col_w=None):
    t = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(h)).table
    if first_col_w:
        t.columns[0].width = Inches(first_col_w)
        rest = (w - first_col_w) / (len(rows[0]) - 1)
        for j in range(1, len(rows[0])):
            t.columns[j].width = Inches(rest)
    for i, r in enumerate(rows):
        for j, v in enumerate(r):
            c = t.cell(i, j)
            c.text = str(v)
            for p in c.text_frame.paragraphs:
                p.font.size = Pt(size)
                p.font.bold = i == 0
    return t


def pic(slide, path, x, y, w=None, h=None):
    kw = {}
    if w:
        kw["width"] = Inches(w)
    if h:
        kw["height"] = Inches(h)
    slide.shapes.add_picture(str(path), Inches(x), Inches(y), **kw)


def foot(slide, text):
    tb = slide.shapes.add_textbox(Inches(0.5), Inches(6.95), Inches(12.3), Inches(0.4))
    p = tb.text_frame.paragraphs[0]
    p.text = text
    p.font.size, p.font.color.rgb = Pt(11), GREY




def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--soffice", default="libreoffice")
    a = ap.parse_args()
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    F = ROOT / "results/v4/figures"
    notes_md = ["# V4 speaker notes", ""]

    def new(note_title):
        s = prs.slides.add_slide(blank)
        CUR["slide"] = len(prs.slides)
        s._note_title = note_title
        return s

    def notes(s, text):
        s.notes_slide.notes_text_frame.text = text
        notes_md.extend([f"## Slide {CUR['slide']}: {s._note_title}", "", text, ""])

    import slides_v4_content  # noqa: E402  (scripts/slides_v4_content.py: results slides, written after the analysis)

    slides_v4_content.build(prs, new, notes, n, title, bullets, table, pic, foot, F)
    prs.core_properties.author = "Yan Wen (CSCI 645); generated with Claude Code"
    prs.core_properties.title = "Uncertain giver grasp in bimanual handover — V4"
    prs.core_properties.last_modified_by = "csci645-v4"
    out = OUT / "slides.pptx"
    prs.save(out)
    (OUT / "speaker_notes.md").write_text("\n".join(notes_md) + "\n")
    (ROOT / "results/v4/slide_numbers.json").write_text(json.dumps(AUDIT, indent=1) + "\n")
    subprocess.run([a.soffice, "--headless", "--convert-to", "pdf", "--outdir", str(OUT), str(out)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"{len(prs.slides)} slides, {len(AUDIT)} audited numbers")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
