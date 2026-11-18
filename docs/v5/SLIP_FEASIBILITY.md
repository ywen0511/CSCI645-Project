# Study B slip feasibility (development only)

**Outcome: feasible, with a restricted slip range.** A physical in-grasp slip can be produced reliably in this
setup for slides of the bar toward the receiver of up to 8 mm. Slides toward the giver's palm, and slides longer
than 8 mm, fail the acceptance bar. Study B uses only the accepted range. Raw records are released with v5.0.0;
the numbers below come from `results/v5/slip/probe/summary.json` and the development records.

## Mechanism

`src/csci645_handover/core/slip.py`, enabled per environment by the opt-in `slip_mechanism` config field (off by
default; with it off, every V1–V4 configuration hash is unchanged).

- During `[onset, onset + 0.25 s)` an external force along the bar axis acts at the bar's centre of mass. A PID
  regulator (kp 6000 N/m, kd 60 N s/m, ki 60000 N/(m s), cap 90 N) makes the bar's in-grasp displacement follow
  a minimum-jerk profile to the case's target. The regulator then holds the target for 0.1 s, after which the
  force is zero.
- The giver keeps its normal closed squeeze (about 17.3 N per finger). The bar is held only by finger friction.
  Only the bar-axis force component is applied, so the grip alone carries the bar's weight.
- No pose or velocity is written to the bar in the scored phase. The realized slip (the displacement change from
  onset to the end of the hold) and its error are measured from the simulator and recorded per episode.
- A slip whose realized displacement misses the target by more than 1.5 mm (x and z) ends the episode as
  `invalid_slip`. That counts as a failure for every method, like an invalid reset in V4.
- The slip starts after the 0.5 s calibration window (onset uniform in [0.7, 1.4] s) and is complete by 1.75 s,
  before the receiver's 2.0 s grasp.

## Evidence

| Check | Result |
|---|---|
| Probe round 1 (relaxed squeeze 6/12/20 N) | Bar-axis target tracked, but the bar sagged 1–10 mm vertically while sliding under the weak grip; most slips invalid |
| Probe round 2, mechanism M6 (full squeeze), start offset 0 | -2, +2, +5, +10 mm: 12/12 valid each; +15 mm 9/12; -5 mm 3/12; -7 mm 1/12 |
| Development round 1 (random start offsets, 14 controllers) | Slides toward the palm: 0/476 valid beyond -2.5 mm, 476/532 (89.5%) for -2.5..0 mm. Slides toward the receiver: 84/84 (0..2.5 mm), 406/406 (2.5..5 mm), 112/112 (5..8 mm), 354/378 (93.7%) for 8..10 mm |
| Development round 2 (final design, 14 controllers) | One invalid slip per controller in the 96 selection-stratum cases |
| Receiver contact before the 2.0 s grasp, at accepted targets | none |
| Giver drop caused by the mechanism, at accepted targets | none |
| Negative controls with slip (no receiver, giver holds, table support) | 0 successes in both probe rounds |
| No-slip case with the mechanism enabled vs disabled | identical outcomes and record fields; bitwise-identical trace positions (3,492 samples per round) |
| V4 `geometry_calibrated` config hash with the new code, slip off | `8b3a0a9d…` (unchanged) |

## Accepted range and condition changes

- Slides toward the receiver of 0 to +8 mm. The start offset plus slide stays inside V4's static feasible in-grasp
  range of [-7, +15] mm.
- Changes from the table in `V5_EXECUTION.md`, adjusted only to this range:
  - `slip_pos_10` becomes `slip_pos_8`.
  - `slip_neg_5` is dropped, because no slide toward the palm is feasible.
  - `slip_after_offset` starts at -5 mm and slides +8 mm (originally +10 mm then -10 mm).
  - The mixed conditions draw slides uniformly from [0, +8] mm.
- `slip_mixed_ood` is out of distribution only in its start offsets and sensor corruption.

Probe and development GPU use was about 0.5 GPU-hours, against the 6 GPU-hour probe cap.
