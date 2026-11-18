# V5 speaker notes

## Slide 1: Title

Fifth study on the same handover. V4 showed that calibrating the giver's grasp reference fixes static grasp uncertainty, but changed three settings at once. V5 isolates that effect and then makes the grasp move after calibration.

## Slide 2: Where V4 left off

Earlier-study results are not re-measured here; they motivate the two questions.

## Slide 3: Study A design

Executed from tag experiment-v5a, whose simulator code equals experiment-v4.

## Slide 4: Study A result

Both primary lower bounds are far above zero. V4's headline is a calibration effect; filtering contributes nothing measurable and the wider bound a few points.

## Slide 5: Making the grasp slide, physically

Relaxing the squeeze made the bar sag; slides toward the palm were never valid beyond −2.5 mm; 8–10 mm slides reached only 93.7%. The condition table was narrowed to the feasible range before the freeze, and this is logged.

## Slide 6: Study B methods

geometry_best tied with the +4 mm constant and three other controllers on development; the frozen tie-break (smallest total correction) chose tracking.

## Slide 7: Study B primary

Both 97.5% intervals include zero, so under the frozen rule neither superiority claim holds. No equivalence is claimed.

## Slide 8: Study B all conditions

The stale calibration costs a few points; tracking, a constant and learned residuals recover them about equally.

## Slide 9: Training stability

Three of five history seeds degraded late; two collapsed completely. Selected and final checkpoints are reported separately in the report.

## Slide 10: Mechanisms

Same picture as V2–V4: the learned residual acts mostly like an offset, not like a temporal estimator.

## Slide 11: Failures and robustness

All taxonomy, repeatability and regression tables are in the report and in results/v5/slip/analysis/summary.json.

## Slide 12: Answer

Per the interpretation rule in V5_EXECUTION.md: tracking matches learning, so continuous geometric estimation, not learning, handles slip in this model.

## Slide 13: Reproduce

The public-download verification record is docs/v5/VERIFICATION.md.

