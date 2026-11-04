# v2 decision log

UTC timestamps. Evidence paths are relative to the repository unless marked as cluster paths.
The v1 log ([docs/DECISIONS.md](../DECISIONS.md)) is historical and unchanged.

### 2026-11-04 05:40 UTC — Start of the follow-up

- Work branch `study/v2-diagnostics` created from `impl/handover` @ `a3bb983` (the follow-up README).
  No earlier follow-up work existed on the remote (only `main`, `impl/handover`; tags `experiment-v1`, `v1.0.0`).
- `STATUS.json` restructured: `v1_completed: true` plus a separate `followup` block.
- Compute: `dgx047` (8x A100-40GB, LSF `gpu_large_shared`) was idle at start; v1 also ran there. All GPU
  work uses self-terminating 1-GPU jobs; no reservation is held between jobs.
- Environment: reuse the v1 isolated conda environment (Isaac Lab v3.0.0, Isaac Sim 6.2.0.0, RSL-RL 5.5.1);
  no upgrades, so archived v1 checkpoints and the v1 physics configuration stay valid.

### 2026-11-04 06:05 UTC — Stage 0 results

- Smoke and negative controls with the v2 source (v1-equivalent defaults), 20 clean cases each
  (`results/v2/stage0/`): nominal 20/20 success, geometry 20/20; `no_receiver` 20/20 drop; `giver_holds`
  20/20 episode timeout (nominal and geometry); `table_support` (6 cm table under the bar) 0/20 success,
  20/20 episode timeout. Same outcomes as v1 Gate 1.
- v1.0.0 re-downloaded anonymously (`scripts/download_release.py`): 22 assets; `sha256sum -c` 21/21 OK;
  `scripts/verify_archives.py` 13 archives, 556 members, 0 mismatches; `verify_release.py` OK.

### 2026-11-04 06:12 UTC — Stage 2/3 development results (450 v2 development cases)

Evidence: `results/v2/diagnostics/tables.md`, `summary.json`; raw records in the v2 release.

- Geometry + constant x offset: +2 to +5 mm all reach 450/450; rule picks **+3 mm** (fewest collision
  episodes, then smaller |x|). Nominal + constant: rule picks **+4 mm** (377/450 vs 360/450 at 0).
- Archived v1 combined **final** policies: 97.4% vs geometry+zero 98.4% (-1.0 [-2.4, -0.1]) and vs
  geometry+3 mm 100% (-2.6 [-4.4, -1.1]; stress -7.8 [-13.1, -3.3]). Their residual is almost a constant
  bias (episode-mean signed x -1.0 to -2.5 mm; across-case std 0.1-0.4 mm; slope vs object x offset ~0):
  **the trained combined behaviour is explained by a constant bias**, in the direction that the constant
  search shows to be harmful.
- Archived v1 combined **step-0** policies are not a zero residual: their deterministic mean is a
  seed-specific constant (x = +1.4, +1.0, -2.5 mm; across-case std <= 0.04 mm). Their success follows the
  constant-offset curve (s22 100%, s33 96.4%). This motivates testing a zero-mean actor initialization.
- Archived v1 residual final policies are state-dependent (slope of residual x vs object x offset
  0.07-0.16, correlation 0.47-0.74): +7.8 pp stress vs nominal [+2.4, +14.2], but +4.4 [-2.0, +11.3] vs
  nominal + 4 mm, with more collision episodes (+9.3 pp on stress).
- Geometry ablation (1 cm bound): A (alignment) is the main component (+29.7 pp on stress), G (release
  gate) +17.0, H (anchor) +0.3; A x G interaction -4.0 (partly redundant). Reproduction: `geom_none` =
  nominal on 450/450 cases; `geom_bound_0p010` = geometry_zero on 450/450; `geom_AHG` vs geometry_zero
  differ in 1/450 terminal reasons in the same process (run-to-run GPU nondeterminism; same config hash).
- Alignment bound: 0.5 cm 94.0%, 1.0 cm 98.4%, 1.5 cm 100%, 2.0 cm 100% (stress 82.0 / 95.3 / 100 / 100).

### 2026-11-04 06:14 UTC — Feasibility (300 development feasibility cases, `development_feasibility.jsonl`)

- Criteria (written down after this run, so not preregistered; chosen as simple solvability checks): an
  extrapolation condition is feasible if >= 95% resets are valid and at least one deterministic controller
  succeeds on >= 50%. The decision is not sensitive to the thresholds (no condition is near them). Results: all 300 resets valid; geometry 2 cm
  bound: position_x3 100%, joint_early_x3 90%, joint_late_x3 92% -> **the three +-3 cm extrapolation
  conditions are included** in the v2 final suite.
