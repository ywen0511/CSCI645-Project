#!/usr/bin/env python3
"""Build the v2 presentation (editable report/v2/deck/deck.pptx) and render deck.pdf with LibreOffice.

    python3 scripts/build_deck_v2.py [--soffice libreoffice]

Requires python-pptx. Numbers are read from results/v2/summary/summary.json where possible.
"""

import argparse
import json
import subprocess
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "report/v2/deck"
DARK = RGBColor(0x1F, 0x2A, 0x44)
ACC = RGBColor(0x2E, 0x6F, 0xB7)


def add_title(slide, text, sub=None):
    tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.3), Inches(0.9))
    p = tb.text_frame.paragraphs[0]
    p.text = text
    p.font.size, p.font.bold, p.font.color.rgb = Pt(28), True, DARK
    if sub:
        p2 = tb.text_frame.add_paragraph()
        p2.text = sub
        p2.font.size, p2.font.color.rgb = Pt(14), ACC


def bullets(slide, items, x=0.5, y=1.4, w=12.3, h=5.6, size=17):
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


def table(slide, rows, x, y, w, h, size=12, bold_rows=()):
    t = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(h)).table
    for i, r in enumerate(rows):
        for j, v in enumerate(r):
            c = t.cell(i, j)
            c.text = str(v)
            for p in c.text_frame.paragraphs:
                p.font.size = Pt(size)
                p.font.bold = i == 0 or i in bold_rows
    return t


