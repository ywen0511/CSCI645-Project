# V3 decisions

## Preparation: 2026-11-06 through 2026-11-07

- Extend completed v2 at `4204da23b17f920d955a0bc90f94a8df271c524f`; do not replace it.
- Retain Isaac Sim through Isaac Lab, PhysX, two Franka arms and parallel-jaw grippers.
- Main question: controlled translation-estimation uncertainty and the incremental
  value of residual learning/history above strong geometry and estimators.
- Keep orientation, contact and proprioception accurate. Explicitly include a
  giver-reference baseline because the policy already observes giver TCP position.
- Pair exogenous errors by case seed and per-episode sensor frame, independent of
  batch layout. Delay repeats the first value at startup; reset retries replay
  the same stream. Include settling frames; verify integration remotely.
- Preserve true-state reward and independent outcome evaluation. Policy/controller
  translation and derived linear velocity use the same estimated sensor path.
- Include a repeated-current 230-feature training control to isolate history
  from the extra input-layer parameters.
- Five seeds for four main families, three matched seeds for the memory control:
  23 x 10M requested transitions. Pilot cap 24M. Budgets are bounded defaults to
  validate against measured remote throughput; no GPU time has been spent here.
- Development/validation suites prepared; final generation is gated by a remote
  acceptance/freeze manifest. Draft configs are not a scientific freeze.
- Physical parameter transfer is explicitly secondary and development-gated.
- No claim of RL superiority or simulated perception realism is assumed.

Append remote decisions with the evidence split, source SHA and affected runs.
