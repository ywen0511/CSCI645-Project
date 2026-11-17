# V3 execution assignment: observation robustness in bimanual handover

> **Archived assignment — completed in release v3.0.0.** For current work, execute
> [POST_V3_EXECUTION.md](POST_V3_EXECUTION.md). Keep this original contract as
> historical evidence; do not repeat its freeze or training stages in place.


## Your assignment and authorization

You are the remote execution agent for Yan Wen's CSCI 645 project in
`https://github.com/ywen0511/CSCI645-Project`. **Complete this assignment end to end.**
This document supplies the task context, decisions, implementation requirements,
experiment protocol, acceptance gates, and publication requirements. Do not ask for
the owner's local files or previous conversation. Repository files referenced below
are available in your clone. All code, documentation, reports, slides, video labels,
release notes, and final communication must be in English.

Start from branch **`study/v3-observation-robustness`**. This is an extension of the
completed v2 project at `4204da23b17f920d955a0bc90f94a8df271c524f`, not a replacement.
Preserve v1/v2 data, tags, releases, proposal files, and unfavorable findings. The
historical complete status in `STATUS.json` applies to those studies only. V3 is
not complete until this document's acceptance gates and fresh-download checks pass.

The owner authorized implementation, corrections, dependency installation in an
isolated environment, training and evaluation on available remote GPU resources,
resume/retry, Git commits/pushes, immutable tags, and publication of all results and
checkpoints as GitHub Releases. No repeated permission is needed for these actions.
The preparation agent was explicitly prohibited from running GPU work; its CPU
checks are not simulator acceptance evidence. You must perform that acceptance.
Do not buy compute, change security settings, expose credentials, force-push shared
history, overwrite an existing release, or delete unrelated files. Actual missing
GPU access, simulator entitlement, storage, or GitHub write permission is a blocker:
record exact evidence and continue independent work. Never fabricate completion.

Reading this file is the assignment to execute, not merely to propose another plan.
Finish necessary engineering autonomously, run the full frozen study, analyze it,
write and inspect the deliverables, publish them, verify them from a fresh checkout,
and return their public links. A scaffold, training launch, or good-looking video
does not finish the assignment. A negative scientific result is valid completion.

## 1. Scientific question and retained scope

**When strong geometric handover control already works, how do object-translation
estimation errors affect geometry and residual learning, and does short observation
history improve robustness?**

Keep Isaac Sim through Isaac Lab, PhysX, two fixed-base Franka arms, two-finger
parallel-jaw grippers, one rigid rectangular bar, fixed commanded orientations,
scripted approach/gripper commands, and a bounded receiver XYZ PPO residual
(`0.02 * tanh(action)` meters per axis, not accumulated). No external dataset is
needed: training data are online simulator transitions. No camera perception,
demonstration collection, real hardware, dexterous hand, or simulator migration.

Keep the independent two-second receiver-only holding evaluator. Success requires
giver release/open fingers, no giver or table support, no drop, and bounded relative
drift/motion. Never attach the object during scored time. Existing settling pinning
is allowed only before scoring. Reset failures and infrastructure failures are
separate from task failures; reconcile all scheduled cases. The scored horizon,
release gate, control period, collision rule, reward coefficients, and action limits
must be common across compared methods unless a declared ablation changes one.

V2 found that residual-only learning helped the nominal script, but combined PPO did
not beat strong geometry or geometry plus a tuned constant. Preserve that result:
v2 all-case success was nominal 65.2%, residual 82.6%, geometry 96.5%, combined 96.1%,
geometry plus constant 99.2%. The scope was one object, accurate state, three seeds,
and initial translation/release-time perturbations. V3 tests the boundary of that
finding. Do not make the baseline artificially weak or promise that RL will win.

Hypotheses to test:

1. Translation bias/noise/delay affect the controllers differently; severity curves
   and failure modes are more informative than one pooled success number.
2. Noise-trained residuals may improve robustness relative to clean-trained ones.
3. Short history may help under partial observability, beyond extra input parameters.
4. Filtering and a giver-grasp kinematic reference may remove most of that benefit.

Translation corruption is a controlled synthetic sensor model, not a vision system.
Orientation, joint states, TCP proprioception, gripper widths and object-specific
contact forces remain accurately measured. In this mostly stationary handover,
delay may have little effect before release. Report that if observed; do not add
unplanned object motion after seeing the test results to create an RL advantage.

## 2. What is already prepared, and what you must validate

Prepared on CPU:

- `core/observation.py`: case/frame-indexed Gaussian translation noise, episode bias,
  delay with causal startup padding, EMA estimator, reset-isolated history stack.
