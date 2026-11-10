"""Slide content of the V4 deck (called by scripts/v4_build_slides.py). Every measured number goes through n(key)."""


def build(prs, new, notes, n, title, bullets, table, pic, foot, F):
    s = new("Title")
    title(s, "Uncertain Giver Grasp in Bimanual Handover — V4",
          "Where a fixed grasp transform fails, and what fixes it · Isaac Lab 3.0 / Isaac Sim 6.2 (PhysX) · CSCI 645, Fall 2026 · Yan Wen")
    bullets(s, ["Two Franka arms with parallel-jaw grippers hand over a rigid bar; success = receiver holds it alone for 2 s",
                "V4: the bar's position inside the giver's grasp is unknown (−7…+15 mm along the bar, ±15 mm vertical)",
                f"Fixed-transform reference (V3) collapses: {n('succ.geometry_fixed.baseline.grasp_15mm')}% at +15 mm",
                f"0.5 s calibration from the same noisy sensor restores it: {n('succ.geometry_calibrated.baseline.grasp_15mm')}%",
                "History / residual PPO: at most a few cases in distribution, worse outside the training support",
                f"Release v4.0.0: {n('count.logical_episodes')} logical held-out episodes, every checkpoint and raw record"], y=1.7, size=19)
    notes(s, "Fourth study on the same handover. V3 showed that a controller using the giver's grasp to locate the bar saturates the "
             "benchmark — but it assumed the grasp transform is known. V4 removes that assumption physically and measures what breaks.")

    s = new("Where V3 left off")
    title(s, "Why V4", "earlier studies, quoted from their reports")
    bullets(s, ["V1/V2: geometric coordination did most of the work; learned residuals ≈ small constant offsets",
                "V3: corrupted bar position (bias, noise, delay). Geometry + giver reference: 100% of 2,600 held-out cases",
                "  every learned policy also 100% → a ceiling; nothing could be ranked",
                "V3's key assumption: bar position = giver TCP + a known, rigid grasp transform",
                "V4 question: what if the bar sits somewhere else in the giver's fingers?",
                "  where does the fixed transform fail? do calibration, filtering, history or residual PPO help there?"], size=18)
    notes(s, "These are earlier-study results, not re-measured here. V4 keeps everything from V3 except the grasp.")

    s = new("Making the grasp uncertain, physically")
    title(s, "The unknown in-grasp offset is physical, not a sensor trick")
    bullets(s, ["Reset: bar pinned at nominal + joint displacement + in-grasp offset; giver closes at its unshifted pose",
                "Pin removed → only finger contact holds the bar; validity checked after settling; achieved offset recorded",
                "No weld, no teleport during the scored episode; the true offset is never visible to a controller",
                "Feasibility probe (development): y re-centred by the fingers → not a supported axis",
                "  toward the palm: −10 mm touches the giver hand (invalid), −7 mm valid; toward receiver: +15 mm stable",
                "Training support: x ∈ [−5, +15] mm, z ∈ [−10, +10] mm, 25% zero; evaluation adds −7 mm and ±15 mm (z)"],
            x=0.5, w=6.6, size=16)
    pic(s, F / "grasp_offsets.png", 7.2, 1.5, w=5.9)
    notes(s, "The achieved offsets track the requests within about a millimetre. The right panel shows the calibration "
             "error: about zero without sensor error, about the bias with it.")

    s = new("Controllers and information")
    title(s, "Same information for every method")
    table(s, [["controller", "how it locates the bar", "fails when"],
              ["fixed transform (V3)", "giver TCP + nominal grasp vector", "in-grasp offset (undetectable)"],
              ["calibrated (0.5 s)", "fixed transform + mean(measurement − fixed) over 10 frames", "sensor bias (inherited)"],
              ["EMA geometry (α 0.2)", "filtered measurement only", "bias, noise lag"],
              ["learned residual (PPO, ±2 cm)", "added to the calibrated parent or to nominal", "outside training support"]],
              0.5, 1.5, 12.3, 2.6, size=14, first_col_w=3.4)
    bullets(s, ["Inputs for all: corrupted translation, proprioception, measured orientation, finger contacts, phase",
                "No controller reads the true offset, clean pose, case label or a future measurement (checked: A6/A8)",
                "Calibration window lies inside the common schedule (receiver pre-grasp at 1.0 s); timings include it"],
            y=4.4, h=2.4, size=16)
    notes(s, "Calibration cannot tell a sensor bias from a grasp offset — it removes their sum's grasp part but keeps the bias.")

    s = new("Protocol")
    title(s, "Develop → accept → pilot → freeze → train → validate → test")
    bullets(s, ["Development: two registered baseline grids (≤ 36 configs) on 288 cases → calibrated parent (α 0.2, 0.5 s, 2.5 cm)",
                f"Acceptance: V3 reproduced exactly ({n('acc.A1')}), no hidden truth path, resets independent, resume works",
                f"Pilots: {n('pilot.total')} transitions (cap 24M) → V3 PPO settings kept; tag experiment-v4 frozen",
                "25 formal runs: 5 profiles × seeds 111/222/333/444/555 × 10,027,008 transitions",
                "Checkpoint selection on 240 validation cases (2/4/6/8/10M; step 0 never eligible)",
                f"Final: 12 conditions × 200 paired cases; {n('count.executed_entries')} executed entries, {n('count.executed_episodes')} episodes",
                "Primary (mixed_id, selected): history − robust FF; history − best constant geometry; 10,000-draw paired bootstrap"],
            size=17)
    notes(s, "The development support was widened once before any training, because in round 1 the strongest baselines were "
             "already at the ceiling in the primary condition. Everything is logged with times in docs/v4/DECISIONS.md.")

    s = new("The failure boundary")
    title(s, "Result 1: the fixed transform breaks beyond ~+5 mm", "held-out, 200 cases per condition")
    table(s, [["condition", "nominal", "fixed transform", "EMA", "calibrated"],
              *[[c, n(f"succ.nominal.baseline.{c}"), n(f"succ.geometry_fixed.baseline.{c}"), n(f"succ.geometry_ema.baseline.{c}"),
                 n(f"succ.geometry_calibrated.baseline.{c}")]
                for c in ("clean", "grasp_5mm", "grasp_10mm", "grasp_15mm", "bias_5mm", "mixed_id", "mixed_ood", "boundary_x_minus_7")]],
          0.5, 1.5, 7.4, 4.6, size=14, first_col_w=2.4)
    bullets(s, [f"Calibrated − fixed on grasp_15mm: {n('eff.geometry_calibrated-geometry_fixed.selected.grasp_15mm')} pp",
                "Failures are collisions with the bar end: the target lies inside the bar",
                "Vertical and palm-side offsets are tolerated by the fixed transform",
                "Sensor-only corruption does not hurt it (it ignores the sensor while the giver holds)"],
            x=8.2, y=1.5, w=4.8, size=15)
    notes(s, "Success in percent. The calibrated controller removes most of the failure at the cost of inheriting sensor bias.")

    s = new("Where methods fail")
    title(s, "Failure modes by method")
    pic(s, F / "failure_breakdown.png", 0.4, 1.3, w=12.5)
    notes(s, "Exclusive terminal reasons. Fixed transform: collisions. EMA: some release timeouts under heavy noise. "
             "Residual-only: collisions and drops.")

    s = new("Primary contrasts")
    title(s, "Result 2: learned history adds at most a few cases", "mixed_id, selected checkpoints, paired bootstrap")
    table(s, [["contrast", "difference [pp] (95% CI)", "97.5% Bonferroni"],
              ["history − robust feed-forward", n("eff.combined_robust_history-combined_robust_ff.selected.mixed_id"),
               n("eff.combined_robust_history-combined_robust_ff.selected.mixed_id.fw")],
              ["history − best constant geometry", n("eff.combined_robust_history-best_constant_geometry.selected.mixed_id"),
               n("eff.combined_robust_history-best_constant_geometry.selected.mixed_id.fw")]],
          0.5, 1.6, 12.3, 1.5, size=16, first_col_w=4.5)
    bullets(s, [f"Robust history: {n('succ.combined_robust_history.selected.mixed_id')}% on mixed_id; calibrated baseline {n('succ.geometry_calibrated.baseline.mixed_id')}%",
                "Both intervals touch zero → no improvement established; no equivalence claimed",
                "Deterministic baseline is one row, never counted as five seeds",
                f"Final (10M) checkpoints instead: history − best constant = {n('eff.combined_robust_history-best_constant_geometry.final.mixed_id')} pp"],
            y=3.5, h=3.2, size=17)
    notes(s, "The two primary contrasts were frozen before any training. Selected checkpoints come from validation only.")

    s = new("Outside the training support")
    title(s, "Result 3: learned residuals are fragile outside their support")
    pic(s, F / "severity_selected.png", 0.3, 1.25, w=8.6)
    bullets(s, [f"Palm-side −7 mm (outside [−5, +15]): history {n('succ.combined_robust_history.selected.boundary_x_minus_7')}% vs calibrated parent {n('succ.geometry_calibrated.baseline.boundary_x_minus_7')}%",
                f"  per seed {n('seeds.combined_robust_history.selected.boundary_x_minus_7')}%",
                f"Over all non-clean conditions: history − parent = {n('eff.combined_robust_history-geometry_calibrated.selected.nonclean')} pp",
                f"Residual-only on nominal: {n('succ.residual_robust_history.selected.mixed_id')}% vs nominal {n('succ.nominal.baseline.mixed_id')}% (mixed_id)"],
            x=9.0, y=1.4, w=4.1, size=14)
    notes(s, "Validation did not include the palm-side boundary, so checkpoint selection could not detect this weakness.")

    s = new("Training stability")
    title(s, "Result 4: late training instability (again)")
    pic(s, F / "learning_curves.png", 0.4, 1.3, w=8.4)
    bullets(s, [f"History final checkpoints: bias_5mm per seed {n('seeds.combined_robust_history.final.bias_5mm')}%",
                f"Residual-only collapses after ~3M transitions: final {n('succ.residual_robust_history.final.mixed_id')}% on mixed_id",
                f"Selected steps ({{step: runs}}): {n('sel.tag_counts')}",
                "Validation-based selection avoided most of the late damage"],
            x=8.9, y=1.4, w=4.2, size=14)
    notes(s, "Same pattern as V3: some history seeds degrade late. Selected and final checkpoints are reported separately.")

    s = new("Effects overview")
    title(s, "Paired effects (selected checkpoints)")
    pic(s, F / "paired_effects.png", 1.5, 1.2, h=5.9)
    notes(s, "Calibrated vs fixed is the large effect. Learned-vs-learned and learned-vs-parent effects are small or negative.")

    return s