def pic(slide, path, x, y, w=None, h=None):
    kw = {}
    if w:
        kw["width"] = Inches(w)
    if h:
        kw["height"] = Inches(h)
    slide.shapes.add_picture(str(path), Inches(x), Inches(y), **kw)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--soffice", default="libreoffice")
    a = ap.parse_args()
    S = json.loads((ROOT / "results/v2/summary/summary.json").read_text())
    pe = S["per_entry"]

    def pct(e, g):
        return f"{100 * pe[e][g]['success_rate_valid']:.1f}"

    def lm(m, role, g):
        v = [pe[f"{m}_seed{s}__{role}"][g]["success_rate_valid"] for s in (11, 22, 33)]
        return f"{100 * sum(v) / 3:.1f}"

    comp = {(c["comparison"], c["role"], c["cases"]): c for c in S["comparisons"] if c["metric"] == "success"}

    def cmp(name, g="all", role="selected"):
        c = comp[(name, role, g)]
        return f"{100 * c['diff']:+.1f} [{100 * c['ci_low']:+.1f}, {100 * c['ci_high']:+.1f}]"

    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    F = ROOT / "results/v2"

    s = prs.slides.add_slide(blank)
    add_title(s, "Robust Bimanual Handover — v2 Follow-up Study",
              "Geometric coordination vs residual RL · Isaac Lab 3.0 / Isaac Sim 6.2 (PhysX) · CSCI 645, Fall 2026 · Yan Wen")
    bullets(s, ["Two Franka Panda arms, parallel-jaw grippers, one rigid bar; success = 2 s receiver-only hold",
                "v1: geometry module decisive, but the selector picked untrained policies (8/9 runs)",
                "v2: audit v1 → diagnose residuals → ablate geometry → preregistered harder experiment",
                "Answer: strong geometry suffices; learned residuals on top add nothing and lose to a tuned constant"],
            y=1.8, size=20)
    pic(s, OUT / "frames/geometry_success.png", 7.6, 4.3, w=5.2)

    s = prs.slides.add_slide(blank)
    add_title(s, "Task and methods")
    table(s, [["method", "receiver target", "release"],
              ["nominal", "fixed approach–grasp schedule", "scheduled"],
              ["geometry", "+ alignment (A) + shared-holding anchor (H)", "contact-gated (G)"],
              ["residual", "+ learned 3-D residual, 2 cm bound (PPO)", "scheduled"],
              ["combined", "geometry on top of nominal + residual", "contact-gated"],
              ["combined_no_phase", "combined without 4 contact-phase inputs", "contact-gated"],
              ["constant controls", "residual replaced by a fixed offset", "as base"]], 0.5, 1.5, 7.6, 3.6, size=13)
    bullets(s, ["Perturbations: bar start position (per axis) and release time",
                "20 Hz control through differential IK, fixed orientations",
                "PPO (RSL-RL 5.5.1), 1,024 envs, 10M transitions per run",
                "Same evaluator and case realizations for every controller"], x=8.4, y=1.5, w=4.6, size=15)

    s = prs.slides.add_slide(blank)
    add_title(s, "Stage 1 — Audit of v1", "reproducible; two labelling/logging errors, one interpretation gap")
    bullets(s, ["Fresh download: 21/21 checksums, 556 archive members re-hashed; tables regenerate byte for byte",
                "19,800 + 16,200 records, identical case IDs, 0 duplicates / invalid resets / errors",
                "E1: aggregate labels '1,400 in-range / 400 stress' → 1,200 non-stress / 600 stress (numbers unchanged)",
                "E2: recorded episode_return omits the terminal-step reward (records written before rewards) — logging only",
                "E3: 'untrained' step-0 policies output a seed-specific constant (+1.4 / +1.0 / −2.5 mm), not zero",
                "Replay of 23 predeclared cases × 20 policies in new processes: 456/460 and 457/460 outcomes agree",
                "  all disagreements are failure-boundary cases; GPU physics is not bitwise reproducible across batch layouts",
                "Negative controls physical: table support → receiver grips 17 N, giver open, table 1.3–1.6 N → 0/20 success"],
            size=16)

    s = prs.slides.add_slide(blank)
    add_title(s, "Stage 2 — What do the learned residuals do?", "450 development cases, archived v1 checkpoints")
    pic(s, F / "diagnostics/figures/constant_offset_sensitivity.png", 0.4, 1.4, w=6.4)
    pic(s, F / "diagnostics/figures/signed_residual_vs_offset.png", 0.4, 4.2, w=6.4)
    bullets(s, ["Geometry + constant +3 mm: 450/450 (geometry + 0: 443)",
                "Trained combined: near-constant −1…−2.5 mm x bias (spread ≤ 0.4 mm), the harmful direction",
                "  −7.8 pp vs the constant on stress cases [−13.1, −3.3]",
                "Failures = palm hits bar end when the object is shifted +15…+19 mm toward the receiver",
                "Residual-only policies are state dependent (slope 0.07–0.16) but ≈ best constant (+4.4 [−2.0, +11.3])"],
            x=7.0, y=1.5, w=6.0, size=15)

    s = prs.slides.add_slide(blank)
    add_title(s, "Stage 3 — Which geometry component matters?", "held-out v2 suite, residual = 0")
    pic(s, F / "summary/figures/ablation_1cm.png", 0.4, 1.4, w=6.6)
    pic(s, F / "summary/figures/alignment_bound.png", 7.3, 1.4, w=5.0)
    ab = S["ablation"]
    bullets(s, [f"Alignment A: +{100 * ab['1cm']['all']['effect_A']['estimate']:.1f} pp (1 cm), +{100 * ab['1p5cm']['all']['effect_A']['estimate']:.1f} pp (1.5 cm)",
                f"Release gate G: +{100 * ab['1cm']['all']['effect_G']['estimate']:.1f} / +{100 * ab['1p5cm']['all']['effect_G']['estimate']:.1f} pp; up to +25.5 pp beyond the alignment bound",
                "Shared-holding anchor H: no measurable effect (±0.1 pp)",
                "Bound 0.5 / 1 / 1.5 / 2 cm → 84.0 / 91.9 / 96.5 / 98.3 % (all cases)"], y=4.9, size=15)

    s = prs.slides.add_slide(blank)
    add_title(s, "Stage 4 — Preregistered v2 protocol", "frozen at tag experiment-v2 (protocol sha256 bd79ae51…)")
    bullets(s, ["Training range widened to ±2 cm / ±0.30 s (curriculum); 1.5 cm geometry in combined methods",
                "Zero-mean actor initialization (pilot P2 chosen by a predeclared rule; 14.75M of 15M pilot budget)",
                "Selection excludes step 0; ties → fewer collisions → smaller residual → latest",
                "Constants tuned on 750 development cases: nominal +9 mm, geometry 1 cm +7 mm, geometry 1.5 cm +10 mm",
                "Final suite: 12 conditions × 200 fresh cases incl. ±3 cm extrapolation (feasibility-checked)",
                "Disclosed: the training range is already solved by 1.5 cm geometry; validation near-saturated",
                "9 runs × 10,027,008 transitions; 117,600 evaluation episodes, all reconciled (0 invalid, 0 errors)"],
            size=17)

    s = prs.slides.add_slide(blank)
    add_title(s, "Stage 5 — Held-out results", "success %, 2,400 fresh cases; learned = mean of 3 seeds (selected checkpoints)")
    rows = [["controller", "inner", "outer ±2 cm", "extrap. ±3 cm", "all"]]
    for lab, e in (("nominal", "nominal"), ("nominal + 9 mm", "const_nominal"), ("geometry 1.5 cm", "geometry_1p5cm"),
                   ("geometry 1.5 cm + 10 mm", "const_geometry_1p5cm")):
        rows.append([lab] + [pct(e, g) for g in ("inner", "outer", "extrapolation", "all")])
    for lab, m in (("residual (PPO)", "residual"), ("combined (PPO)", "combined"), ("combined_no_phase", "combined_no_phase")):
        rows.append([lab] + [lm(m, "selected", g) for g in ("inner", "outer", "extrapolation", "all")])
    table(s, rows, 0.5, 1.5, 6.6, 3.8, size=13, bold_rows=(4,))
    pic(s, F / "summary/figures/success_by_condition.png", 7.3, 1.5, w=5.8)
    bullets(s, ["Everything with 1.5 cm geometry is 100 % inside the training range",
                "Differences appear only in extrapolation"], x=7.3, y=4.3, w=5.8, size=15)

    s = prs.slides.add_slide(blank)
    add_title(s, "Primary comparisons", "paired seed × case bootstrap, pp [95% CI], all 2,400 cases")
    table(s, [["comparison", "selected", "final checkpoints"],
              ["combined − geometry 1.5 cm", cmp("combined - geometry_1p5cm"), cmp("combined - geometry_1p5cm", role="final")],
              ["combined − (geometry + 10 mm)", cmp("combined - const_geometry_1p5cm"), cmp("combined - const_geometry_1p5cm", role="final")],
              ["residual − nominal", cmp("residual - nominal"), cmp("residual - nominal", role="final")],
              ["residual − (nominal + 9 mm)", cmp("residual - const_nominal"), cmp("residual - const_nominal", role="final")],
              ["combined − combined_no_phase", cmp("combined - combined_no_phase"), cmp("combined - combined_no_phase", role="final")]],
          0.5, 1.5, 8.5, 3.0, size=14)
    bullets(s, [f"Extrapolation: combined − geometry {cmp('combined - geometry_1p5cm', 'extrapolation')}; − (geometry + const) {cmp('combined - const_geometry_1p5cm', 'extrapolation')}",
                "Trained combined is 0.4 pp below its own untrained (= geometry) version",
                "Residual RL without geometry learns a state-dependent correction a constant cannot match (+13 pp)",
                "Explicit contact-phase input: no effect"], y=4.8, size=16)

    s = prs.slides.add_slide(blank)
    add_title(s, "Why combined does not help", "same mechanism in v1 and v2")
    pic(s, F / "diagnostics/figures/failtrace_combined_bias_v2dev-joint_early_stress-0017.png", 0.3, 1.3, w=7.2)
    bullets(s, ["Learned combined residual ≈ constant −1…−2.4 mm in x (spread ≤ 0.6 mm, slope ≈ 0)",
                "92–100 % of combined failures: object shifted > 2 cm toward the receiver (beyond the 1.5 cm bound)",
                "Those cases need a positive offset; the +10 mm constant solves 97 % of extrapolation cases",
                "Inside the training range geometry already succeeds → no learning signal for the useful direction",
                "Residual-only policies see failures in training and learn ~10–13 % offset tracking"],
            x=7.7, y=1.4, w=5.4, size=15)

    s = prs.slides.add_slide(blank)
    add_title(s, "Demo (10 provenance-linked videos in the release)", "every single-env replay matched its evaluation record")
    for i, (f, cap) in enumerate((("nominal_timeout", "nominal: timeout (joint −0.30 s, ±2 cm)"),
                                  ("geometry_success", "geometry 1.5 cm: success (same case)"),
                                  ("combined_failure", "combined: palm collision at ±3 cm"))):
        pic(s, OUT / f"frames/{f}.png", 0.3 + 4.35 * i, 1.6, w=4.2)
        tb = s.shapes.add_textbox(Inches(0.3 + 4.35 * i), Inches(4.1), Inches(4.2), Inches(0.5))
        tb.text_frame.text = cap
        tb.text_frame.paragraphs[0].font.size = Pt(13)
    bullets(s, ["Matched comparison, release-gate rescue, alignment-bound example, trained success/failure, residual policy",
                "Selected by a rule frozen before final outcomes (videos.json lists rule, hashes, replay outcome)"], y=4.9, size=15)

    s = prs.slides.add_slide(blank)
    add_title(s, "Conclusions and limitations")
    bullets(s, ["Strong geometry is sufficient for this handover; alignment does most of the work, gating the rest",
                "Residual RL on top of geometry adds no robust value and loses to a development-tuned constant offset",
                "Residual RL alone helps a lot over nominal (+17 pp) but stays far below geometry",
                "Limitations: simulation only, privileged state, translation-only perturbations, 3 seeds,",
                "  v2 designed after v1 diagnostics, saturated training range / validation, one reward design",
                "Everything public: tags experiment-v2 + release v2.0.0 (records, checkpoints, logs, videos, report)"],
            y=1.5, size=19)

    OUT.mkdir(parents=True, exist_ok=True)
    pptx = OUT / "deck.pptx"
    prs.save(pptx)
    subprocess.run([a.soffice, "--headless", "--convert-to", "pdf", "--outdir", str(OUT), str(pptx)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("wrote", pptx, OUT / "deck.pdf")


if __name__ == "__main__":
    main()
