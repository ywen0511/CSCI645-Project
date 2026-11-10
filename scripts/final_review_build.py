#!/usr/bin/env python3
"""Build the final synthesis Markdown, sensitivity figure and PDF on CPU.

Requires numpy, matplotlib and reportlab. No simulator, torch, browser or GPU is used.
The small Markdown renderer supports only the constructs used in the checked template.
"""
import argparse
import html
import json
from pathlib import Path
import re
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "report/final"
GITHUB = "https://github.com/ywen0511/CSCI645-Project/blob/study/v4-grasp-uncertainty/report/final/"


def data(path):
    return json.loads((ROOT / path).read_text())


def table(headers, rows):
    return "\n".join("| " + " | ".join(map(str, row)) + " |" for row in
                     [headers, ["---"] * len(headers), *rows])


def render_markdown(audit):
    summary = data("results/v4/summary/family_condition_summary.json")
    conditions = ["grasp_15mm", "mixed_id", "mixed_ood", "boundary_x_minus_7"]
    families = [("geometry_fixed", "Fixed geometry"), ("geometry_calibrated", "Calibrated geometry"),
                ("geometry_ema", "EMA geometry"), ("combined_robust_ff", "Robust feed-forward"),
                ("combined_robust_history", "Robust history"), ("combined_robust_repeat", "Repeated current frame"),
                ("residual_robust_history", "Residual-only history"), ("nominal", "Nominal")]
    rows = []
    for family, label in families:
        rates = [next(r["success_rate_mean"] for r in summary if r["family"] == family and
                      r["condition"] == c and r["role"] in ("selected", "baseline")) for c in conditions]
        rows.append([label, *[f"{v*100:.1f}" for v in rates]])
    values = {"main_table": table(["Controller", "Grasp-15", "Mixed ID", "Mixed OOD", "x = -7 mm"], rows)}
    rows = []
    for r in audit["primary_recomputed"]:
        if r["confidence"] == 0.975:
            label = "History minus feed-forward" if r["right"] == "combined_robust_ff" else "History minus best constant"
            rows.append([label, f"{r['difference_pp']:+.1f}", f"[{r['ci_low_pp']:+.1f}, {r['ci_high_pp']:+.1f}]"])
    values["primary_table"] = table(["Primary selected mixed-ID contrast", "Difference (pp)", "97.5% interval (pp)"], rows)
    common = [r for r in audit["boundary_sensitivity"] if r["cohort"] == "common_valid_posthoc"]
    labels = ["Robust history", "Robust feed-forward", "Repeated current frame"]
    values["sensitivity_table"] = table(["Selected controller", "Common-valid success", "Parent success", "Difference (pp)"],
                                        [[label, f"{r['success_pct']:.2f}%", f"{r['parent_success_pct']:.2f}%",
                                          f"{r['difference_pp']:+.2f}"] for label, r in zip(labels, common)])
    r = common[0]
    values["history_sensitivity"] = f"{r['difference_pp']:+.2f} pp, 95% CI [{r['ci_low_pp']:+.2f}, {r['ci_high_pp']:+.2f}]"
    template = (OUT / "overview_template.md").read_text()
    result = re.sub(r"\{\{(\w+)\}\}", lambda m: values[m[1]], template)
    if "{{" in result:
        raise ValueError("unresolved placeholder")
    (OUT / "overview.md").write_text(result)
    return result


def figure(audit):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8.0, 2.7), layout="constrained")
    for cohort, offset, color, label in [("all_scheduled", -0.12, "#2563a6", "All scheduled (200 cases)"),
                                        ("common_valid_posthoc", 0.12, "#b85914", "Common-valid (189 cases; post hoc)")]:
        rows = [r for r in audit["boundary_sensitivity"] if r["cohort"] == cohort]
        for i, r in enumerate(rows):
            d, lo, hi = (r[k] for k in ("difference_pp", "ci_low_pp", "ci_high_pp"))
            ax.errorbar(d, i + offset, xerr=[[d-lo], [hi-d]], fmt="o", color=color,
                        capsize=3, label=label if i == 0 else None)
    ax.axvline(0, color="#777777", lw=1, ls="--")
    ax.set_yticks(range(3), ["Robust history", "Robust feed-forward", "Repeated current"])
    ax.invert_yaxis()
    ax.set_xlabel("Success difference from calibrated parent (percentage points)")
    ax.set_xlim(-50, 5)
    ax.set_title("Palm-side boundary: the history deficit persists", loc="left", fontsize=12)
    ax.legend(loc="lower left", fontsize=8, frameon=False)
    ax.set_ylim(2.8, -0.6)
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(OUT / "boundary_sensitivity.png", dpi=200, metadata={"Software": "CSCI645 final_review_build.py"})
    plt.close(fig)


