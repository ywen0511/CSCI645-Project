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

### 2026-11-04 06:33 UTC — v2 constant search on 750 development cases; expanded grid

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
