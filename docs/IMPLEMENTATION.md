# Implementation contract

## Project layout

Generate an external project using the selected Isaac Lab version's official template. The simulator-specific package does not exist in the initial handoff. Preserve these documents and add implementation in a structure such as:

```text
src/csci645_handover/
  tasks/handover_env.py
  tasks/handover_env_cfg.py
  controllers/nominal.py
  controllers/geometry.py
  observations.py
  rewards.py
  outcomes.py
  case_suites.py
  agents/ppo_cfg.py
scripts/
  doctor.py
  run_scripted.py
  train.py
  evaluate.py
  record_video.py
  analyze.py
  run_experiments.py
  package_release.py
tests/
configs/frozen/
results/summary/
report/
```

This is a responsibility map, not a requirement to duplicate upstream runners. Thin wrappers around official training/play runners are preferable when they preserve this interface. Create package registration, dependency metadata, and tests appropriate to the pinned Lab release. Keep pure geometry, timers, case generation, and metrics independently testable without launching Isaac Sim.

## Component behavior

### Environment

The environment owns batched assets, valid reset settling, scene observations, action execution, reward, terminations/truncations, and per-environment state. Use explicit masks for environment-specific resets. Stable-contact dwell, independent-hold time, release-request flags, anchors, and trajectory progress must reset correctly for a subset of environments.

Use the installed SDK's contact-reporting configuration and per-finger, object-filtered sensors. Check that the sensor actually reports nonzero contact on the target object and does not accept table/link contact as grasping. Validate contact data in an isolated grasp before relying on it in release or success logic.

### Controller composition

Separate nominal trajectory generation, learned residual, optional geometry, common safety limits, and low-level IK. Store intermediate outputs in telemetry. The controller receives current observations and per-environment time; it must not inspect held-out labels or case seed to choose actions.

Run no-policy controllers through the same environment with zero residual. Do not create a simpler evaluation-only simulator for nominal/geometry. Contact-gated release belongs only to the geometry-enabled methods.

### Training integration

Use PPO's existing runner. Provide full method-specific config resolution, deterministic seeding where supported, observation normalization, finite-value checks, periodic checkpoints, validation callback, logging, and resume. Record nondeterministic GPU behavior rather than promising bitwise reproducibility.

Each checkpoint should contain or reference policy/value parameters, optimizer, normalization state, scheduler, RNG states, training transition counter, curriculum position, and resolved configuration. If the library cannot restore in-progress simulator state, resume at explicit episode boundaries and document that it is an approximate training continuation, not bitwise replay.

### Evaluation and analytics

Use an independent outcome evaluator, frozen normalization, no exploration, explicit case records, and append-safe raw JSONL/CSV. On restart, check existing records against run/config/checkpoint hashes. Never silently combine different models into one run ID. Recompute all tables and figures from raw episode records using the checked-in analysis script.

## CLI to implement

The following are **target command interfaces, not commands that already work in the handoff**. Wrap each with the installed version's required Python/application launcher, and replace this section with exact tested invocations once implemented. `--help` must explain units, outputs, and defaults.

| Entry point | Required capability |
|---|---|
| `doctor.py --output outputs/preflight.json` | Hardware, versions, backend, asset availability, smoke results, no secret values |
| `run_scripted.py --method nominal --num-envs 1 --episodes 20 --output outputs/baseline` | Repeatable no-learning control, raw outcomes and optional video |
| `train.py --method combined --seed 11 --protocol configs/frozen/protocol.json --output outputs/combined_seed11` | Train to frozen budget; support `--resume CHECKPOINT` |
| `evaluate.py --method combined --checkpoint PATH --suite PATH --output PATH` | Evaluate exact case list and checkpoint; support deterministic resume by case ID |
| `record_video.py --run-index PATH --run-id ID --case-id ID --output PATH` | Reproduce a recorded case and record provenance |
| `analyze.py --run-index PATH --output results/summary` | Validate counts and generate metrics/figures from raw records |
| `run_experiments.py --protocol PATH --output PATH --resume` | Execute all required runs and evaluations with a persistent ledger |
| `package_release.py --run-index PATH --output release_assets` | Gather deliverables, indexes, hashes, and release notes without inventing absent files |

Expose a tiny smoke profile separate from final configurations. All output paths should be relative or user-specified. Never embed the owner's desktop path or a particular remote account name.

## Required tests and simulator checks

Pure logic checks:

- Frame transformations round trip and grasp targets transform correctly for both bases.
- Residual bounds hold; zero residual matches nominal; repeated actions do not accumulate offsets.
- Release timing sign, waiting cap, and contact dwell obey physical time.
- The two-second success timer resets on loss of independent support and cannot pass while giver/table support exists.
- Partial resets do not reset unrelated environments or retain stale anchors.
- Ablation masks exactly the four explicit phase channels before normalization; other inputs/actions/reward remain identical.
- Fixed case generation is repeatable and splits do not overlap.
- Outcome precedence, null-valued unsuccessful completion times, duplicate detection, and count reconciliation behave correctly.

Simulator checks on the actual remote environment:

- Verify physical grasp without hidden attachments; opening giver fingers with no receiver causes a drop.
- Verify both receiver fingers' object contacts and correctly reject table-only contacts.
- Observe nominal successful transfer and injected early-release/misalignment failures on development cases.
- Check subset resets in a batch, contact stability, finite states, collision masks, and equivalent single/batched behavior within documented numerical tolerances.
- Short PPO run produces finite losses, nonzero policy updates, correct bounded targets, and save/load/resume behavior.
- A selected checkpoint loaded in a new process reproduces evaluation rates within the stated tolerance; normalization and observation ordering are restored.

Source checks and mocked physics do not satisfy simulator acceptance gates. Store command, exit status, version, timestamp, and log path for each gate.

## Development discipline

Maintain readable English logs and configuration names. Avoid a large untested code dump. Run the scene and controller at each stage, inspect actual videos/contact traces, fix problems, then scale. Capture exceptions with traceback and failed-run status. Save before scheduler preemption and handle resumable work explicitly.

Once final experiments begin, changes affecting physics, reset, reward, observations, action, geometry, or evaluator require a new experiment version and consistent reruns. Reporting-only fixes can use a later analysis commit, but record both experiment and analysis commit SHAs.
