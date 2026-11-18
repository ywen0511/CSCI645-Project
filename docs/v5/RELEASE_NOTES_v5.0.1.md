# v5.0.1 — Why EMA was inert in Study A; post hoc invalid-slip check for Study B

CPU-only update to [v5.0.0](https://github.com/ywen0511/CSCI645-Project/releases/tag/v5.0.0). It ran no simulation
and changed no frozen input and no v5.0.0 result. Checkpoints, raw records, logs and videos remain in the v5.0.0
release. Decision record: `docs/v5/DECISIONS.md` (entry 2026-11-18 17:50Z).

## What changed

**Study A: EMA α is inert by construction.** v5.0.0 reported that EMA α had exactly zero effect and did not explain
why. With the giver reference on, the controller uses the giver-kinematic bar estimate whenever the giver holds the
bar with both contacts. The 0.5 s calibration averages the unfiltered measurement, not the EMA output. The EMA output
therefore reaches the controller only while settling, when the receiver command is pinned to its start pose, and
after the giver releases.

`scripts/v5_ema_identity.py` compares the executed α 1.0 and α 0.2 runs:
- Across all 9,600 paired episodes, every record field except run identifiers and configuration hashes is identical.
- In the traced episodes, the executed receiver command never differs.

V4's fixed → calibrated comparison therefore changed two effective settings (reference and bound), not three. Study
A's conclusion is unchanged: the gain comes from calibration.

**Study B: post hoc sensitivity (not preregistered).** `scripts/v5_slip_sensitivity.py` keeps a base case only if no
episode of any primary arm ended in `invalid_slip`. 177 of 200 `slip_mixed_id` cases remain. Results (97.5% CI):

| Contrast | Difference | 97.5% CI |
|---|---:|---|
| B1 (history − feed-forward) | +0.5 pp | [−1.4, +2.3] |
| B2 (history − `geometry_best`) | +1.4 pp | [−0.8, +4.0] |

Both intervals still include zero, so the verdict is unchanged. On the exploratory `slip_mixed_ood`, history −
`geometry_best` is +6.1 pp (95% CI [+1.4, +10.7]) on the kept cases. It is reported only as a hypothesis, because the
check is post hoc, uses a secondary condition and filters on episode outcomes. The preregistered analysis remains the
result of record.

**Documents rebuilt**
- Report (13 pages).
- Slides (13 slides) and speaker notes.
- V1–V5 overview (8 pages).

The report's compute total now also counts the public-verification jobs, giving 9.49 A100 GPU-hours (cap 60). The
slides were rendered with LibreOffice on macOS, so the font differs from v5.0.0; the layout is unchanged.

**Pipeline and tests**
- `scripts/v5_regen.py` now also runs both new scripts.
- `docs/v5/REPRODUCE.md` §2a gives the standalone commands.
- Tests: 144 passed, 1 skipped (Isaac Lab not installed on the CPU machine).

## Assets

| File | Contents |
|---|---|
| `report.pdf`, `report.md` | V5 report |
| `slides.pptx`, `slides.pdf`, `speaker_notes.md` | Slides and speaker notes |
| `overview.pdf` | V1–V5 project overview |
| `ema_identity_summary.json` | EMA identity summary (`results/v5/calibration/ema_identity/summary.json`) |
| `slip_sensitivity_summary.json` | Sensitivity summary (`results/v5/slip/sensitivity/summary.json`) |
| `source-v5.0.1.tar.gz` | Source archive (`git archive` of the tag) |
| `SHA256SUMS` | Checksums |

AI assistance: all AI assistance was Anthropic Claude via Claude Code; no other AI coding assistant was used.
