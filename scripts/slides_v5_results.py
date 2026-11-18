"""Study B result slides of the V5 deck (called from scripts/slides_v5_content.py). Numbers only through n(key)."""


def build(prs, new, notes, n, title, bullets, table, pic, foot, F):
    s = new("Study B primary")
    title(s, "Study B primary: memory does not beat the comparators", "slip_mixed_id, selected checkpoints, paired seed × case bootstrap")
    table(s, [["contrast", "difference", "95% CI", "97.5% CI", "superiority"],
              ["B1 history − feed-forward", n("b.B1"), n("b.B1.ci95"), n("b.B1.ci975"), n("b.B1.decision")],
              ["B2 history − geometry_best", n("b.B2"), n("b.B2.ci95"), n("b.B2.ci975"), n("b.B2.decision")]],
          0.5, 1.5, 12.3, 1.4, size=15, first_col_w=3.6)
    pic(s, F / "study_b_contrasts.png", 2.4, 3.1, h=3.9)
    notes(s, "Both 97.5% intervals include zero, so under the frozen rule neither superiority claim holds. No equivalence is claimed. "
             "Post hoc check (v5.0.1, not preregistered): dropping every case with an invalid slip in a primary arm "
             f"({n('b.sens.slip_mixed_id.kept')} kept) gives B1 {n('b.sens.slip_mixed_id.B1')} {n('b.sens.slip_mixed_id.B1.ci975')} "
             f"and B2 {n('b.sens.slip_mixed_id.B2')} {n('b.sens.slip_mixed_id.B2.ci975')}: the same verdict.")

    s = new("Study B all conditions")
    title(s, "Study B: success by condition", "learned: 5 seeds pooled (selected); training-free: one controller")
    rows = [["method", "static mixed", "slip +5", "slip +8", "after offset", "slip mixed ID", "slip mixed OOD"]]
    for m, k, lab in (("nominal", "baseline", "nominal"), ("geometry_fixed", "baseline", "fixed transform"),
                      ("geometry_calibrated", "baseline", "one-shot calibrated"), ("geometry_tracking", "baseline", "tracking (= best)"),
                      ("best_constant_geometry", "baseline", "calibrated + 4 mm"), ("slip_robust_ff", "selected", "learned FF"),
                      ("slip_robust_history", "selected", "learned history"), ("slip_robust_repeat", "selected", "learned repeat")):
        rows.append([lab] + [n(f"b.succ.{m}.{k}.{c}") for c in ("static_mixed_id", "slip_pos_5", "slip_pos_8", "slip_after_offset",
                                                              "slip_mixed_id", "slip_mixed_ood")])
    table(s, rows, 0.5, 1.4, 12.3, 4.2, size=14, first_col_w=3.0)
    bullets(s, [f"Tracking − one-shot: {n('b.c.tracking_minus_calibrated.slip_mixed_ood')} on mixed OOD; FF − parent: {n('b.c.ff_minus_calibrated_parent.slip_mixed_id')} on mixed ID (exploratory)",
                "~6% of held-out slips are invalid (> 1.5 mm off target) → failure for every method; ceiling ≈ 94%"],
            y=5.8, h=1.4, size=14)
    notes(s, "The stale calibration costs a few points; tracking, a constant and learned residuals recover them about equally.")

    s = new("Training stability")
    title(s, "Late training instability, again", "history final checkpoints")
    pic(s, F / "learning_curves.png", 0.6, 1.2, w=7.6)
    bullets(s, [f"History final, per seed, clean: {n('b.seeds.slip_robust_history.final.clean')}%",
                f"  slip mixed ID: {n('b.seeds.slip_robust_history.final.slip_mixed_id')}%",
                f"Selected: {n('b.seeds.slip_robust_history.selected.slip_mixed_id')}%",
                "Feed-forward and repeat final ≈ selected",
                "Validation-based selection avoided the collapse (as in V3/V4)"],
            x=8.4, y=1.4, w=4.6, h=5.5, size=15)
    notes(s, "Three of five history seeds degraded late; two collapsed completely. Selected and final checkpoints are reported separately in the report.")

    s = new("Mechanisms")
    title(s, "What do the history policies use?", "60-case subset of slip_mixed_id; successes / 60")
    rows = [["run", "policy", "reversed", "current only", "dev constant"]]
    for k in (111, 222, 333, 444, 555):
        r = f"slip_robust_history_s{k}"
        rows.append([f"history s{k}"] + [n(f"b.mech.{r}.{x}") for x in ("selected", "reversed", "current_only", "constant")])
    table(s, rows, 0.5, 1.5, 7.8, 3.4, size=14, first_col_w=1.9)
    bullets(s, [f"Zero-residual parent: {n('b.mech.parent')}",
                "Reversing or removing the frame order changes no outcome",
                "A constant fitted on development records does exactly as well",
                "All 8 failures per row are the same invalid slips"],
            x=8.6, y=1.5, w=4.4, size=15)
    notes(s, "Same picture as V2–V4: the learned residual acts mostly like an offset, not like a temporal estimator.")

    s = new("Failures and robustness")
    title(s, "Failures, repeatability, regression, videos")
    bullets(s, ["Nominal / fixed transform: collisions with the bar end (as in V4)",
                "Calibrated, tracking, constant, learned: remaining failures are almost all invalid slips",
                f"Repeatability (second process): parent {n('b.rep.geometry_calibrated')}, history s111 {n('b.rep.slip_robust_history_s111__selected')}",
                "Regression on the V4 final suite (no slip): see report Section 8",
                "Videos by a rule frozen before final evaluation: Study A pair, one-shot vs tracking vs history, a failure, a no-slip control"],
            size=17)
    notes(s, "All taxonomy, repeatability and regression tables are in the report and in results/v5/slip/analysis/summary.json.")

    s = new("Answer")
    title(s, "Answers to the V5 questions")
    bullets(s, [f"A: V4's gain is calibration (A1 {n('a.A1')}, A2 {n('a.A2')}); EMA is inert here; bound a few points",
                "B: a physical slip is feasible only for slides toward the receiver ≤ 8 mm in this setup",
                f"B1/B2: history beats neither feed-forward nor tracking geometry ({n('b.B1')}, {n('b.B2')})",
                "Continuous tracking or a constant offset recovers what the stale calibration loses",
                "Still no held-out evidence in this project that memory helps",
                "Limits: one slip model, simulation only, near-ceiling baselines, ~6% invalid slips"], size=18)
    notes(s, "Per the interpretation rule in V5_EXECUTION.md: tracking matches learning, so continuous geometric estimation, "
             "not learning, handles slip in this model.")