- Candidate training distribution +-2 cm / +-0.30 s (`train_dist_2cm`, 100 cases): all resets valid;
  geometry 1 cm 89%, **1.5 cm 100%**, 2 cm 100%, nominal 69%. +-2 cm is the largest offered range and is
  feasible, so it is used. It is saturated by the default stronger comparator (1.5 cm geometry); this is
  disclosed rather than changed (the assignment forbids weakening geometry).
- Consequence for the constant search: on the 450-case suite every x in [-2, +5] mm ties at 450/450 for
  1.5 cm geometry, so the rule degenerates to x = 0. The v2 constants are therefore re-selected on the
  union of the development suite and the development feasibility suite (750 development cases) for all three
  bases (nominal, geometry 1 cm, geometry 1.5 cm); the 450-case selections above stay recorded as Stage 2
  diagnostics.

### 2026-11-04 06:17 UTC — Pilot plan (written before any pilot result)

- Two pilot configurations, identical except the actor initialization (Stage 2 evidence: the default
  random initialization gives a seed-specific constant residual of 1-2.5 mm that changes success):
  `configs/v2/pilot/P1_default_init.json` (v1 initialization) and `P2_zero_mean_init.json` (actor output
  layer zeroed, so the deterministic residual is exactly 0 at step 0; exploration std 0.5 unchanged).
  Both: curriculum 0 -> (1 cm, 0.15 s) at 10% -> (1.5 cm, 0.225 s) at 30% -> (2 cm, 0.30 s) from 50% of the
  budget; geometry 1.5 cm bound; v1 rewards and PPO settings. No reward-weight change is piloted.
- Runs (seeds 101/102, budget cap 15M including smoke): smoke combined P2 s102 (196,608 transitions, with a
  resume), combined P1 s101 5M, combined P2 s101 5M, residual P2 s101 4.5M (all rounded up to whole
  32,768-transition rollouts; total ~14.88M).
- Decision rule: evaluate every pilot checkpoint on the 1,150 development cases (development,
  development_valproxy, development_feasibility). Use P2 for the final runs unless the mean success of P2's
  checkpoints at >= 2M transitions is more than 1.0 pp below P1's on those cases; otherwise P1.
  Tie or near-tie favours P2 because it makes the step-0 control identical to geometry + zero.

### 2026-11-04 06:29 UTC — v2 constant search on 750 development cases; expanded grid

- On the union of `development` (450) and `development_feasibility` (300) the frozen grid selects
  x = +5 mm for all three bases (nominal 516/750, geometry 1 cm 722/750, geometry 1.5 cm 741/750), i.e. the
  edge of the grid (`results/v2/diagnostics/constants_v2_750.json`). Because an edge optimum suggests the
  grid is too narrow for a *tuned* constant, a separate expanded grid x = +6..+10 mm (1 mm steps, y = z = 0)
  is evaluated on the same 750 development cases (evaluation only, no training budget). The final constants
  are selected by the same rule over the union of both grids (-5..+10 mm). Validation and final cases are
  not used.
- Validation proxy (development-seed copy of the planned validation strata, 400 cases): geometry 1.5 cm is
  100% on clean, in-range, full-training-range and edge strata and 94% on the harder +-2.5 cm stratum
  (394/400 overall); geometry 1 cm 92.0% overall; nominal 61.8%. The planned validation set is therefore
  near-saturated for the stronger comparator; the harder stratum is the only one that separates
  controllers. Kept as planned and disclosed.

### 2026-11-04 06:36 UTC — v2 constants selected (750 development cases, grid -5..+10 mm)

- Evidence: `results/v2/diagnostics/constants_v2.json` (`scripts/v2_select_constants.py`).
- Selected: **nominal +9 mm** (528/750), **geometry 1 cm +7 mm** (724/750), **geometry 1.5 cm +10 mm**
  (746/750, 0 collision episodes). The 1.5 cm selection is again at the edge of the (extended) grid, but the
  curve is flat there (+8 / +9 / +10 mm: 745 / 745 / 746 of 750). Stopping rule (decided after seeing this
  result): no further extension when the edge improves on its inner neighbour by <= 1 of 750 cases. The
  residual bound (2 cm) is not reached by any constant.
- Interpretation: a positive x offset shortens the receiver's insertion (it approaches from +x), which avoids
  the palm-bar-end contacts that dominate failures; the learned v1 combined policies drifted the other way.

### 2026-11-04 06:45 UTC — Pilot results and decision (`results/v2/pilot/`)

- Realized pilot transitions: smoke 196,608 + combined P1 5,013,504 + combined P2 5,013,504 + residual P2
  4,521,984 = **14,745,600** (cap 15M). All pilot checkpoints evaluated on the 1,150 development cases.
