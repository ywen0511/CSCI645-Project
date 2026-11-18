"""Slide content of the V5 deck (called by scripts/v5_build_slides.py). Every measured number goes through n(key)."""

import slides_v5_results  # noqa: E402  (scripts/slides_v5_results.py: Study B result slides, written after the analysis)


def build(prs, new, notes, n, title, bullets, table, pic, foot, F):
    s = new("Title")
    title(s, "Calibration and In-Grasp Slip in Bimanual Handover — V5",
          "Matched calibration ablation + physical dynamic slip · Isaac Lab 3.0 / Isaac Sim 6.2 (PhysX) · CSCI 645, Fall 2026 · Yan Wen")
    bullets(s, ["Two Franka arms with parallel-jaw grippers hand over a rigid bar; success = receiver holds it alone for 2 s",
                "Study A: which setting carried V4's calibration gain? (training-free, preregistered, 2,400 fresh cases)",
                "Study B: the bar slides in the giver's fingers after calibration — does learned memory help?",
                f"Study A verdict: calibration-only improvement {n('a.A1.decision')} ({n('a.A1')} on mixed ID)",
                f"Study B verdict: history − feed-forward {n('b.B1.decision')}; history − geometry_best {n('b.B2.decision')}",
                "Release v5.0.0: every checkpoint, raw record, video; public re-download verification"], y=1.7, size=19)
    notes(s, "Fifth study on the same handover. V4 showed that calibrating the giver's grasp reference fixes static grasp "
             "uncertainty, but changed three settings at once. V5 isolates that effect and then makes the grasp move after calibration.")

    s = new("Where V4 left off")
    title(s, "Why V5", "earlier studies, quoted from their reports")
    bullets(s, ["V1/V2: geometric coordination did most of the work; residuals ≈ constant offsets",
                "V3: known giver grasp → 100% ceiling for geometry and every learned policy",
                "V4: unknown static grasp offset → fixed transform breaks; 0.5 s calibration fixes most of it",
                "  but V4's comparison changed reference, EMA α (1.0 → 0.2) and bound (15 → 25 mm) together",
                "  and a one-shot calibration is only valid if the grasp stays put",
                "V5 = two preregistered studies: A (matched ablation), B (slip after calibration)"], size=18)
    notes(s, "Earlier-study results are not re-measured here; they motivate the two questions.")

    s = new("Study A design")
    title(s, "Study A: a 2 × 2 × 2 matched ablation", "training-free geometry; frozen before any simulation")
    bullets(s, ["Factors: reference (fixed transform / 0.5 s calibrated) × EMA α (1.0 / 0.2) × bound (15 / 25 mm)",
                "2,400 new held-out cases: V4's 12 conditions × 200, fresh split seed",
                "Anchors reproduce V4 exactly (config + controller hashes of fixed and calibrated geometry)",
                "Primary: calibrated − fixed at α 0.2, bound 25 mm, on mixed ID (A1) and +15 mm (A2)",
                "Rule: improvement supported only if the Bonferroni 97.5% lower bound > 0"], size=18)
    notes(s, "Executed from tag experiment-v5a, whose simulator code equals experiment-v4.")

    s = new("Study A result")
    title(s, "Study A: calibration alone carries the gain")
    table(s, [["primary", "condition", "calibrated − fixed", "97.5% CI", "verdict"],
              ["A1", "mixed ID", n("a.A1"), n("a.A1.ci975"), n("a.A1.decision")],
              ["A2", "+15 mm", n("a.A2"), n("a.A2.ci975"), n("a.A2.decision")]],
          0.5, 1.4, 12.3, 1.3, size=15, first_col_w=1.4)
    pic(s, F / "study_a_factorial.png", 0.5, 2.9, w=7.5)
    bullets(s, [f"EMA α: {n('a.main.mixed_id.ema')} — identical outcomes in every cell",
                f"Bound 25 vs 15 mm: {n('a.main.mixed_id.bound')} on mixed ID",
                f"Second process: {n('a.rep.ema0p2_cal050_a25')} identical outcomes"],
            x=8.3, y=3.0, w=4.8, h=3.5, size=15)
    notes(s, "Both primary lower bounds are far above zero. V4's headline is a calibration effect; filtering contributes nothing "
             "measurable and the wider bound a few points.")

    s = new("Making the grasp slide, physically")
    title(s, "Study B: a physical slip after the calibration window")
    bullets(s, ["Bar-axis force at the bar's centre of mass, PID-regulated to a minimum-jerk slide (0.25 s), then 0.1 s hold",
                "Giver keeps its full squeeze; only friction holds the bar; no pose/velocity writes in scored time",
                "Onset 0.7–1.4 s (after the 0.5 s calibration), done by 1.75 s (receiver grasps at 2.0 s)",
                "Realized slip measured per episode; > 1.5 mm off target → invalid_slip = failure for every method",
                "Feasible (development probe): slides toward the receiver of 0 to +8 mm only"],
            x=0.5, y=1.3, w=12.3, h=2.6, size=15)
    pic(s, F / "slip_mechanism.png", 2.2, 3.9, h=3.0)
    notes(s, "Relaxing the squeeze made the bar sag; slides toward the palm were never valid beyond −2.5 mm; 8–10 mm slides "
             "reached only 93.7%. The condition table was narrowed to the feasible range before the freeze, and this is logged.")

    s = new("Study B methods")
    title(s, "Study B: methods with the same information")
    table(s, [["method", "how it handles the slip"],
              ["one-shot calibrated (V4 parent)", "calibration frozen after 0.5 s → stale after the slip"],
              ["tracking geometry (new)", "giver-frame correction re-estimated by an EMA every frame"],
              ["calibrated + constant", "fixed offset tuned on development (+4 mm)"],
              ["geometry_best", "strongest training-free on development = tracking (EMA 0.05)"],
              ["learned FF / history / repeat", "PPO residual (±2 cm) on the parent; 1 frame / 4 frames / 1 frame × 4"]],
          0.5, 1.4, 12.3, 3.2, size=14, first_col_w=4.2)
    bullets(s, ["Training: V4 robust profile + slip with probability 0.5 (0 to +8 mm); 10,027,008 transitions; 5 seeds each",
                "Selection: checkpoints every 1 M transitions, V4 rule on 160 validation cases; step 0 never eligible",
                "Primary on slip_mixed_id (selected): B1 history − FF, B2 history − geometry_best; 97.5% lower bound > 0"],
            y=4.9, h=2.2, size=15)
    notes(s, "geometry_best tied with the +4 mm constant and three other controllers on development; the frozen tie-break "
             "(smallest total correction) chose tracking.")

    slides_v5_results.build(prs, new, notes, n, title, bullets, table, pic, foot, F)

    s = new("Reproduce")
    title(s, "Everything is released", "github.com/ywen0511/CSCI645-Project · release v5.0.0")
    bullets(s, ["Tags: experiment-v5a (Study A), experiment-v5b (Study B freeze and execution), v5.0.0 (delivery)",
                "Every checkpoint (formal and pilot), raw record, trace, log and video; checkpoint index with SHA-256",
                "docs/v5/REPRODUCE.md: anonymous download → verify → regenerate tables/figures → replay/reload/resume",
                f"Compute: {n('comp.total')} A100 GPU-hours (cap 60)",
                "AI assistance: all AI assistance was Anthropic Claude via Claude Code; no other AI coding assistant was used"],
            size=17)
    notes(s, "The public-download verification record is docs/v5/VERIFICATION.md.")
    return s
