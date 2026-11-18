# V5 Study B - post hoc sensitivity: excluding invalid slips

Not preregistered. A base case is kept only if no episode of any primary arm (history and feed-forward selected checkpoints, five seeds each, and `geometry_best`) ended in `invalid_slip`. Same bootstrap as the preregistered analysis. The filter conditions on an episode outcome, so kept cases are not a random subset.

| Condition | Contrast | All cases: diff (97.5% CI) | Kept cases | Valid-slip cases: diff (95% CI) | (97.5% CI) |
|---|---|---|---:|---|---|
| slip_mixed_id (primary) | B1: slip_robust_history - slip_robust_ff | -1.0 [-3.4, +1.3] | 177/200 | +0.5 [-1.0, +2.0] | [-1.4, +2.3] |
| slip_mixed_id (primary) | B2: slip_robust_history - geometry_best | +0.9 [-2.6, +4.6] | 177/200 | +1.4 [-0.5, +3.6] | [-0.8, +4.0] |
| slip_mixed_ood (exploratory) | B1: slip_robust_history - slip_robust_ff | +0.7 [-4.5, +5.6] | 181/200 | +1.4 [-2.4, +5.1] | [-3.1, +5.5] |
| slip_mixed_ood (exploratory) | B2: slip_robust_history - geometry_best | +3.9 [-1.5, +9.4] | 181/200 | +6.1 [+1.4, +10.7] | [+0.8, +11.4] |

| Condition | Arm | Invalid-slip episodes | Success, all cases (%) | Success, kept cases (%) |
|---|---|---:|---:|---:|
| slip_mixed_id | slip_robust_history | 68 of 1000 | 92.9 | 99.7 |
| slip_mixed_id | slip_robust_ff | 54 of 1000 | 93.9 | 99.2 |
| slip_mixed_id | geometry_best | 13 of 200 | 92.0 | 98.3 |
| slip_mixed_ood | slip_robust_history | 56 of 1000 | 91.4 | 96.7 |
| slip_mixed_ood | slip_robust_ff | 48 of 1000 | 90.7 | 95.2 |
| slip_mixed_ood | geometry_best | 8 of 200 | 87.5 | 90.6 |
