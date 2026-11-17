# V4 speaker notes

## Slide 1: Title

Fourth study on the same handover. V3 showed that a controller using the giver's grasp to locate the bar saturates the benchmark — but it assumed the grasp transform is known. V4 removes that assumption physically and measures what breaks.

## Slide 2: Where V3 left off

These are earlier-study results, not re-measured here. V4 keeps everything from V3 except the grasp.

## Slide 3: Making the grasp uncertain, physically

The achieved offsets track the requests within about a millimetre. The right panel shows the calibration error: about zero without sensor error, about the bias with it.

## Slide 4: Controllers and information

Calibration cannot tell a sensor bias from a grasp offset — it removes their sum's grasp part but keeps the bias.

## Slide 5: Protocol

The development support was widened once before any training, because in round 1 the strongest baselines were already at the ceiling in the primary condition. Everything is logged with times in docs/v4/DECISIONS.md.

## Slide 6: The failure boundary

Success in percent. The calibrated controller removes most of the failure at the cost of inheriting sensor bias.

## Slide 7: Where methods fail

Exclusive terminal reasons. Fixed transform: collisions. EMA: some release timeouts under heavy noise. Residual-only: collisions and drops.

## Slide 8: Primary contrasts

The two primary contrasts were frozen before any training. Selected checkpoints come from validation only.

## Slide 9: Outside the training support

Validation did not include the palm-side boundary, so checkpoint selection could not detect this weakness.

## Slide 10: Training stability

Same pattern as V3: some history seeds degrade late. Selected and final checkpoints are reported separately.

## Slide 11: Effects overview

Calibrated vs fixed is the large effect. Learned-vs-learned and learned-vs-parent effects are small or negative.

## Slide 12: Mechanisms

Successes out of 60. This is the same picture as V2 and V3: learned residuals mostly encode a fixed offset.

## Slide 13: Repeatability, traces and videos

The trace shows the mechanism of the boundary directly. Videos are in the release with a montage.

## Slide 14: Answer

A measured failure boundary plus a strong geometric remedy; no positive RL result, consistent with V1–V3.

## Slide 15: Limitations

All limitations are also in the report, Section 10.

## Slide 16: Reproduce

The public-download verification record is docs/v4/VERIFICATION.md on the branch.

