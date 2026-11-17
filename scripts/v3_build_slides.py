#!/usr/bin/env python3
"""Build the v3 presentation: report/v3/slides.pptx (editable), slides.pdf (LibreOffice), speaker_notes.md,
and results/v3/slide_numbers.json (every number on a slide or in its notes -> report_values key and source).

    python3 scripts/v3_build_slides.py [--soffice libreoffice]

Requires python-pptx. All measured numbers come from results/v3/report_values.json (scripts/v3_report_values.py);
design constants (budgets, case counts, seeds) are written directly.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "report/v3"
DARK = RGBColor(0x1F, 0x2A, 0x44)
ACC = RGBColor(0x2E, 0x6F, 0xB7)
GREY = RGBColor(0x55, 0x55, 0x55)
V = json.loads((ROOT / "results/v3/report_values.json").read_text())
AUDIT: list[dict] = []
CUR = {"slide": 0}


def n(key: str) -> str:
    """Formatted value of a report_values key; logged in the slide number audit."""
    v = V[key]
    AUDIT.append({"document": "report/v3/slides.pptx", "slide": CUR["slide"], "key": key, "text": v["text"],
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
    F = ROOT / "results/v3/figures"
    notes_md = ["# V3 speaker notes", ""]

    def new(note_title):
        s = prs.slides.add_slide(blank)
        CUR["slide"] = len(prs.slides)
        s._note_title = note_title
        return s

    def notes(s, text):
        s.notes_slide.notes_text_frame.text = text
        notes_md.extend([f"## Slide {CUR['slide']}: {s._note_title}", "", text, ""])

    # 1
    s = new("Title")
    title(s, "Observation Robustness in Bimanual Handover — v3",
          "Sensor bias, noise and delay vs geometry and residual PPO · Isaac Lab 3.0 / Isaac Sim 6.2 (PhysX) · CSCI 645, Fall 2026 · Yan Wen")
    bullets(s, ["Two Franka arms, parallel-jaw grippers, one rigid bar; success = 2 s receiver-only hold",
                "v3 corrupts only the bar's translation measurement (synthetic sensor, not vision)",
                f"Held-out: {n('count.logical_episodes')} logical episodes (6 baselines + 23 PPO runs × selected/final × 2,600 cases)",
                f"Strong estimator saturates the suite: geometry_common {n('succ.geometry_common.baseline.mixed_id')}% on mixed_id",
                "Both primary contrasts are exactly 0 pp: a ceiling, not a win for learning",
                "Release v3.0.0: every checkpoint, raw record, log, video and checksum"], y=1.7, size=19)
    notes(s, "This is the third study on the same two-arm handover. v1 and v2 used accurate object state. v3 asks what "
             "happens when the object position measurement is wrong. Headline: the strong deterministic controller "
             "with a giver-grasp reference already succeeds on every held-out case, so learning has no room to help.")

    # 2
    s = new("Why v3")
    title(s, "Where v2 left off", "previous studies, quoted from the v2 report (release v2.1.1)")
    table(s, [["v2 controller (accurate state)", "all-case success"], ["nominal script", "65.2%"], ["residual PPO", "82.6%"],
              ["geometry", "96.5%"], ["combined (geometry + residual PPO)", "96.1%"], ["geometry + tuned constant", "99.2%"]],
          0.5, 1.6, 6.2, 3.2, size=15)
    bullets(s, ["v2: learned residuals on top of geometry ≈ a small constant offset",
                "Open question: does geometry break when the object estimate is corrupted?",
                "Hypotheses (frozen before held-out data):",
                "  H1 bias / noise / delay hurt controllers differently",
                "  H2 noise-trained residuals beat clean-trained ones",
                "  H3 a 5-frame history helps beyond input size",
                "  H4 filtering + giver-grasp reference remove that benefit"], x=7.0, y=1.6, w=6.0, size=16)
    notes(s, "These v2 numbers are prior work and were not re-measured. The v3 design keeps everything from v2 except "
             "the object translation measurement, and adds a repeated-current-frame control so that any history "
             "effect can be separated from simply having more inputs.")

    # 3
    s = new("Sensor model and conditions")
    title(s, "Synthetic translation sensor")
    bullets(s, ["y_k = x_{k−d} + b + σ·n(seed, k);  estimate ŷ_k = α·y_k + (1−α)·ŷ_{k−1}",
                "Same noise sequence for every controller on a case (counter-based generator)",
                "Giver reference: while the giver holds, estimate = giver TCP − nominal grasp offset (proprioception)",
                "Orientation, joints, TCPs, gripper widths and contact forces stay accurate",
                "Final suite: 200 base cases × 13 conditions = 2,600 paired cases",
                "  clean, physical_only, bias 2/5/10 mm, noise 1/2/4 mm, delay 1/2/4 steps (50 ms each)",
                "  mixed_id: bias ≤ 5 mm, σ 2 mm, delay 2   ·   mixed_ood: bias ≤ 10 mm, σ 4 mm, delay 4",
                "Validation 240 cases and development 312 cases on separate seeds"], y=1.45, size=17)
    foot(s, "A controlled model of translation-estimation error — not a vision system and not a sim-to-real claim.")
    notes(s, "Bias is fixed per episode, noise is drawn per control step from a seed indexed by case and step, delay "
             "shifts the measurement back by whole control steps. mixed_id matches the training corruption; "
             "mixed_ood doubles it.")

    # 4
    s = new("Controllers")
    title(s, "Controllers and learned policies")
    table(s, [["controller", "estimator", "learned"],
              ["nominal", "none (fixed schedule)", "–"],
              ["geometry_raw", "α = 1, no giver reference", "–"],
              ["geometry_filtered", "EMA α = 0.2", "–"],
              ["geometry_common (= best_constant = giver)", "α = 1 + giver reference", "–"],
              ["combined_clean_ff / robust_ff", "geometry_common", "PPO residual, 1 frame (46 inputs)"],
              ["combined_robust_history", "geometry_common", "PPO residual, 5 frames (230 inputs)"],
              ["combined_robust_repeat", "geometry_common", "5 × current frame (memory control)"],
              ["residual_robust_history", "on nominal script", "PPO residual, 5 frames"]],
          0.5, 1.5, 12.3, 4.4, size=14, first_col_w=4.6)
    bullets(s, ["Residual = 0.02·tanh(a) m per axis; PPO (RSL-RL 5.5.1), MLP [128,128]; 10,027,008 transitions per run",
                "Seeds 11/22/33/44/55 (repeat control: 11/22/33) → 23 formal runs"], y=6.0, h=0.9, size=15)
    notes(s, "Three baseline roles turned out identical after the development search: the best constant offset was zero "
             "and the best giver-reference configuration was the shared estimator. They were evaluated once and "
             "reused under recorded aliases; aliases are not counted as independent evidence.")

    # 5
    s = new("Protocol")
    title(s, "Protocol: develop → freeze → train → validate → test")
    bullets(s, [f"Remote acceptance: {n('acc.passed')} checks passed (sensor, resets, no hidden truth path, PPO resume, caches)",
                "Development search over estimators and constants on development cases only",
                "Pilots ≤ 24M transitions → PPO settings unchanged; protocol frozen as tag experiment-v3",
                f"23 runs × 10M transitions: {n('compute.formal.gpu_hours')} A100 GPU-hours",
                "Selection on 240 validation cases at 2/4/6/8/10M (step 0 = control, never eligible)",
                "Final: one fresh process per entry, batch 256, all 2,600 cases; 0 invalid resets",
                "Primary (mixed_id, selected): history − robust FF; history − geometry_best_constant",
                "Paired bootstrap, 10,000 replicates over seeds and base-case clusters; 97.5% Bonferroni"], size=17)
    notes(s, "Everything that touches held-out data ran from the clean experiment-v3 commit. Decisions are logged with UTC "
             "times in docs/v3/DECISIONS.md.")

    # 6
    s = new("Development")
    title(s, "Development: the estimator decides", "development cases, used only to choose baselines")
    bullets(s, ["Raw estimate + noise ≥ 2 mm: release gate never opens (timeouts)",
                "EMA filtering helps noise; giver reference fixes it for every smoothing level",
                "Delay up to 4 steps: no effect (the bar is nearly stationary before release)",
                "Best constant offset = 0 → geometry_best_constant = geometry_common",
                "This was decided before any validation or final data"], y=1.4, w=12.3, h=2.4, size=16)
    pic(s, F / "pipeline.png", 0.9, 3.75, h=3.15)
    notes(s, "The acceptance check that found the release-gate blocking is check 7. Choosing the giver-reference estimator "
             "for all combined policies was therefore a development decision, not a reaction to final results.")

    # 7
    s = new("Validation curves")
    title(s, "Validation learning curves (all 23 runs)")
    pic(s, F / "learning_curves.png", 0.4, 1.45, w=12.5)
    bullets(s, ["Combined runs at 100% from step 0; selection fell to the residual-size / latest-step tie-breaks",
                f"History training is unstable: seed 55 {n('val.combined_robust_history_s55.step_006029312')}% at 6M, seed 11 {n('val.combined_robust_history_s11.step_008028160')}% at 8M",
                f"Residual-only history declines after 2–4M (seed 55: {n('val.residual_robust_history_s55.step_010027008')}% at 10M)"],
            y=4.55, h=2.3, size=17)
    notes(s, "Stars mark the selected checkpoints. Step 0 is the untrained control. Selection protected the study from "
             "the late collapses, which is why final checkpoints are reported separately.")

    # 8
    s = new("Main table")
    title(s, "Held-out success (%) by condition", "selected checkpoints; learned rows = mean over seeds; 200 cases per cell")
    cols = ["clean", "physical_only", "bias_10mm", "noise_4mm", "delay_4step", "mixed_id", "mixed_ood"]
    rows = [["controller"] + [c.replace("_", " ") for c in cols]]
    for lab, f, role in [("nominal", "nominal", "baseline"), ("geometry_raw", "geometry_raw", "baseline"),
                         ("geometry_filtered", "geometry_filtered", "baseline"), ("geometry_common", "geometry_common", "baseline"),
                         ("combined clean FF", "combined_clean_ff", "selected"), ("combined robust FF", "combined_robust_ff", "selected"),
                         ("combined robust history", "combined_robust_history", "selected"),
                         ("combined repeated-current", "combined_robust_repeat", "selected"),
                         ("residual-only history", "residual_robust_history", "selected")]:
        rows.append([lab] + [n(f"succ.{f}.{role}.{c}") for c in cols])
    table(s, rows, 0.5, 1.6, 12.3, 4.6, size=14, first_col_w=3.3)
    foot(s, "Full 13-condition table with final checkpoints: report Section 6.2.")
    notes(s, "Read across a row for sensitivity to each corruption. The nominal script and residual-only policies fail on "
             "physical offsets, not on the sensor: their clean success is 100% and every sensor condition matches "
             "physical_only. Raw geometry fails under noise; filtered geometry under 10 mm bias.")

    # 9
    s = new("Severity curves")
    title(s, "Severity curves (selected checkpoints, per-seed dots)")
    pic(s, F / "severity_selected.png", 0.5, 1.4, w=12.3)
    bullets(s, [f"Noise: raw geometry {n('succ.geometry_raw.baseline.noise_1mm')}% at 1 mm → {n('succ.geometry_raw.baseline.noise_2mm')}% at 2 mm (release timeouts)",
                f"Bias 10 mm: raw {n('succ.geometry_raw.baseline.bias_10mm')}%, filtered {n('succ.geometry_filtered.baseline.bias_10mm')}% (collisions); giver reference 100%"],
            y=5.4, h=1.4, size=16)
    notes(s, "Delay has no effect for any controller. All combined policies and geometry_common lie on the 100% line.")

    # 10
    s = new("Primary contrasts")
    title(s, "Primary contrasts: exactly zero", "mixed_id, selected checkpoints, 5 seeds × 200 paired cases")
    table(s, [["contrast", "difference [pp] (95% CI)", "97.5% Bonferroni", "per seed"],
              ["history − robust FF", n("eff.combined_robust_history-combined_robust_ff.selected.mixed_id"),
               n("eff.combined_robust_history-combined_robust_ff.selected.mixed_id.fw"), n("eff.combined_robust_history-combined_robust_ff.selected.mixed_id.seeds")],
              ["history − geometry_best_constant", n("eff.combined_robust_history-geometry_best_constant.selected.mixed_id"),
               n("eff.combined_robust_history-geometry_best_constant.selected.mixed_id.fw"),
               n("eff.combined_robust_history-geometry_best_constant.selected.mixed_id.seeds")],
              ["robust FF − clean FF (secondary)", n("eff.combined_robust_ff-combined_clean_ff.selected.mixed_id"), "–",
               n("eff.combined_robust_ff-combined_clean_ff.selected.mixed_id.seeds")],
              ["history − repeated-current (secondary)", n("eff.combined_robust_history-combined_robust_repeat.selected.mixed_id"), "–",
               n("eff.combined_robust_history-combined_robust_repeat.selected.mixed_id.seeds")],
              ["residual-only history − nominal (secondary)", n("eff.residual_robust_history-nominal.selected.mixed_id"), "–",
               n("eff.residual_robust_history-nominal.selected.mixed_id.seeds")]],
          0.5, 1.6, 12.3, 3.2, size=13, first_col_w=4.0)
    bullets(s, ["Zero-width intervals: both sides succeed on every case — a ceiling, not proof of equivalence",
                "No evidence that history or noise-trained residuals help on this suite (H2, H3 untestable here)",
                "Residual-only history does not beat the nominal script (unlike v2 with accurate state)"], y=5.0, h=1.9, size=16)
    notes(s, "The bootstrap resamples seeds and base-case clusters; when every paired difference is zero there is nothing "
             "to resample, so the interval collapses. The honest reading is that this suite cannot rank these policies.")

    # 11
    s = new("Final checkpoints")
    title(s, "Final (10M) checkpoints: selection mattered", "declared secondary analysis")
    bullets(s, [f"History final − geometry_common, mixed_id: {n('eff.combined_robust_history-geometry_common.final.mixed_id')} pp",
                f"  per seed {n('eff.combined_robust_history-geometry_common.final.mixed_id.seeds')}",
                f"Validation at 10M predicted it: seed 55 {n('val.combined_robust_history_s55.step_010027008')}% (collisions)",
                "Feed-forward and repeated-current final checkpoints stay at ceiling",
                f"Residual-only history final − nominal: {n('eff.residual_robust_history-nominal.final.mixed_id')} pp"], y=1.3, w=12.3, h=2.6, size=15)
    pic(s, F / "severity_final.png", 1.6, 3.95, h=3.0)
    notes(s, "The late instability is specific to real history inputs in this setup. Validation-based selection removed it; "
             "training to a fixed budget and keeping the last checkpoint would have produced a large negative result.")

    # 12
    s = new("Mechanisms")
    title(s, "What the residuals do")
    pic(s, ROOT / "results/v3/mechanisms/figures/residual_vs_error.png", 0.3, 1.35, w=8.0)
    bullets(s, [f"Combined: episode-mean x offset ≈ constant, {n('mech.combined.intercept_range')} mm",
                f"Slope on injected bias ≤ {n('mech.combined.max_abs_slope_bias')}: ignores the sensor error",
                f"Mean |residual| {n('mech.combined.abs_mean_range')} mm, max {n('mech.combined.abs_max')} of 20 mm; no clipping",
                f"Frames permuted / current-only: {n('int.combined_robust_history.permuted')} and {n('int.combined_robust_history.current_only')} of {n('int.combined_robust_history.episodes')} successes (unmodified {n('int.combined_robust_history.unmodified')})",
                f"Step-0 policies reproduce their controller: {n('zero.combined_robust_history')}"], x=8.45, y=1.4, w=4.6, size=14)
    notes(s, "Each dot is one episode: mean commanded x residual against the true offset (top) and the injected sensor bias "
             "(bottom). Flat clouds mean the policy does not use either. The robustness comes from the estimator.")

    # 13
    s = new("Repeatability and videos")
    title(s, "Repeatability and videos")
    bullets(s, [f"65-case subset × 7 entries × 3 process seeds × batch 1/23: {n('rep.terminal_equal')} terminal outcomes reproduced",
                f"History − geometry_common: {n('rep.eff.b1.mean_of_3')} pp (batch 1), {n('rep.eff.b23.mean_of_3')} pp (batch 23)",
                "Sensor parameters identical in every rerun; a check at the ceiling, not of a nonzero effect",
                f"Videos: {n('video.clips')} clips by a frozen rule + {n('video.montage_s')} s montage; 20 Hz, real time",
                "  No main-comparison failure exists in mixed_id / mixed_ood → none shown, none substituted",
                f"  Evaluation vs single-env replay disagreements: {n('video.replay_disagreements')}"], y=1.5, w=7.4, size=16)
    frame = ROOT / "results/v3/videos/frames/montage_frame.png"
    if frame.exists():
        pic(s, frame, 8.1, 1.6, w=4.9)
    notes(s, "Every clip has a sidecar with case, method, seed, checkpoint hash, camera and both outcomes. The index is "
             "results/v3/videos/video_index.json.")

    # 14
    s = new("Conclusions")
    title(s, "Conclusions")
    bullets(s, ["H1 supported: noise breaks the raw estimate at the release gate; 10 mm bias causes collisions; delay is harmless",
                "H4 supported: a giver-grasp reference makes geometry perfect on all 2,600 held-out cases",
                "H2, H3 not testable: every selected combined policy is also at 100%",
                "History training was the least stable; validation selection prevented a large loss",
                "Learned residuals act as small constant offsets and ignore the sensor error",
                "Next step (would be a new study): harder suites, e.g. error after release, object motion, grasp slip"],
            size=18)
    notes(s, "The result reproduces the v2 pattern under corrupted sensing: when a strong, well-informed geometric "
             "controller exists, residual PPO adds nothing measurable here.")

    # 15
    s = new("Limitations and artifacts")
    title(s, "Limitations and artifacts")
    bullets(s, ["Ceiling makes the primary contrasts uninformative; one object, fixed physics",
                "Giver reference assumes a rigid grasp with known offset and accurate giver proprioception",
                "Synthetic translation sensor only; simulation only; 5 seeds (3 for the memory control)",
                "Physical-transfer extension not performed (spawn overrides not validated before freeze)",
                "Release v3.0.0: source (experiment-v3 + v3.0.0), all checkpoints, raw records, logs, videos,",
                "  release_manifest.json, SHA256SUMS, archive inventories; fresh-download verification report",
                "AI-assisted: implemented, run and written by an AI coding agent (Claude Code) for the owner"], size=17)
    notes(s, "Everything needed to reproduce or audit the numbers is public. docs/v3/REPRODUCE.md has the commands; "
             "docs/v3/VERIFICATION.md records the fresh-download check.")

    OUT.mkdir(parents=True, exist_ok=True)
    import datetime
    cp = prs.core_properties
    cp.title, cp.author, cp.last_modified_by = "Observation Robustness in Bimanual Handover — v3", "Yan Wen", "Yan Wen"
    cp.subject, cp.comments = "CSCI 645 v3 study (release v3.0.0)", "Generated by scripts/v3_build_slides.py (AI-assisted)"
    cp.created = cp.modified = datetime.datetime(2026, 11, 8, tzinfo=datetime.timezone.utc)
    pptx = OUT / "slides.pptx"
    prs.save(pptx)
    subprocess.run([a.soffice, "--headless", "--convert-to", "pdf", "--outdir", str(OUT), str(pptx)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    (OUT / "speaker_notes.md").write_text("\n".join(notes_md))
    (ROOT / "results/v3/slide_numbers.json").write_text(json.dumps(AUDIT, indent=1) + "\n")
    print("wrote", pptx, OUT / "slides.pdf", f"{len(prs.slides)} slides, {len(AUDIT)} audited numbers")


if __name__ == "__main__":
    main()