- `tasks/handover_env.py` and `_cfg.py`: opt-in sensor path, shared controller
  measurements, estimated translation-derived velocity, history/repeated-current
  control, giver-reference estimator, sensor trace metadata. Archived defaults remain
  the default path. Ground-truth evaluator and training reward remain separate.
- `v3_protocol.py`, `scripts/v3_prepare.py`: deterministic suites, disjoint splits,
  candidate training configs and development baseline matrices, freeze guard.
- `scripts/eval_matrix.py`: v3 cache validation rejects wrong source, wrong sensor
  parameters, duplicate/extra cases, and missing final records.
- `v3_analysis.py`, `scripts/v3_analyze.py`: raw-data checks, per-seed counts and
  paired clustered bootstrap contrasts. Extend plotting/reporting around these.
- CPU tests and `docs/v3/PREPARATION.md`: exact verification evidence and limitations.

**These are implemented candidate components, not GPU-validated experiments.**
Inspect actual installed Isaac Lab control-loop ordering, reset callbacks, tensor
wrappers, RSL-RL normalization and serialization before trusting the integration.
Correct issues on development data, add meaningful regression tests, and record
changes before freezing. Do not simply run an old v2 command and call it v3.

Important implementation boundaries:

- Defaults `observation_sensor=None`, history length 1, history mode `stack`, and
  giver-reference false preserve the historical path/config hash. Do not use new
  source to claim bitwise reproduction of old releases; use their original tags.
- Sensor advances once per control frame and per environment, including settling;
  reset retries restart the same error stream. Repeated observation reads at a
  single control-frame token must not advance noise/filter/history. Confirm the
  simulator calls `_get_dones`/`_get_observations` in the assumed order.
- `self.m` is truth for reset validation, rewards and independent outcomes.
  `controller_m` supplies estimated object translation to policy, geometric
  alignment and stability gating. Estimated relative linear velocity must be
  derived from the same estimated position, not leaked from true translation.
- Ground-truth dense/terminal reward during simulation training is allowed and
  must be disclosed. Neither actor nor critic receives true translation or hidden
  bias/seed/delay labels. Current PPO actor and critic use the same policy input.
- Contacts/orientation/proprioception stay accurate by design. A policy can infer
  object location from the giver TCP; this is why the giver-reference baseline is
  mandatory. This study does not simulate uncertainty in every sensor.
- The giver-reference estimate is measured giver TCP minus the nominal known grasp
  offset rotated by measured object orientation, only while both giver contacts
  exist and release has not been commanded. It is a rigid-grasp model, not true
  object translation or a fit to final-test data. Check switching and slip behavior.
- EMA is a controller estimator, not a change to the error realization. Same case
  seed/frame must give the same raw noise regardless of controller, vector slot,
  batch size or rollout completion ordering. CPU/CUDA transcendental roundoff and
  PhysX nondeterminism can still differ; measure and report these separately.
- History is oldest-to-newest, length 5 (230 features); repeat-first padding on
  reset. At 20 Hz its oldest sample is 0.20 s old. Apply any phase mask to every
  frame before normalization. The same-dimensional control repeats the current
  46-feature observation five times and has no temporal memory.

## 3. Setup and work organization

Use a GPU machine already available to you. Create an isolated environment and a
clean worktree. The repository's verified v2 platform was Ubuntu 24.04, Python 3.12,
Isaac Lab v3.0.0 at `e3f7d9ff1f5d7f8280de3ece9000b7117f66bcf4`, Isaac Sim 6.2.0.0,
RSL-RL 5.5.1, torch 2.11.0+cu130, PhysX, and an A100 40 GB. The CPU preparation used
a different Python/torch stack and is not a replacement for this runtime lock.

Read `docs/SETUP_REMOTE.md`, `scripts/setup/build_env.sh`, and
`configs/v2/frozen/pip-freeze.txt` for the existing installation. Inspect upstream
official documentation for the installed version. If the recorded stack is not
available, document the exact incompatibility and validate a compatible stack on
development cases; do not mix stacks within the final comparison. Record OS, GPU,
VRAM, driver, CUDA, Python, complete package lock, simulator/Lab commits, physics
and control rates, quaternion convention, and all launch environment variables.
Use dedicated scratch/cache variables; do not repurpose the user's HOME.

Initial commands (substitute only machine paths, never scientific settings):

```bash
git clone --branch study/v3-observation-robustness https://github.com/ywen0511/CSCI645-Project.git
cd CSCI645-Project
python scripts/v3_prepare.py
CUDA_VISIBLE_DEVICES='' python -m unittest discover -s tests -v
python scripts/doctor.py --output runs/v3/preflight/doctor.json
python scripts/inspect_scene.py --output runs/v3/preflight/scene.json
```

