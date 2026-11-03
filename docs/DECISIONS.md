# Decision log

## Initial handoff: 2026-11-02

Owner-confirmed requirements:

- Approximately one month remains; exact deadline and remote hardware are not specified.
- Execution will happen remotely. The remote agent must understand the entire assignment from GitHub alone.
- Use Isaac Sim through Isaac Lab, two parallel-jaw grippers, geometric coordination, and bounded position-residual PPO.
- Complete implementation, experiments, reporting, and uploads, including checkpoints and a final GitHub Release.
- All project content is in English. The original proposal must remain unchanged.

Engineering defaults selected for a concrete starting point:

- Two Franka arms and one rectangular object; score only the handover, beginning from a physically established giver grasp.
- Three receiver position residuals, fixed orientation targets, one policy; no dexterous fingers or multi-agent RL.
- Direct single-agent external Isaac Lab project, existing IK/PPO integrations, fixed PhysX backend.
- Primary spatial perturbations are translations; coupled giver/object start displacement preserves a feasible initial grasp.
- Three seeds, five methods including the phase-input ablation, nine final evaluation conditions, and the budgets in `configs/protocol.json`.
- Explicit phase-label masking retains raw contact observations and network dimensionality. It does not remove geometry's contact information.

These are proposed implementation choices, not completed experiments. The remote agent may calibrate documented pilot parameters before the protocol freeze while preserving the scientific scope. No simulation, policy training, or GPU timing has been performed by this handoff.

## Entries to add during execution

For each material decision, record date, decision, evidence, affected files/configs, whether made before or after protocol freeze, and implications for comparability. Especially record version pair/backend, frame convention, scene dimensions, thresholds/rewards, perturbation feasibility, training budget/batch size, checkpoint selection, deviations, failure corrections, and release verification.

Use explicit facts and links to run IDs/logs. Do not retroactively rewrite pilot choices as preregistered facts or delete unsuccessful runs from the history.

## Execution log (remote agent)

All entries below were made **before the protocol freeze** unless marked otherwise. Pilot evidence lives in
`results/pilot/` (summaries) and in the logs archive of the release (raw pilot outputs). Run names refer to
those archives.

### 2026-11-03 — Platform and versions (Gate 0)

- **Isaac Lab v3.0.0** (GA release 2026-10-20, commit e3f7d9ff) with **Isaac Sim 6.2.0.0** pip wheels and the
  **Isaac Sim PhysX** backend (`isaaclab_physx.physics.PhysxCfg`), Python 3.12, PyTorch 2.11.0+cu130,
  Warp 1.17.0, **RSL-RL 5.5.1**. This is the release pair named by Isaac Lab 3.0's own compatibility notes.
  Isaac Lab 3.0 also offers Newton/OVPhysX backends; they are not used for any experiment.
- Hardware: NVIDIA A100-SXM4-40GB (one GPU per job), driver 580.159.03, Ubuntu 24.04. A100s lack RT cores;
  physics and training run headless. Videos use the Newton Warp ray-tracing renderer (camera only), which
  runs on any CUDA GPU and pairs with Isaac Sim PhysX; it does not affect physics or control timing.
- The GPU nodes ship only compute driver libraries. Isaac Sim needs a Vulkan ICD even headless, so the
  user-space graphics libraries of the *same* driver version were extracted from NVIDIA's installer
  (no system changes; see `docs/SETUP_REMOTE.md`).
- Isaac Lab 3.0 conventions adopted: quaternions are `(x, y, z, w)`; data via `ProxyArray.torch`; joint
  targets via `articulation.actuators.target_command`; no `--headless` flag (headless is the default).
- Project scaffolding metadata comes from the official generator
  (`tools/template/cli.py --non_interactive --task_type external --workflow direct:single-agent
  --rl_library rsl_rl`); its machine-specific `[tool.uv.sources]` paths were removed.

### 2026-11-03 — Scene, frames and grasp geometry (Gate 1)

- Bases at x = -0.62 m (giver, yaw 0) and x = +0.62 m (receiver, yaw 180 deg). Handover center (0, 0, 0.50) m.
  Bar 0.18 x 0.035 x 0.035 m, 0.15 kg, friction 1.0, long axis = world x. Kinematic table 0.30 x 0.30 x 0.20 m
  under the handover center (top at 0.20 m) for drop detection only.
- Both hands point along the bar axis (giver +x at the -x end, receiver -x at the +x end); TCP insertion
  0.025 m. Hands never share space. TCP = `panda_hand` + 0.1034 m along hand z: finger collision geometry
  spans 0.0585-0.1123 m along hand z (inspect_scene), so the TCP lies inside the pads 9 mm from the tips.
