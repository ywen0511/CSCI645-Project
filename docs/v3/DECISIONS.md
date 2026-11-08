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

## Remote execution (dates/times from `date -u`)

### 2026-11-08 16:07 UTC — runtime, compute and orchestration (split: none; engineering)

- Runtime: the verified v2 stack is available unchanged on the cluster (Isaac Lab v3.0.0 at `e3f7d9ff…`,
  Isaac Sim 6.2.0.0, RSL-RL 5.5.1, torch 2.11.0+cu130, Python 3.12.16, A100-SXM4-40GB, driver 580.159.03,
  user-space Vulkan ICD). All v3 simulator work runs on one 8-GPU node of that type (queue `gpu_large_shared`,
  1 GPU per job). Other nodes have a different driver (580.105.08) and are not used, so no stack mixing.
- Preflight (`v3_prepare.py` reproduces the committed suites byte-identically; 49/49 CPU tests pass with the
  locked Python, 0 skipped; `doctor.py` and `inspect_scene.py` pass): `runs/v3/preflight/`.
- Step order of the installed `DirectRLEnv.step` read from source: pre-physics → physics × decimation →
  `common_step_counter += 1` → `_get_dones` → `_get_rewards` → resets → observations. The sensor token is the
  counter; one advance per control frame, including settling.
- Orchestration: `scripts/v3_jobs.py` runs committed task manifests (`results/v3/jobs/`) with a per-attempt
  ledger. Isaac Sim intermittently hangs in Kit shutdown after all outputs are written ("SimulationContext
  cleared", process never exits); four first-attempt jobs lost their wall-time this way. The runner now kills a
  task's process group 90 s after that marker if all declared outputs exist, and records the event; a per-task
  timeout fails anything else. Records written before a kill are complete (the evaluation writes and validates
  them before leaving the simulation context).
- The first acceptance/development attempt ran at `913cda1`; after the runner fix, every output was moved to
  `runs/v3/superseded/candidate_913cda1` and all tasks re-run at the new commit, because v3 evaluation caches are
  keyed to the source commit and are (correctly) rejected otherwise.
- Pilot budget: 8 pilots × 2,752,512 transitions (84 PPO iterations) + 1,966,080 smoke/resume transitions (two
  attempts) = 23,986,176 ≤ 24M.

### 2026-11-08 16:31 UTC — development baselines and selection (split: development only)

- All 85 development entries (1 nominal + 6 estimators × 14 geometry settings, 312 cases each, fresh process
  per entry) completed at `2d20fe4`; nominal ignores the estimator and is run once (aliased in the table).
- Selection (`scripts/v3_select_baselines.py`, six validation-like strata, equal weight): `geometry_common` =
  `geometry_best_constant` = `geometry_giver` = EMA 1.0 + giver reference, 1.5 cm, zero constant (144/144 on the
  selection strata, 312/312 on all 13 development conditions); `geometry_filtered` = EMA 0.2, 1.5 cm (144/144);
  `geometry_raw` = 96/144; nominal 117/144. The three aliased roles are evaluated once in the final matrix and
  reported as aliases, not as independent evidence. Selections sit at grid edges (1.5 cm bound; EMA 1.0 for
  the giver-reference estimator; EMA 0.2 for filtering), recorded in `at_grid_edge`; no further search.
- Finding used for acceptance check 7: with the raw (unfiltered) estimate, finite-difference velocity noise
  blocks the stability-gated release at noise ≥ 2 mm (24/24 release timeouts in noise_2mm, noise_4mm,
  mixed_id, mixed_ood); EMA 0.2 and the giver reference do not. Delay up to 4 steps has no effect on any
  estimator. Bias 10 mm causes collisions unless the giver reference is used.
- Consequence fixed by the protocol (not chosen by us): every combined profile and the residual-only profile
  inherit the giver-reference estimator. While the giver holds the bar (both contacts, release not commanded),
  object translation is inferred from the measured giver TCP and the nominal grasp offset; the corrupted
  sensor is used after release. Development data suggest little remaining headroom for learned residuals on
  top of this controller; this is recorded as a pre-test expectation, not a result.
- Simulator code (`src/`, train/eval/scripted/video scripts, v3 suites, development matrices, draft profiles) is
  byte-identical between `913cda1`, `2d20fe4` and the current commit (git diff empty); acceptance evidence
  produced at different commits of tooling therefore exercises the same simulator code.

### 2026-11-08 16:35 UTC — giver-reference accuracy, physical transfer, video rule (split: development)

- Giver-reference estimate vs true object position on traced development cases (EMA 1.0 + giver reference):
  at most 3.0 mm while the giver holds (rigid-grasp model: nominal grasp offset vs the realized grasp), then
  the corrupted sensor after release (up to 6.1 mm in noise_2mm, 10.7 mm in mixed_id). It is therefore not an
  oracle; it removes most pre-release translation error by using accurate giver proprioception, which the
  policy also observes (giver TCP − receiver TCP). This is the allowed information channel the assignment
  requires to be disclosed.
- Physical transfer (Section 10) is **not performed**. Evidence: the bar's spawn geometry, mass and friction
  come from module constants in `handover_env_cfg.py` (`CuboidCfg(size=OBJECT_SIZE)`, `MassCfg(mass=OBJECT_MASS)`,
  fixed `RigidBodyMaterialCfg`), so the task field `object_size` does not change the simulated object. A valid
  transfer study needs spawn overrides plus consistent grasp transforms, reset poses and jaw clearance, each
  validated on separate development starts before the freeze. The mandatory uncertainty study is prioritized;
  nothing about transfer is claimed.
- Video selection rule frozen in `configs/v3/video_rule.json` before any final outcome is opened.
