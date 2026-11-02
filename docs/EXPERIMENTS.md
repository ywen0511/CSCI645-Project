# Experiment protocol

## Status and freezing

`configs/protocol.json` provides concrete pilot defaults. Its values are not measured facts or mandatory optimal hyperparameters. Calibrate scene dimensions, reachable perturbations, contact thresholds, and reward scales using development data. Then write a fully resolved config, its SHA-256, a protocol-freeze entry in `docs/DECISIONS.md`, and an immutable source commit before final experiments. Store final configs under `configs/frozen/`.

Keep the core question, methods, fixed-orientation scope, physical-parameter controls, and independent two-second success definition. If engineering evidence requires another timing/range/budget, document the reason before test evaluation and apply it consistently. Do not tune perturbations to make a preferred method win. A different physics backend or simulator is a scope change, not a hidden implementation detail.

## Methods

| ID | Geometry | Learned residual | Explicit contact-phase channels | Train? |
|---|---|---|---|---|
| nominal | Off | Zero | N/A | No |
| geometry | On | Zero | N/A | No |
| residual | Off | PPO | Present | Yes |
| combined | On | PPO | Present | Yes |
| combined_no_phase | On | PPO | Zeroed | Yes |

Train the three learned methods separately. A residual-only checkpoint inserted into geometry without retraining is not the combined method. The ablation must be trained with its phase input removed, not only masked at test time. Geometry parameters are identical in `geometry`, `combined`, and the ablation.

All trained methods use the same observation design except the declared ablation, identical network size, action bounds, reward implementation, curriculum, environment-transition budget, evaluation conditions, and low-level controller settings. Keep the input dimensionality fixed by zeroing the phase channels. All methods use the same physical state/contact access appropriate to their controller; nominal intentionally follows its fixed script. Report that geometry is a state-feedback controller, not an information-free baseline.

## Training defaults and resource management

- PPO through the pinned Isaac Lab integration, preferably RSL-RL; actor and critic MLPs start at two 128-unit layers.
- Initial PPO candidates: learning rate 3e-4, gamma 0.99, GAE lambda 0.95, clipping 0.2, 5 optimization epochs, 4 minibatches, 32 control steps per rollout. Treat these as pilot values and respect the runner's supported semantics. Record entropy coefficient, KL schedule, action standard deviation, observation normalization, value normalization, and timeout bootstrapping explicitly.
- Start with 1 environment for visual debugging, then 16 for reset isolation, then 64 for a training smoke test. Benchmark 256 or more only as memory and throughput permit. Parallel-environment count is not a scientific goal.
- Final default: 10 million **environment transitions** per run, seeds 11/22/33, three learned methods = nine final runs and 90 million transitions. Count transitions over all environments; never confuse vector steps, optimizer updates, physics substeps, and environment transitions.
- Freeze the same rollout batch size for all final learned methods. Round the common transition budget up to a full rollout batch and report the realized value. Use the same evaluation intervals up to one-rollout rounding.
- Pilot budget: at most 15 million transitions total across methods before a resource-plan review. Log every pilot, including failed attempts; tuning cost is separate from final budget.
- Benchmark wall time and VRAM, estimate full training and evaluation cost, and fit it within the available machine allocation. If the default is infeasible, set a lower common budget with evidence **before final runs**, record it as a protocol deviation, and report it prominently. Do not quietly omit seeds or the ablation.
- Use the fixed transition-based curriculum in the JSON, not method-specific performance-triggered curricula. Final training distribution is per-axis uniform translation in +/-1 cm and uniform release offset in +/-0.15 s. Orientation and physical parameters remain fixed.
- Timeouts are truncations for value bootstrapping where appropriate; drops and other task-ending failures are terminal. Verify the RL wrapper's terminal-observation handling.

## Data generation and separation

No external dataset is required. The simulator generates online PPO transitions. Archive reset definitions, random seeds, run configurations, normalization, scalar metrics, and selected traces; full per-step PPO rollouts need not be retained unless used in reported analysis.

Three independent suites:

1. **Development:** seed 6452028; used for controller calibration and debugging, never advertised as held-out test results.
2. **Validation:** seed 6452027; 100 fixed cases sampled from the final training distribution, used for checkpoint selection. Do not include stress conditions. Store explicit sampled perturbations and case IDs.
3. **Final evaluation:** seed 6452026; 200 scheduled cases per condition in the JSON, nine conditions = 1,800 cases per policy/controller. Sample each position axis independently uniformly within its bound; timing is the signed fixed offset specified by each condition. Save the realized case list before final training. Inspect feasibility using development cases of the same ranges, not policy performance on held-out cases.