- **Finger closing axis: horizontal (world y).** First design closed vertically; Gate-1 development data
  (`gate1b`) showed the receiver's lower finger *catching* the bar after premature release (nominal had
  0 drops even at -0.30 s release). That made release timing physically irrelevant and the release-gate
  hypothesis untestable, so both grippers were rotated 90 deg about the approach axis; only friction now
  carries the weight. Re-run (`gate1c`): nominal joint_early_stress fell to 2 % success with drops and
  shallow-grasp timeouts. This is a physical-design correction, not a change of perturbation ranges.
- Robot actuation: Franka (flat `franka_panda.usda`, PhysX payload, primitive colliders), arm PD
  400/80 with arm gravity disabled (as Isaac Lab's high-PD IK preset). Gripper k = 2000 N/m, d = 100,
  effort cap 70 N, 0.2 m/s; ~17 N per finger on the bar. The lift-task finger gains (k 350, d 175;
  0.5 s time constant) did not close before settling ended (all resets invalid, run `scripted1` v1).
- Low-level controller (all methods): Isaac Lab `DifferentialIKController` (pose, DLS) on the hand frame,
  evaluated every physics substep in the world frame, fixed hand orientations, joint targets clamped to
  soft limits, common receiver workspace box. Null-space joint-limit avoidance left 2-7 mm steady error,
  so it is disabled; instead verified joint seeds (>= 0.12 rad from limits, zero IK error) are written at
  reset (`inspect_scene`).

### 2026-11-03 — Reset settling and validity

- Settling (learning disabled): 0.3 s object pinned at its shifted start while the giver servos to the
  shifted hold pose; 0.3 s giver closes (object still pinned); 0.3 s object free in the giver's grasp.
  No pin, weld or teleport acts after settling. Validity: both giver fingers > 0.2 N on the object, no
  table support, object above the drop height, finite-difference object speed < 0.05 m/s, no prohibited
  contact, |realized - requested| start displacement < tolerance. Up to 3 deterministic attempts.
- **Offset tolerance 8 mm.** Over 899 development resets the bar sags a systematic 2.2 mm in z after
  release into the giver's grasp; |realized - requested| median 2.2 mm, p99 4.7 mm, max 5.0 mm. The
  initial 5 mm tolerance rejected one borderline stress case nondeterministically; 8 mm covers the tail
  and stays well below the 10-20 mm perturbation scale. Realized offsets are logged per episode.

### 2026-11-03 — Measurement fixes

- **Relative motion by finite differences.** PhysX-reported velocities of the bar squeezed between fingers
  contain depenetration bias (a static, gripped bar reported ~1.04 rad/s while its orientation changed
  < 0.05 deg). The stability proxy, evaluator and observations use finite differences of the measured
  object pose relative to the receiver hand over one control step.
- **Exact episode clock.** Float accumulation of 0.05 s steps drifted by ~2e-6 s and delayed the nominal
  release by one control step; time is now an integer step counter times dt, and timing comparisons use a
  1e-4 s tolerance.

### 2026-11-03 — Calibration of geometry and diagnostics (development cases only)

- Stability proxy kept at the initial thresholds (0.2 N per finger, 0.03 m/s, 0.5 rad/s, 0.15 s dwell):
  with finite-difference motion, clean runs reach stability at 2.70 s, before the nominal 2.8 s release.
- **Alignment bound 0.010 m per axis** (gain 1.0). With 0.015 m geometry succeeded on 100 % of every
  development condition (`gate1c`), i.e. it removed nearly all stress error, which the specification warns
  against ("avoid unbounded exact tracking"). The bound now equals the in-range perturbation envelope
  (+/-1 cm): geometry is 100 % in-range and 92-96 % on stress conditions (`gate2`). Chosen before any
  learned-policy result exists. Shared-holding tolerance 0.01 m and 1.0 s release wait kept.
- Misalignment diagnostic measured at t = 2.4 s (just before receiver finger contact in clean runs)
  instead of 2.0 s, because the receiver's tracking lag (~9 mm at 2.0 s even when clean) flagged 40/50
  in-range cases at 2.0 s regardless of the perturbation.
- Prohibited contact: any monitored robot link (links 1-7, hand) or finger contact with the table or a
  non-object body above 1 N; counted as an event; terminal when sustained for 0.25 s. Finger-object
  contact is never a collision. In development runs nominal failures under +x offsets are palm-bar-end
  contacts (deeper insertion), and under -x offsets shallow grasps that sag (timeouts).

### 2026-11-03 — Negative controls (Gate 1)

- `no_receiver`: 20/20 drop. `giver_holds` (no release request): 20/20 episode timeout, 0 successes.
  `table_support` (separate process with a 6 cm-wide table under the bar's middle, between the grippers):
  receiver holds at ~17 N per finger and the giver opens, yet 0/20 successes because the table carries
  1.5 N. Clean nominal and geometry: 100/100 each (clean cases are deterministic repeats).

### 2026-11-03 — Training integration and budget

- PPO through RSL-RL 5.5.1 `OnPolicyRunner` (created with Isaac Lab's `create_rsl_rl_runner` after
  `handle_deprecated_rsl_rl_cfg`); the training loop replicates `OnPolicyRunner.learn` to checkpoint on
  transition boundaries. `clip_actions=None`; the only squashing is `0.02 * tanh(a)` in the task.
- Throughput 1024 envs: ~10,000 environment transitions/s on one A100 (smoke run `smoke_ppo1024`), so
  the default budget of 10M transitions per run (~17 min) is kept; no common-budget reduction.
- Resume restores model, optimizer, iteration, transition counter, curriculum position and RNG states,
  and restarts episodes at a boundary (approximate continuation). Verified in `smoke_ppo1024`
  (train 3 iterations, resume to 5, evaluate the final checkpoint in a new process: 20/20 dev clean).

### 2026-11-03 — PROTOCOL FREEZE v1

- Frozen file: `configs/frozen/protocol.json`, SHA-256 `9727eae67fdab5ce2c908e7b467f510707a668d89531cad22acd6286d83f97fc`
  (also in `configs/frozen/PROTOCOL_SHA256`). Task configuration hash
  `b9eac03d5848617625efd453adf1eb02fa942693766b137bc631cd052ec52b8d` (task-level physics, control, reward,
  observation, geometry and evaluator parameters; identical for every method apart from the method flags).
- Suites (generated from the frozen protocol; content depends only on the protocol seeds and bounds):
  final 1800 cases sha256 `880ac131487d88a3571e7ff308493359d93267281ce5617b0a18fe23d01d7b0d`;
  validation 100 cases sha256 `328639febceabd254d0a6be7a2cf83d1d986ed07416bd6df468051373a0b6f47`;
  development 450 cases sha256 `f75bd8c11517c2cf489ba15b387c1c059a2df3a59e10343f964b89d56ea903e1`.
- Training: 1024 environments x 32 steps = 32,768 transitions per PPO iteration; 306 iterations =
  **10,027,008 transitions per run** (10M rounded up to whole rollouts), seeds 11/22/33, methods residual,
  combined, combined_no_phase. Checkpoints at the first iteration boundary at or after every 1M transitions
  plus step 0 and final. Validation candidates: step 0 and the checkpoints at/after 2M, 4M, 6M, 8M, 10M
  (and final), on the 100-case validation suite; selection = highest validation success, then lowest drop
  rate, then earliest step. Final evaluation: selected checkpoint of every run + nominal + geometry on all
  1,800 final cases (19,800 episodes).
- Pilot budget used before freezing: 2 x 5,013,504 transitions (`pilot_combined_s101`, `pilot_residual_s101`)
  plus smoke runs (~0.26M); total below the 15M pilot cap. Pilot seeds (101) are disjoint from final seeds.
  Pilot development results (not held-out; for calibration only): nominal 79.3 %, geometry 98.0 %,
  residual 83.1 % (5M), combined 97.1 % (5M) over the 450 development cases.
- The experiment source is the commit tagged `experiment-v1`; final runs execute from a clean clone of
  that tag. Any later change to physics, reset, reward, observations, action, geometry or evaluator would
  require a new protocol version and reruns.

### 2026-11-03 04:03 UTC — Validation saturation; secondary analysis declared (post-freeze, before any final-test result)

- Observation: for `combined_seed11` and `combined_no_phase_seed11` every validation candidate, including the
  untrained step-0 policy, scored 100/100 on the validation suite (sampled from the final training
  distribution, +/-1 cm and +/-0.15 s), because the geometry module alone already solves that distribution.
  The frozen selection rule (highest success, then lowest drop rate, then earliest step) therefore selects
  step 0 for those runs. The rule is applied unchanged to all nine runs; the primary results use the
  selected checkpoints.
- Declared now, before any final-suite result of a learned policy exists: a **secondary analysis** evaluates
  the preserved *final* checkpoint of all nine runs on the same 1,800 final cases. It is reported separately,
  labelled secondary, and is never used to choose among checkpoints. Records go to `eval_final_checkpoint/`.