The last two commands require the remote simulator runtime and may use GPU. They
were not run by the preparation agent. `v3_prepare.py` is CPU-only and must run
before remote tuning; do not regenerate draft training configs after you tune them.

Test Git read/write and Release capability before long runs, without exposing
credentials. `git push -u origin study/v3-observation-robustness` publishes commits;
use available GitHub API/CLI authentication for releases. The preparation agent's
connector permissions are not evidence of your remote permissions.

Keep small source/configs/summaries under version control; put large binaries/raw
records under ignored `runs/v3/` until packaging. Maintain:

- `V3_STATUS.json`: stage, active jobs, planned/completed counts, blockers, next action,
  source commits, final release URL, and completion flags supported by evidence.
- `docs/v3/DECISIONS.md`: dated engineering/scientific decisions and their data split.
- `results/v3/run_index.json`: every smoke, pilot, final, failed and resumed run.
- `results/v3/task_ledger.jsonl`: commands, input hashes, source, timestamps, exit
  status, attempts, outputs and hashes. Never trust only a count/status cache.

Make incremental commits and push milestones. Formal simulator jobs must run from
the same clean immutable experiment worktree. Use a separate delivery worktree for
analysis/docs and record both commits. New data files must not cause a source SHA
change halfway through a final evaluation. Do not leave jobs unmonitored and end
the assignment while they are merely queued/running.

## 4. Remote acceptance before pilots

Write `results/v3/acceptance.json` with the command, commit, evidence path and pass/
fail for every check. All must pass before formal training:

1. One-env and multi-env reset/settling, physical grasp, release and two-second
   independent hold. Repeat negative controls `no_receiver`, `giver_holds`, and
   `table_support`; none may score success. Use the existing negative-control scene
   settings in `configs/closeout/`, including the narrow raised table configuration.
2. Verify zero residual equals its deterministic controller under identical v3
   sensor settings. Check single squashing, 2 cm bounds, no accumulation, reset
   isolation and fixed-release semantics without geometry.
3. For analytic moving-position inputs, confirm bias, noise moments, delay in actual
   control steps, EMA response and derivative. Compare logged raw sensor outputs
   for the same case across batch sizes 1 and 23, reordered case queues and unrelated
   environment resets. Exogenous noise should match; physics need not be bitwise equal.
4. Trace the first reset, first scored frame, terminal frame and immediate next
   reset. There must be no stale measurement/history from the previous episode,
   no duplicate noise advance, and no observation from the future. Check that the
   simulator's token semantics match the pure module contract; fix if necessary.
5. Audit all object-translation-derived policy/controller channels. Hold available
   sensor/contact/proprioception inputs fixed in a dependency test and change hidden
   true translation; actor inputs and geometric targets must not change through a
   hidden translation path. Rewards/outcomes may change. Document the allowed giver
   proprioception and orientation channels instead of claiming complete blindness.
6. No-error v3 sensor path versus archived default path: finite-difference/reset
   treatment can differ at boundaries. Compare traces and outcomes; explain/fix
   unintended changes before freeze. Keep archived v2 execution on its original tag.
7. Verify geometry-only and all combined profiles use the same chosen estimator,
   geometry thresholds and gains; policy and geometry see the same estimate. Compare
   raw, EMA and giver-reference baselines. Noisy finite differences must not create
   a universally blocked release gate without testing filtered alternatives.
8. Verify real history versus repeated-current inputs, 46/230 feature dimensions,
   normalization freeze at inference, shape-compatible checkpoint load, no hidden
   corruption parameters in observations, and no simulator state in the critic.
9. Run a short PPO smoke for each distinct method/input shape. Save/reload actor,
   critic, optimizer, normalizer and RNG/counters. Interrupt and resume for two PPO
   iterations; check monotonic counters and preserved optimizer/normalizer state.
   Resumption restarts episodes and is approximate, not a bitwise simulator restore.
10. Delete/truncate an output in a disposable evaluation copy and alter one case,
    checkpoint or config hash. Resume/verification must reject stale records and
    re-execute only genuinely missing work. Never report complete from `matrix_status`
    alone. The old closeout driver's fast path is not a v3 acceptance mechanism.

If sensor-gating changes reveal an implementation fault, correct it for all methods
before freeze. Do not change the independent success evaluator to hide a failure.

## 5. Data and split contract

The committed development suite has 312 cases (13 conditions x 24); validation has
240 cases (6 conditions x 40); the final suite will have 2,600 cases (13 x 200).
There are no external data downloads. The generator fixes independent split seeds
6455101/6455201/6455301 and case-specific seeds. IDs and random streams are disjoint.

Except the clean reference, physical starts are sampled uniformly within +/-2 cm
per axis and release offsets within +/-0.30 s. These physical draws are paired
across severity conditions using `base_case_id`, and across all methods. The clean
condition repeats one physical setup: report it as a reliability check, not 200
independent initial states. Do not drop hard cases or silently resample resets.