- Combined P1 (default init): step 0 97.5%, checkpoints >= 2M 97.6-97.7%; mean signed residual x -1.4 to
  -2.5 mm. Combined P2 (zero-mean init): step 0 98.1% (exactly 1.5 cm geometry), 1M-2M checkpoints dip to
  94-95%, 4-5M back to 97.9-98.0%; residual x drifts to about -2.6 mm. Neither combined pilot improves on its
  zero-residual comparator on development cases.
- Residual P2: 62.1% at step 0 (= nominal) -> 90.4% at 4.5M on the 1,150 development cases, with a high
  collision-episode rate (35%).
- Rule (declared 06:17 UTC): P2 unless its mean success over checkpoints >= 2M is more than 1.0 pp below
  P1's. P1 97.63%, P2 96.85% (-0.78 pp) -> **P2 zero-mean actor initialization** for all final runs. Both
  pilot configurations are used up; no reward change is made. The negative-x drift of combined policies is
  reported, not tuned away.

### 2026-11-04 06:48 UTC — PROTOCOL FREEZE v2

- Frozen file: `configs/v2/frozen/protocol.json`, SHA-256 `bd79ae5140db002aaeb532a41ebc01a698fdd015078288dcd518f4c4f7779f10`
  (`configs/v2/frozen/PROTOCOL_SHA256`); resolved in the Isaac Lab environment by `scripts/freeze_v2.py` from
  `configs/v2/protocol.json` (source commit c9705d4). Task configuration hash for all v2 learned methods
  `d3bec7da0586891a4c60deac4fb970315add5856a2f3d36f95e2789618989278` (identical to the P2 pilot runs).
- Suites: validation `c611b99a...` (400 cases, seed 6453027), final `041ca5cf...` (2,400 cases, seed 6453026);
  `configs/v2/frozen/SUITES_SHA256`; disjointness check `results/v2/suites_check.json` (no shared case IDs or
  sampled offsets across v1/v2 suites).
- Environment lock `configs/v2/frozen/pip-freeze.txt` is byte-identical to the v1 lock.
- Realized budget per final run 10,027,008 transitions (306 x 32,768). Final runs use a separate clean clone
  at tag `experiment-v2`; any later behaviour change requires a new protocol version.

### 2026-11-04 07:28 UTC — Final training and selection (frozen rule, no decisions)

- Nine final runs completed (10,027,008 transitions each, clean clone at `experiment-v2`); all five candidates
  per run validated on the 400 validation cases (`results/v2/final/selection/`).
- Selected: combined s11 8.0M, s22 10.0M, s33 10.0M; combined_no_phase s11 8.0M, s22 2.0M, s33 2.0M;
  residual s11 10.0M, s22 10.0M, s33 8.0M. Combined candidates are within 377-393/400 (geometry 1.5 cm proxy
  394/400); several runs tie on success and are decided by collision rate / residual norm, as declared.
- Final evaluation matrix generated by `scripts/make_v2_final_matrices.py`: 12 matrices, 49 run entries,
  117,600 scheduled episodes; 4 deterministic entries reuse identical configurations (`final_manifest.json`).

### 2026-11-04 07:48 UTC — Final evaluation, videos, analysis (no protocol changes)

- Final evaluation: 117,600 / 117,600 episodes recorded (manifest), 0 invalid resets, 0 infrastructure errors,
  no reset retries; all 13 evaluation jobs exited 0 (`results/v2/summary/reconciliation.json`).
- Videos: the frozen rule selected 10 videos; one category (release-gate rescue) used its declared fallback
  because no in-training early-release drop occurred without the gate. All 10 single-environment replays
  matched their evaluation records.
- Tooling fixes made after the `experiment-v2` tag, none of which touches simulation, controllers, training or
  evaluation: `v2_select_videos.py` skipped manifest files in its matrix glob (crashed before); learning-curve
  figure uses 10-iteration windows; `v2_analyze_final.py` adds a residual-behaviour table; learned final
  matrices in Git now use checkpoint paths relative to the training root (the runs used absolute paths;
  records identify checkpoints by tag and SHA-256, so the matrices are equivalent).
- Privacy note: commit `38a12ec` (pushed) contained absolute filer paths in `configs/v2/matrices/final/*`, and
  the v1 file `results/videos/video_plan.json` (commit `11e3118`, v1) does too. Shared history is not
  rewritten (force-push is not authorized); the current tree is clean and release text members are redacted.
- Run-to-run nondeterminism measured on the final records: zero-residual untrained policies differ from the
  identical deterministic controller in 2/2,400 (geometry) and 10/2,400 (nominal) outcomes
  (`results/v2/summary/nondeterminism_untrained_vs_zero.json`).
