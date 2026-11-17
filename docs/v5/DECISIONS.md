# V5 decision log

Append-only. Each entry: date, decision, reason, evidence.

## 2026-11-17 — CPU preparation (owner's machine, no GPU or simulator)

- **Scope.** The owner asked for three tiers: CPU-only fixes and analysis now; a matched
  calibration ablation (Study A) and a dynamic-slip study (Study B) on remote GPU later,
  with a complete public release. CPU work is on branch `study/v5-calibration-slip`.
- **Failure taxonomy.** The proposal promised drop/collision rates, completion time and a
  misalignment / premature-release / conflicting-motion breakdown. V1 reported them; the V4
  synthesis did not. `scripts/v5_failure_taxonomy.py` derives them from the public
  v4.0.0 `raw-final.tar.gz` (SHA-256 checked) without changing published V4 outputs.
  Flags are reported among failed valid-reset episodes because they are non-exclusive.
- **AI disclosure.** The owner confirmed all AI assistance was Anthropic Claude via Claude
  Code. The V4 overview, REVIEW.md and DEFENSE_NOTES.md had named Codex in error; corrected.
  The already published v4.0.2 overview PDF is immutable; the correction is recorded in
  REVIEW.md and will ship in v5.0.0.
- **Overview.** Added the failure section, the V3 residual-only counter-example
  (68.7% vs 70.5%), ManipTrans (cited in the proposal, V1 and V2 but dropped in V4), and
  V5 pointers. PDF links now target `main`. The overview grew from 6 to 7 pages.
- **Study A design.** 2 x 2 x 2 factorial (reference fixed/cal050 x EMA 1.0/0.2 x bound
  15/25 mm) of training-free geometry, so the V4 confound (three settings changed at once)
  is separated. Fresh suite: V4 condition definitions, split seed 6457301 (6456501 was
  already V4's evaluation-process seed), 200 cases x 12 conditions. Primary contrasts at
  matched alpha 0.2 / bound 25 mm on mixed_id and grasp_15mm, Bonferroni 97.5%, case-level
  paired bootstrap (single deterministic controller per arm, so no seed level). Frozen in
  `configs/v5/calibration/FREEZE.json` before any simulation.
- **Study B design principles** (details left to the GPU agent's feasibility probe):
  physical slip only, onset after the calibration window, a continuous re-estimating
  geometric baseline as the strong comparator, learned residuals on the V4 calibrated
  parent, V4 selection rule, freeze before final evaluation, explicit infeasibility exit.
