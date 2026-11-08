# V3 speaker notes

## Slide 1: Title

This is the third study on the same two-arm handover. v1 and v2 used accurate object state. v3 asks what happens when the object position measurement is wrong. Headline: the strong deterministic controller with a giver-grasp reference already succeeds on every held-out case, so learning has no room to help.

## Slide 2: Why v3

These v2 numbers are prior work and were not re-measured. The v3 design keeps everything from v2 except the object translation measurement, and adds a repeated-current-frame control so that any history effect can be separated from simply having more inputs.

## Slide 3: Sensor model and conditions

Bias is fixed per episode, noise is drawn per control step from a seed indexed by case and step, delay shifts the measurement back by whole control steps. mixed_id matches the training corruption; mixed_ood doubles it.

## Slide 4: Controllers

Three baseline roles turned out identical after the development search: the best constant offset was zero and the best giver-reference configuration was the shared estimator. They were evaluated once and reused under recorded aliases; aliases are not counted as independent evidence.

## Slide 5: Protocol

Everything that touches held-out data ran from the clean experiment-v3 commit. Decisions are logged with UTC times in docs/v3/DECISIONS.md.

## Slide 6: Development

The acceptance check that found the release-gate blocking is check 7. Choosing the giver-reference estimator for all combined policies was therefore a development decision, not a reaction to final results.

## Slide 7: Validation curves

Stars mark the selected checkpoints. Step 0 is the untrained control. Selection protected the study from the late collapses, which is why final checkpoints are reported separately.

## Slide 8: Main table

Read across a row for sensitivity to each corruption. The nominal script and residual-only policies fail on physical offsets, not on the sensor: their clean success is 100% and every sensor condition matches physical_only. Raw geometry fails under noise; filtered geometry under 10 mm bias.

## Slide 9: Severity curves

Delay has no effect for any controller. All combined policies and geometry_common lie on the 100% line.

## Slide 10: Primary contrasts

The bootstrap resamples seeds and base-case clusters; when every paired difference is zero there is nothing to resample, so the interval collapses. The honest reading is that this suite cannot rank these policies.

## Slide 11: Final checkpoints

The late instability is specific to real history inputs in this setup. Validation-based selection removed it; training to a fixed budget and keeping the last checkpoint would have produced a large negative result.

## Slide 12: Mechanisms

Each dot is one episode: mean commanded x residual against the true offset (top) and the injected sensor bias (bottom). Flat clouds mean the policy does not use either. The robustness comes from the estimator.

## Slide 13: Repeatability and videos

Every clip has a sidecar with case, method, seed, checkpoint hash, camera and both outcomes. The index is results/v3/videos/video_index.json.

## Slide 14: Conclusions

The result reproduces the v2 pattern under corrupted sensing: when a strong, well-informed geometric controller exists, residual PPO adds nothing measurable here.

## Slide 15: Limitations and artifacts

Everything needed to reproduce or audit the numbers is public. docs/v3/REPRODUCE.md has the commands; docs/v3/VERIFICATION.md records the fresh-download check.