| Condition | Translation bias | Gaussian noise sigma/axis | Delay |
|---|---:|---:|---:|
| clean | 0; also zero physical perturbation | 0 | 0 |
| physical_only | 0 | 0 | 0 |
| bias_2mm / bias_5mm / bias_10mm | +/-2 / +/-5 / +/-10 mm per axis | 0 | 0 |
| noise_1mm / noise_2mm / noise_4mm | 0 | 1 / 2 / 4 mm | 0 |
| delay_1step / delay_2step / delay_4step | 0 | 0 | 1 / 2 / 4 control steps |
| mixed_id | uniform +/-5 mm/axis | 2 mm | 2 steps |
| mixed_ood | uniform +/-10 mm/axis | 4 mm | 4 steps |

Bias-only conditions use randomly signed fixed amplitudes on each axis. The signs
and sensor noise streams are paired across severity levels. At the inherited 20 Hz,
delays are 50/100/200 ms. Validate the actual rate before freezing. Translation only
is delayed, not orientation or contacts; explicitly describe this approximation.

Validation and deterministic-baseline selection use only `clean`, `physical_only`,
`bias_5mm`, `noise_2mm`, `delay_2step`, and `mixed_id`. Development includes stronger
conditions for feasibility diagnostics; do not optimize policies/baseline selection
against those stronger conditions. Final stronger levels are severity extrapolation
with fresh realizations, not an unseen type of corruption. Mixed ID is the primary
test condition. Keep all individual severity tables; never bury them in an average.

## 6. Baselines and bounded pilots

Run the six committed development matrices: EMA alpha {1, .5, .2} x giver-reference
{off,on}. Each matrix has nominal plus geometry at alignment bounds {1.5, 2 cm} and
x constants {-10,-5,0,5,10,15,20 mm}, y=z=0. It is 28,080 development episodes in
total (6 x 15 x 312). Do not rerun identical nominal results as independent evidence.

Example, executed only on the remote GPU:

```bash
python scripts/eval_matrix.py \
  --matrix configs/v3/matrices/development/ema0p5_giver1.json \
  --output runs/v3/development/ema0p5_giver1 --seed 6455501
```

Use the six validation-like development strata equally weighted. Select:

- `geometry_common`: best zero-constant geometry estimator/alignment combination.
- `geometry_best_constant`: best candidate including constants over the full grid.
- `geometry_raw`: unfiltered, no giver reference, 1.5 cm geometry, zero residual.
- `geometry_filtered`: best EMA-only zero-constant geometry (giver-reference off).
- `geometry_giver`: best giver-reference zero-constant geometry.
- `nominal`: original script, no geometry or residual.

Tie-break by scheduled-case success descending, collision rate ascending, absolute
constant ascending, alpha descending, alignment bound ascending, giver-reference
false before true, then candidate ID. Store every candidate's count table and the
selected IDs/settings in `configs/v3/baseline_selection.json`. Preserve raw
development results. Hitting a grid edge is a limitation, not permission for an
unbounded search. The 2 cm alignment bound and +/-2 cm constants use the same
residual action scale as PPO; do not call the best grid point a global optimum.

All combined profiles inherit **exactly `geometry_common`** (including EMA and
giver-reference), zero constant. Stronger `geometry_best_constant` remains a separate
challenging comparator. Residual-only has geometry/gating off but uses the same
measurement estimator and available observations. Thus the experiment tests residual
value on top of a fair common estimator. Do not give PPO an oracle-only feature.

Pilot budget: at most 24 million transitions in total, seeds 101/102 only, maximum
8 runs at up to 3 million transitions each. Include robust FF, history, repeated-
current and residual-history smoke/pilots. Check reward breakdown, gradient/normalizer
stability, residual authority, gate saturation, reset validity and throughput.
Prefer fixing faults over a large hyperparameter search. Keep the inherited PPO
settings/reward unless development evidence demonstrates a concrete failure; log
every candidate and apply a selected change across comparable variants.

Estimate total GPU hours and disk use from measured throughput, including evaluation,
rendering and retries. Formal scope below is 230M requested training transitions,
plus <=24M pilots, plus evaluation. Reserve at least 25% of available time for
verification/reporting. Do not spend a month on unbounded tuning. If actual resources
cannot meet the required scope, record the shortfall before formal runs; finish
feasible work and label the incomplete requirements. Do not silently reduce seeds
and still claim this assignment is complete.

## 7. Formal learning comparison and protocol freeze