def build_pdf(markdown):
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
    from reportlab.lib.utils import ImageReader

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("Text", fontName="Helvetica", fontSize=10, leading=14, spaceAfter=8))
    styles.add(ParagraphStyle("Cell", fontName="Helvetica", fontSize=8, leading=10, spaceAfter=0))
    styles["Heading1"].textColor = colors.HexColor("#17365b")
    styles["Heading2"].textColor = colors.HexColor("#17365b")
    styles["Heading2"].spaceBefore = 12
    styles["Heading2"].spaceAfter = 10

    def inline(s):
        s = html.escape(s)
        s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: f'<a href="{html.escape(urljoin(GITHUB, html.unescape(m[2])), quote=True)}" color="#2563a6">{m[1]}</a>', s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
        s = re.sub(r"`([^`]+)`", r"<font name='Courier' size='8'>\1</font>", s)
        return s

    story = []
    for block in re.split(r"\n\s*\n", markdown.strip()):
        if block == "<!-- pagebreak -->":
            story.append(PageBreak())
        elif block.startswith("!["):
            path = OUT / re.search(r"\]\(([^)]+)\)", block)[1]
            w, h = ImageReader(str(path)).getSize()
            story.extend([Image(str(path), width=492, height=492*h/w), Spacer(1, 6)])
        elif block.startswith("|"):
            raw = [[c.strip() for c in line.strip().strip("|").split("|")] for line in block.splitlines()]
            rows = [r for r in raw if not all(re.fullmatch(r"[:\- ]+", c) for c in r)]
            cells = [[Paragraph(inline(c), styles["Cell"]) for c in r] for r in rows]
            widths = ([42, 128, 322] if len(cells[0]) == 3 and cells[0][0].text == "Stage" else
                      [160, 166, 166] if len(cells[0]) == 3 else
                      [160] + [332/(len(cells[0])-1)] * (len(cells[0])-1))
            t = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
            t.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#e8eef5")),
                                   ("VALIGN", (0,0), (-1,-1), "TOP"),
                                   ("LINEBELOW", (0,0), (-1,0), .6, colors.HexColor("#607d9b")),
                                   ("BOTTOMPADDING", (0,0), (-1,-1), 7), ("TOPPADDING", (0,0), (-1,-1), 7),
                                   ("LINEBELOW", (0,1), (-1,-1), .25, colors.HexColor("#d8dfe6"))]))
            story.extend([t, Spacer(1, 10)])
        elif block.startswith("# "):
            story.append(Paragraph(inline(block[2:]), styles["Title"]))
        elif block.startswith("## "):
            story.append(Paragraph(inline(block[3:]), styles["Heading2"]))
        elif block.startswith("- "):
            for line in block.splitlines():
                story.append(Paragraph(inline(line[2:]), styles["Text"], bulletText="-"))
        else:
            story.append(Paragraph(inline(" ".join(block.splitlines())), styles["Text"]))

    def footer(canvas, doc):
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#52677b"))
        canvas.drawString(60, 32, "CSCI 645 | Final synthesis and retrospective CPU review | November 2026")
        canvas.drawRightString(552, 32, str(doc.page))

    doc = SimpleDocTemplate(str(OUT / "overview.pdf"), pagesize=(612, 792), leftMargin=60, rightMargin=60,
                            topMargin=46, bottomMargin=52, title="Robust Bimanual Handover: Final Synthesis",
                            author="Yan Wen; AI assistance disclosed", invariant=1)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown-only", action="store_true")
    args = parser.parse_args()
    audit = data("results/final_review/audit.json")
    if not audit["passed"]:
        raise ValueError("audit has not passed")
    markdown = render_markdown(audit)
    if not args.markdown_only:
        figure(audit)
        build_pdf(markdown)
    print("Built final review supplement (no simulator/GPU).")


if __name__ == "__main__":
    main()