Generate explicit JSONL case files with `case_id`, condition, displacement vector, release offset, initialization seed, object/config identifiers, and suite version/hash. Use disjoint case IDs and RNG streams. Each method and training seed receives the same final case list. Do not depend on vector-environment scheduling to reproduce randomness; initialize each case from its own RNG state. A clean condition can be deterministic; acknowledge repeated identical cases and do not claim they provide 200 independent perturbation samples.

In-range and stress conditions must remain separate in tables. Do not average them together into an unlabeled headline number. If the +/-2 cm stress bound overlaps the training support, call it an expanded-range stress distribution, not exclusively out-of-distribution samples. Fixed orientations limit what conclusions can be drawn.

## Validation and checkpoint selection

Evaluate the untrained policy and then every 2 million transitions through the final budget on the fixed validation suite. Freeze normalization and disable exploration during evaluation. Preserve the final checkpoint regardless of whether it is selected.

Select the checkpoint with highest validation success rate; ties use lowest validation drop rate, then earliest training step. Use this exact rule for all nine runs. Store every candidate's validation results and selection rationale. Do not choose a checkpoint using final test success or a visually attractive demo.

For learning curves, plot validation success and drop rates against environment transitions with all seeds and an aggregate. Keep training reward curves separate from task-success curves. Checkpoints should be saved at least every million transitions and on clean interruptions, with rollout rounding documented. Keep selected, final, and an appropriate resumable checkpoint for every final run; archive all final-run periodic checkpoints if storage permits, otherwise provide a complete retention ledger and preserve every checkpoint used in any reported result/video.

## Final evaluation matrix

Run two deterministic controllers once per case and the three selected learned methods for each of their three training seeds. The default matrix has `(2 + 3*3) * 9 * 200 = 19,800` episodes, excluding reset retries and validation. Use the same fixed physics/control frequency and no policy exploration. Rendering should not change control timing or randomization.

Required episode fields:

`run_id`, `method`, `training_seed` (null for deterministic controllers), `case_id`, `condition`, `suite_hash`, `config_hash`, `source_commit`, `checkpoint_sha256` (null for deterministic controllers), `requested_offset_xyz_m`, `realized_offset_xyz_m`, `release_offset_s`, `reset_attempts`, `reset_valid`, `success`, `drop`, `collision`, `collision_count`, `terminal_reason`, `completion_time_s` (null on failure), `episode_duration_s`, `release_request_time_s`, `release_command_time_s`, `giver_contact_end_time_s`, `receiver_stable_time_s`, `independent_hold_s`, and diagnostic flags for misalignment/premature release/conflicting motion. Encode unavailable values as null, never fake zeros.

Record simulation errors and invalid initializations separately with traceback/log references. They must not disappear from a count reconciliation table. Resume evaluation by unique `(run_id, case_id)` and reject duplicates. Verify intended and completed counts before reporting success rates.

## Metrics and uncertainty

- Success and drop rates using the declared valid-episode denominator; also report scheduled cases, invalid resets, and infrastructure errors.
- Collision episode rate and event count, with the contact rule stated.
- Completion time among successful episodes, with successful sample count; do not treat failed trials as zero-time successes.
- Release delay relative to request, timeout rate, and diagnostic failure breakdown.
- Learning curves against training transitions, plus runtime/throughput and training resource consumption.
- Per-seed results and mean/standard deviation across the three learned-policy seeds. Three seeds offer limited precision; do not imply otherwise.
- For per-policy binomial rates, Wilson intervals are a reasonable default when cases are independent. For paired method differences, use shared case IDs and a paired bootstrap; preserve training-seed grouping for learned methods. Document the resampling unit and bootstrap seed. Do not pool all episodes as independent training replicates or duplicate deterministic baseline runs to manufacture seed variance.

Primary comparisons: combined vs nominal, combined vs geometry, combined vs residual, and combined vs combined_no_phase for each condition. Report effect sizes and uncertainty; avoid claims of significance unsupported by the design. Include a raw counts table so percentages can be regenerated.

## Failure inspection and videos

Preserve time-series traces for representative successes and failures, including contact forces, relative poses, targets, residuals, phase, gripper commands, release request/command, and holding timer. Render a clean baseline demonstration, examples for each method under a shared perturbed case, at least one position-error failure, one premature-release failure, and any observed conflicting-motion failure. If a category never occurs, report that rather than fabricate it.

Choose videos with a declared rule, such as first success/failure by case ID in each category. Record run ID, case ID, checkpoint hash, config hash, method, perturbation, playback speed, and outcome in a video index. Videos illustrate behavior; the full evaluation table supports performance claims.

## Reporting negative results

Geometry alone may be sufficient, the residual may not improve success, or the ablation may have negligible effect. These are valid findings. Examine physical feasibility, reward exploitation, observation sufficiency, geometry saturation, and residual authority using development/validation evidence. If a post-test change is scientifically necessary, label the existing results exploratory and create a new frozen protocol and fresh held-out suite rather than presenting tuned-on-test results as confirmatory.