| Family | Method CLI | Training errors | Input | Seeds |
|---|---|---|---|---|
| combined_clean_ff | combined | zero | current 46 features | 11,22,33,44,55 |
| combined_robust_ff | combined | robust mixture | current 46 | 11,22,33,44,55 |
| combined_robust_history | combined | robust mixture | five-frame stack, 230 | 11,22,33,44,55 |
| residual_robust_history | residual | robust mixture | five-frame stack, 230 | 11,22,33,44,55 |
| combined_robust_repeat | combined | robust mixture | current frame repeated five times, 230 | 11,22,33 |

The last family is the matched-input-size memory control; compare it to the matching
three history seeds. Keep MLP hidden widths [128,128], PPO settings and action bounds
equal. Report parameter counts: FF versus history is not parameter-count matched;
the repeated-current comparison is. Do not infer memory's causal value from the
FF comparison alone. V2 already studied explicit phase masking; retraining that
ablation is not required for the main v3 question.

For the robust mixture, at episode reset draw a clean-error episode with probability
.25. Otherwise draw each bias uniformly +/-5 mm, sigma uniformly [0,2] mm, and delay
uniformly from {0,1,2} control steps. Keep each episode's parameters fixed; Gaussian
noise varies per control step. Physical perturbation curriculum remains the v2
curriculum: 0-10% clean; 10-30% +/-1 cm,+/-.15s; 30-50% +/-1.5cm,+/-.225s;
50-100% +/-2cm,+/-.30s. The clean-trained comparator shares this physical curriculum.

Each of the 23 formal runs gets 10,000,000 requested environment transitions, rounded
up to the same PPO rollout boundary (1024 envs x32 steps gives 10,027,008). Count
settling transitions consistently and also report scored transitions. A smaller
batch due to measured VRAM limits must be chosen before freeze, applied to all runs,
and the actual rounded budgets/learning schedules recorded. Seeds are replicates;
do not substitute many rollout cases for independent training runs.

Freeze after acceptance and development decisions, before final training/testing:

1. Copy the five tuned protocol files from `configs/v3/training/` to
   `configs/v3/frozen/training/`; set `status=frozen`, distinct v3 protocol IDs,
   geometry_common settings, actual batch/budget, and final seed lists.
2. Write `configs/v3/FREEZE.json` with `status: frozen`, `source_commit` (the clean
   tested candidate commit), `gpu_acceptance_evidence` (path + hash), and `files`
   mapping repo-relative paths to SHA-256. Include executable source, train/eval
   scripts, suite generator, draft design, all frozen protocols, baseline selection,
   development/validation suites, final-condition design, selection rule and budgets.
3. Commit these decisions. Run `python scripts/v3_prepare.py --final` to generate
   final cases after the freeze checks. Commit the final suite and its hash.
4. Tag and push this final executable snapshot as **`experiment-v3`**. If the name
   already exists, verify its identity; never move it. Use `experiment-v3-r2` for a
   genuinely necessary corrected study, preserving superseded evidence.
5. Create a clean experiment worktree at that tag for all formal jobs. Record the
   final experiment SHA separately from the earlier tested candidate SHA. Analysis
   and publication continue in the delivery worktree. Do not open final outcomes
   until tuning, formal training and checkpoint selection are finished.

Example final training command:

```bash
python scripts/train.py --method combined --seed 11 \
  --protocol configs/v3/frozen/training/combined_robust_history.json \
  --output runs/v3/train/combined_robust_history_s11 --run-type final
```

Loop all declared profiles/seeds with a recorded job manifest, not copied ad hoc
commands. Save step 0, every 1M transition boundary, final, latest and resumable
state. Validate resumes against method, seed, observation shape/history mode,
protocol hash, source and total budget before loading. Never overwrite an earlier
checkpoint under a misleading filename; preserve resumed lineage.

## 8. Validation selection and final evaluation

Evaluate trained candidate checkpoints at the first saved step at/after 2M,4M,6M,
8M,10M on all 240 validation cases, with frozen normalization and no exploration.
Step 0 is an untrained control and is never eligible for selection. Select highest
validation success rate, then lowest collision rate, lowest mean bounded residual
squared norm, then latest transition count (existing `selection.select_v2`). Require
all scheduled validation cases accounted for and valid before comparing candidates.
Archive every candidate result and selection rationale; retain selected and final
even if their bytes are identical. Plot all learning curves, not just the winner.

Use `scripts/eval_matrix.py` for v3 evaluation. Make separate matrix/process files
for every estimator, observation length/mode and protocol. Those settings are NOT
runtime-safe entry overrides. `--only ENTRY` in a fresh process avoids controller-
ordering effects within one simulator; use this for formal evaluation entries.
Within an entry, run all paired cases with a fixed declared batch size, default 256.

Training error distributions affect training, while explicit case metadata controls
evaluation error. Clean-trained checkpoints must be tested on the SAME corrupted
cases. Keep their own protocol/normalizer/shape; never use `observation_sensor=None`
for the clean-trained final test. Use `allow_config_mismatch` only for a declared
transfer/intervention, accompanied by the exact difference and rationale; do not
silence checkpoint/config errors indiscriminately.

Final main matrix:

- Six deterministic baselines above, all 2,600 cases each.
- All 23 learned runs, selected and final checkpoints, all 2,600 cases each.
- Scheduled total **135,200 episodes** = (6 + 23 x2) x2,600, excluding validation,
  development, negative controls, repeatability, replay and videos. If baseline
  definitions coincide, record aliases and reuse identical data with hashes; do not
  count aliases as independent evidence. Logical matrix counts remain explicit.
- Preserve step-0 validation and at least the first five cases per final condition
  per distinct profile for zero-policy verification; label these controls separately.

Create `configs/v3/final_matrix_index.json` using the schema in
`scripts/v3_analyze.py`. Include exact raw-file hash, family, seed, selected/final/
baseline role, entry ID, suite/config/controller/checkpoint hashes, source SHA and
clean-source flag. Each baseline uses seed=null and role=baseline. Include a separate
case/suite manifest and declared entry/job count manifest. Verify indices reference
all 23 selected/final/periodic checkpoint families and no missing files.

Store terminal outcomes plus physical and sensor parameters, reset attempts/validity,
success/drop/collision/timeouts, completion and release times, contact phases,
independent hold, residual magnitude/changes, requested/executed targets, clipping,
geometry saturation, reward components, hashes and lineage. For selected traces,
also store true/raw/estimated/controller object position, estimated velocity,
sensor frame/seed, gripper states and forces. Truth is diagnostic only at inference.

Main final jobs must reconcile 100% of scheduled case IDs with no duplicates,
unexpected IDs, unresolved infrastructure errors or invalid resets. Fix underlying
engineering and rerun the same cases when justified; do not resample/eject hard
starts. If a physical case cannot be initialized validly, report an incomplete gate
and denominator explicitly rather than manufacturing a complete table.

## 9. Analysis, mechanisms and repeatability

Run CPU analysis:

```bash
python scripts/v3_analyze.py --index configs/v3/final_matrix_index.json \
  --root . --output results/v3/summary
```

Extend the provided script to produce required plots and additional descriptive
metrics; keep its input-hash and case reconciliation checks. Report per seed and
per condition: success, drop, collision, gate timeout, episode timeout, completion
time among successes, release delay, residual magnitude, clipping/saturation and
compute cost. Keep scheduled-case and valid-reset denominators explicit.

Primary contrasts, selected checkpoints on `mixed_id` only:

1. combined_robust_history minus combined_robust_ff.
2. combined_robust_history minus geometry_best_constant.

Report effect sizes in percentage points, per-seed values, 95% paired bootstrap CIs
and 97.5% individual intervals for the two-comparison Bonferroni family. Resample
training seeds and shared `base_case_id` clusters; keep paired conditions together
for averages over severities. Deterministic baselines are not extra training seeds.
Use 10,000 bootstrap replicates with seed 6455401. Five seeds still limit precision;
bootstrap intervals are not proof of universal superiority. Treat repeated identical
clean initializations as a reliability check without a binomial population claim.

Secondary contrasts: robust FF vs clean FF, residual-history vs nominal, history vs
geometry_common, and history vs repeated-current on matching seeds 11/22/33. Final
checkpoints, individual severity curves, mixed OOD and nonclean equal-condition
averages are secondary/descriptive. No post-hoc claim that the best-looking
condition was the primary hypothesis. If final data drive a new design, label it
exploratory and freeze a fresh study/suite before confirmatory claims.

Required mechanism analysis:

- Plot commanded residual against true error, observed error, contact phase and
  time; fit/describe constant-bias versus state-dependent behavior per seed.
- Decompose approach/hold/terminal/action penalties; quantify geometry clipping and
  whether residual commands have physical authority. Compare successful and failed
  paired cases without selecting only attractive examples.
- Compare EMA and giver-reference baselines, and real versus repeated-current
  history. Explain whether gains come from filtering, rigid-grasp inference,
  temporal information, or simply a constant insertion offset.
- On a predeclared 65-case subset (first five cases by ID from each condition),
  evaluate selected history policies with temporal frames permuted using the fixed
  oldest-to-newest permutation [4,2,0,3,1] and with previous frames replaced by current. These inference-time
  interventions are distribution shifts, not causal proof; the trained repeated-
  current control is the stronger memory comparison. Add the intervention hook
  before experiment freeze and keep raw results separate from the primary matrix.

Repeatability: on the same 65-case subset, rerun geometry_common,
geometry_best_constant and the five selected history policies in three fresh
process seeds {6455601,6455602,6455603} and batch sizes {1,23}. This is 2,730 episodes
(7 x65 x3 x2). Record sensor-stream equality separately from terminal/success
agreement and paired effect stability. Average within-case/process repetitions
before seed-level inference; do not treat repeated processes as extra training
seeds. This is a sensitivity check on existing cases, not new held-out evidence.

## 10. Secondary physical transfer (development-gated)

Prioritize the main uncertainty study. After main acceptance and a throughput
estimate, perform a bounded transfer check if feasible: single-factor mass,
friction, bar length and width changes at the multipliers in the draft config, plus
one joint combination fixed before test (at most nine cells, 100 paired cases each).
No additional training is required. Use geometry_common, geometry_best_constant
and the five selected robust-history policies (maximum 6,300 episodes).

First verify physical feasibility on separate development starts. Scene spawn
size/mass/material, inertia, grasp transforms, reset poses and collision geometry
must all actually change consistently. The existing `object_size` task field alone
does NOT guarantee changed simulator geometry: implement and validate proper spawn
overrides before claiming this extension. Record actual spawned dimensions/mass/
friction, jaw clearance and valid resets. Hold an actual valid giver grasp; do not
silently exclude difficult outcomes. Add the transfer implementation before freeze
if doing it. Report known object geometry to controllers as an explicit assumption.

This is secondary zero-shot simulator transfer with privileged dimensions, not
unseen-category dexterous generalization. If infeasible within the measured budget,
write `not_performed` with evidence in status/report; do not claim it as a completed
experiment. It does not block completion of the mandatory uncertainty study.

## 11. Report, slides and videos

Write a standalone English final report in `report/v3/report.md` and PDF. Explain
the original question, v1/v2 findings and why v3 follows, hypotheses, exact task,
sensor equations, input information, fair baselines, training/split/selection rules,
counts, metrics/uncertainty, main/secondary results, mechanisms, repeatability,
compute, limitations and reproducibility. Clearly separate previous studies,
development findings and new held-out results. Include real references and disclose
AI-assisted implementation. Cite the official installed simulator documentation
and relevant primary residual-RL/handover research; verify bibliography metadata.
Never claim that a synthetic translation sensor is real vision or sim-to-real.

Required figures: pipeline/data-access diagram, validation learning curves, severity
curves with per-seed points, main paired effects, failure breakdown, representative
raw/filtered/true trajectories and residual/contact traces. Required tables: full
counts, hyperparameters/budgets, baseline search/selection, selected vs final,
per-seed results, repeatability, artifact inventory and limitations.

Create a presentation (`report/v3/slides.pptx` and PDF, approximately 12-16 slides)
and concise speaker notes. Render report/slides and visually inspect EVERY page;
fix clipped plots/tables, tiny labels, incorrect numbers, broken citations and links.
Keep editable sources and figure scripts. Include a traceable number-audit file
mapping report/slide numeric claims to generated tables; no invented placeholders.

Videos must follow a frozen selection rule: first success and first failure by
case ID in `mixed_id` and `mixed_ood` for the main comparison, plus one clean
baseline, one severe-noise example, and one giver-reference comparison. Reuse an
identical case for side-by-side methods. If no failure exists, state that and do
not substitute a fabricated failure. Target 8-12 distinct clips plus a short montage.
Every clip needs run/case/method/seed/checkpoint/config/source hashes, original
evaluation and replay outcome, camera, control/playback rates, and selection rule.
If replay differs, retain/disclose both outcomes. Use separate recording processes
for different observation shapes/estimators; the old video plan cannot switch
these safely at runtime. Verify every MP4 decodes and has visible robot contact.

## 12. Publication contract: every result and checkpoint

Publish source on `study/v3-observation-robustness`; preserve the v2 branch. Push
the immutable `experiment-v3` source tag and a new delivery tag **`v3.0.0`**. If a
tag/release already exists, verify it; never overwrite it. Publish a patch release
for necessary delivery fixes and retain the superseded release with an explanation.
Do not merge into main unless separately requested.

Required Git content:

- Source/tests/scripts; frozen training/controller/evaluation configs and suites;
  baseline selection, protocol freeze and version lock; exact reproduction commands.
- Small results/plots/tables, report/deck sources, decisions, acceptance/verification
  evidence, full run/checkpoint/video indices, final status and release notes.
- `docs/v3/REPRODUCE.md`: clean-clone setup, download/checksum/extraction, a tiny
  replay, complete evaluation, raw-to-table regeneration, video replay and resume.
  Commands must refer to immutable experiment and delivery versions with relative
  paths; no dependence on an ephemeral remote directory or the owner's computer.

Required Release assets (split archives below GitHub size limits, no credentials):

| Asset group | Required content |
|---|---|
| Source/configs | exact experiment source archive, delivery source, frozen configs/suites, locks, manifests |
| Checkpoints | EVERY saved checkpoint for all formal and pilot/smoke/resume runs: step0, periodic, selected, final, latest, optimizer/critic/normalizer/RNG/counters; retention/alias ledger |
| Raw experiments | all development, validation, selection, final, interventions, repeatability, negative controls, transfer if performed; failed/invalid/resumed records included |
| Logs/traces | stdout/stderr, PPO/TensorBoard logs, reward components, representative traces, complete run metadata and job ledger |
| Analysis | generated tables/figures, analysis inputs/index, plots/scripts, provenance and number audit |
| Documents | report MD/PDF, editable slides PPTX/PDF, speaker notes, reproduction guide |
| Videos | individual MP4s, montage, sidecars, selection plan and video index |
| Integrity | release manifest, file checksums, archive member sizes/SHA-256, run/checkpoint/video indices |

Archive all saved checkpoints, not just the best one. Identical bytes may be stored
once if an explicit alias ledger maps every original run/role/path to the retained
member and hash. Do not silently prune periodic or failed-run checkpoints. Never
claim a file exists merely because a ledger mentions it. Publish logs and raw
records, including negative findings; remove credentials/private machine paths from
new public metadata without changing scientific content.

`release_manifest.json` must map every logical run and artifact to an asset/member,
byte size, SHA-256, source/config/suite/checkpoint lineage, and status. Include a
complete archive-member inventory, including the source archives. `SHA256SUMS`
covers every asset except itself; the manifest/checksum file must not self-hash in
a recursive loop. Describe coverage explicitly. Existing v2 releases may be linked
as prior work; v3 must be independently reproducible from its own assets/source.

GitHub CLI example (after preparing a complete reviewed asset directory):

```bash
git push origin study/v3-observation-robustness
git push origin experiment-v3
git tag v3.0.0 DELIVERY_COMMIT
git push origin v3.0.0
gh release create v3.0.0 --repo ywen0511/CSCI645-Project \
  --verify-tag --title 'V3: observation robustness in bimanual handover' \
  --notes-file docs/v3/RELEASE_NOTES.md release_assets/v3/*
```

Replace `DELIVERY_COMMIT` with the verified concrete commit. Check `gh release view`
first so an existing release is not overwritten. Generate a complete file list
when shell argument limits apply. Credentials must be supplied by the remote
environment, never committed or requested as plain chat text.

## 13. Fresh verification and definition of done

Use a NEW directory and public release URLs, not your original training files.
Clone the delivery tag, download ALL assets, verify checksums and member inventories,
extract safely, and resolve every index entry. Confirm all 23 formal runs and all
saved checkpoints, selected/final mappings, raw-case counts and rendered documents.

Regenerate every reported table from downloaded raw records and compare numeric
values exactly or under explicitly justified floating tolerances. Regenerate
figures and inspect them. Re-run the documented quickstart and the predeclared
65-case replay for geometry_common, geometry_best_constant and all five selected
history policies. Report agreement and all mismatches; do not promise perfect
PhysX determinism. Reload all distinct formal checkpoint architectures and test
one downloaded resumable checkpoint for two iterations in a disposable directory;
verify counters/optimizer/normalizer and unchanged original file hashes.

Record commands, exit codes, source/runtime hashes, file counts, discrepancy tables
and public asset URLs in `docs/v3/VERIFICATION.md` plus machine-readable JSON.
If publication verification fails, correct the delivery and publish a new version;
do not mark complete while any mandatory asset/check remains missing.

Completion checklist:

- [ ] Remote sensor/physics/PPO acceptance passed with evidence.
- [ ] Development decisions and immutable final protocol/source recorded.
- [ ] All 23 required training runs and checkpoint validation/selection completed.
- [ ] Full main evaluation reconciled, negative controls and repeatability passed.
- [ ] Memory control and declared interventions analyzed; negative results retained.
- [ ] Optional physical transfer completed OR explicitly documented as not performed.
- [ ] Report, slides, figures and videos built, checked and numerically audited.
- [ ] All code, raw results, logs, checkpoints, indices and checksums published.
- [ ] Fresh download, table regeneration, replay and resume verification completed.
- [ ] `V3_STATUS.json` complete=true only after the above; no required active jobs.

Final response must provide clickable links to the branch, immutable experiment
commit/tag, final release, report, slides, summary metrics, checkpoint index and
assets, video index, and verification report. State actual findings and limitations,
not an assumed RL victory. List every incomplete mandatory item if blocked. The
owner should not need to reconstruct commands, find a checkpoint on a remote disk,
or supply another instruction to finish publication.
