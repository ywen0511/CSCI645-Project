# Robust Bimanual Handover

**Geometric Coordination and Residual Reinforcement Learning for Robust Bimanual Handover**  
CSCI 645 Robot Manipulation, Fall 2026 · Yan Wen

## Remote agent: your complete assignment starts here

**When the owner asks you to execute this README, complete this project end to end: implement it, run the experiments, analyze the results, write the report, and publish the source and all required artifacts in GitHub Releases.** Reading this README is the only entry point the owner needs to provide. Follow the repository links below yourself; do not ask the owner to paste the linked files, explain previous conversations, or provide local desktop content.

This README is an execution brief, not a request to produce another plan. The linked specifications are part of the assignment and must be read before their corresponding implementation stages. Do not stop after summarizing the repository, writing a scaffold, passing CPU checks, starting training, or uploading a demonstration. Finish the acceptance checklist below, or identify a concrete external blocker and preserve all completed work.

The owner authorizes routine implementation and debugging, dependency setup in an isolated environment, experiments on already available compute, project commits and pushes, tags, and publication of project checkpoints/results/releases to **`ywen0511/CSCI645-Project`**. Routine steps do not require repeated approval. This does not authorize paid resource provisioning, account/security changes, changes to repository visibility, destructive changes to unrelated data, or replacement of published history/releases.

All code documentation, logs intended for delivery, reports, release notes, and progress updates must be in English. Use the available remote GPU and credentials; discover hardware and version details through preflight. Missing compatible compute, asset access, or write/release permissions must be reported precisely. The README supplies assignment context, not credentials or computing resources.

## Current status

**Completed (November 2026).** The project was implemented, run and published end to end:

| Deliverable | Location |
|---|---|
| Final release (checkpoints, raw results, logs, configs, videos, report, checksums) | [v1.0.0](https://github.com/ywen0511/CSCI645-Project/releases/tag/v1.0.0) |
| Experiment source (all final runs) | tag [`experiment-v1`](https://github.com/ywen0511/CSCI645-Project/tree/experiment-v1) |
| Final report | [report/report.md](report/report.md) · [report/report.pdf](report/report.pdf) |
| Result summaries (tables, CSVs, figures) | [results/summary/primary](results/summary/primary/tables.md) · [secondary](results/summary/secondary/tables.md) |
| Checkpoint index / video index | release assets `checkpoints.json`, `videos.json`; [results/videos](results/videos) |
| Setup / reproduction / decisions | [docs/SETUP_REMOTE.md](docs/SETUP_REMOTE.md) · [docs/REPRODUCE.md](docs/REPRODUCE.md) · [docs/DECISIONS.md](docs/DECISIONS.md) |
| Release verification record | [docs/RELEASE_VERIFICATION.md](docs/RELEASE_VERIFICATION.md) |

Platform: Isaac Lab v3.0.0 + Isaac Sim 6.2.0.0 (PhysX backend), RSL-RL 5.5.1 PPO, NVIDIA A100-40GB.
Nine PPO runs (3 methods x seeds 11/22/33, 10,027,008 transitions each) and 19,800 final-evaluation
episodes (0 invalid resets, 0 infrastructure errors).

**Main findings (held-out final suite; success rate, mean over seeds).**

| | nominal | geometry | residual | combined | combined_no_phase |
|---|---|---|---|---|---|
| in-range conditions (1,400 cases) | 95.5 % | 100.0 % | 99.9 % | 100.0 % | 100.0 % |
| stress conditions (400 cases) | 47.8 % | 93.3 % | 52.9 % | 94.5 % | 95.2 % |

* The training-free geometry module is decisive (+45.5 points on stress cases, all drops removed).
* combined vs geometry: +1.2 points [-4.3, +5.4] (no detectable gain); trained final checkpoints
  (secondary analysis): -3.4 [-6.3, -1.1]. The phase-label ablation has no detectable effect.
* Validation (drawn from the training distribution) was saturated by geometry, so the frozen selection rule
  chose the untrained step-0 policy for 8 of 9 runs; see report Section 7 and docs/DECISIONS.md.

The original execution brief follows unchanged below.

## Objective

Determine whether explicit geometric coordination and a bounded learned position residual improve simulated two-arm object handover under spatial and release-timing perturbations. Compare nominal control, geometry alone, residual learning alone, and their combination, plus an ablation removing the combined policy's explicit contact-phase input.

Use **two Franka arms, each with a two-finger parallel-jaw gripper**, one rigid object, fixed orientation targets, low-dimensional simulator state, Isaac Sim through Isaac Lab, and PPO. This is not a dexterous-hand reproduction project. A positive result is not required; a reproducible, fair comparison is required.

## Start here

1. Read [AGENTS.md](AGENTS.md) and [the remote-agent assignment](docs/REMOTE_AGENT_PROMPT.md).
2. Read the unchanged [original proposal](proposal/CSCI645_Project_Proposal_YanWen.pdf), also available as [extracted text](proposal/proposal.txt).
3. Read [task specification](docs/PROJECT_SPEC.md), [implementation plan](docs/IMPLEMENTATION.md), and [experiment protocol](docs/EXPERIMENTS.md).
4. Establish the remote environment following [environment requirements](docs/ENVIRONMENT.md).
5. Execute the [milestones and runbook](docs/RUNBOOK.md), then satisfy the [release contract](docs/RELEASE.md).

The [machine-readable protocol](configs/protocol.json) defines proposed defaults. The remote agent must validate physical thresholds during pilot work and freeze the resolved protocol before final training. All changes go into [the decision log](docs/DECISIONS.md). [Status](STATUS.json) records actual progress.

## Execute these stages without waiting for another task prompt

| Stage | Work to complete | Evidence required before advancing |
|---|---|---|
| 0. Preflight | Inspect hardware, asset access, GitHub permissions, and compatible Isaac Sim/Lab versions; pin the environment and run official control and short training examples. | Exact working setup commands, versions, backend, hardware inventory, and logs. |
| 1. Scripted handover | Build the external Isaac Lab task with two Franka parallel-jaw grippers, a physically established giver grasp, receiver approach/closure, fixed-time release, giver retreat, and outcome detection. | Repeated clean handovers, actual contact traces, a full video, negative controls, and independent batched resets. |
| 2. Geometry | Implement relative-target correction, shared-holding coordination, and contact-conditioned release gating with a bounded wait. Add feasible initial-position and release-time perturbations. | Development-only comparisons and traces confirming geometry is absent from the nominal baseline. |
| 3. Residual PPO | Add a bounded three-dimensional receiver position residual, state observations, shared rewards, PPO training, validation, save/load/resume, and the contact-phase-input ablation. | Finite short training runs, correct action bounds, meaningful policy authority, and verified checkpoint reload. |
| 4. Freeze and train | Calibrate using pilot data, benchmark resources, freeze source/configuration/case suites, and train all learned methods with matched budgets and three seeds. | Nine completed run records, validation history, selected/final/resume checkpoints, and config/source hashes. |
| 5. Evaluate and report | Evaluate every required controller/policy on the same held-out cases; analyze success, drops, learning curves, completion time, collisions, and failure modes. Write the final English report and record indexed videos. | Reconciled raw episode data, per-seed/aggregate summaries, uncertainty, reproducible figures, Markdown/PDF report, and video provenance. |
| 6. Publish and verify | Push source and small summaries, tag the experiment source, package all artifacts, upload a draft GitHub Release, download it afresh, check hashes and replay, then publish it. | Verified downloadable checkpoints/results/logs/configs/report/videos, clean-clone reproduction, final release URLs, and truthful completed status. |

Use the detailed [runbook](docs/RUNBOOK.md) for each gate. Choose routine engineering details autonomously, record evidence-backed decisions, and continue. If interrupted, save supported checkpoint state and exact resume commands, update the run ledger and `STATUS.json`, and resume outstanding stages on continuation. Do not assume a background job completed successfully without collecting its outputs.

## Scientific contract at a glance

| Method | Geometry | Residual policy | Training |
|---|---|---|---|
| `nominal` | Off | Zero | None |
| `geometry` | On | Zero | None |
| `residual` | Off | PPO, explicit contact phase available | Three seeds |
| `combined` | On | PPO, explicit contact phase available | Three seeds |
| `combined_no_phase` | On | PPO, only the explicit phase channels zeroed | Three seeds |

- Use Isaac Sim through Isaac Lab with a fixed PhysX backend; use one centralized policy, fixed orientation targets, and online simulated experience. No external demonstration dataset is required.
- The residual is a bounded offset from the current nominal receiver position target, not an accumulated displacement. Its initial bound is 0.02 m per axis. Gripper commands and giver motion remain scripted or geometry-governed.
- Keep mass, friction, geometry, physics/controller settings, rewards, evaluation code, and training budgets controlled across methods. Train the three learned methods separately.
- Primary spatial perturbations are initial translations with fixed object orientation. Preserve a valid initial giver grasp and ensure the displacement persists into receiver approach.
- Without geometry, release commands remain at their perturbed scheduled times. Geometry may defer release after the request when receiver stability is insufficient, with a finite wait cap.
- Success requires two continuous seconds of receiver-only holding after giver release, without giver or table support. Contact alone is insufficient. Log invalid resets and infrastructure failures separately; do not silently discard difficult cases.
- The ablation removes only the explicit contact-phase label, retaining raw contact observations and geometry access to contacts. Train with the mask; do not merely mask a full-input policy at test time.
- Default final training is 10 million environment transitions per run with seeds 11, 22, and 33; nine learned runs total. Pilot defaults must be physically validated and resource-budgeted before freezing. Any common-budget adjustment must be recorded before final training.
- Default held-out evaluation has nine conditions: clean, in-range position, expanded-range position, early/late in-range timing, early/late in-range joint perturbations, and early/late expanded-range joint perturbations. Use 200 cases per condition, shared across methods and seeds: 19,800 final evaluation episodes in total.
- Select checkpoints using fixed validation cases only. Report per-seed results, uncertainty, negative findings, and failures. An improvement by the combined method is a hypothesis, not a required result.

For exact perturbations, schedules, observation semantics, selection rules, and data fields, read [PROJECT_SPEC.md](docs/PROJECT_SPEC.md), [EXPERIMENTS.md](docs/EXPERIMENTS.md), and [protocol.json](configs/protocol.json). These detailed definitions control implementation; this overview must not be used to skip them.

## Commands available in this initial handoff

```bash
python3 scripts/check_handoff.py
python3 -B -m unittest discover -s tests -v
python3 scripts/verify_release.py --help
```

These commands validate the specification or a release inventory; they do not run robotics experiments. The remote agent must implement and document the simulator commands specified in [IMPLEMENTATION.md](docs/IMPLEMENTATION.md). Do not substitute successful document validation for successful simulation or training.

## Required outcome

- Runnable, version-pinned Isaac Lab project with scripted control, geometry, residual PPO, evaluation, and video recording.
- Full four-method comparison and explicit contact-phase-input ablation under a frozen, shared evaluation suite.
- Three training seeds for each learned method, learning curves, raw episode records, uncertainty summaries, and failure analysis.
- English final report in Markdown and PDF, figures, configuration snapshots, training/evaluation logs, and representative videos.
- Selected and final checkpoints for every trained run, including observation normalization and resume state where supported.
- GitHub source commits, an immutable experiment-source tag, and a verified final GitHub Release containing downloadable artifacts, checksums, and replay instructions.

Results must remain accessible after the remote machine disappears. Large artifacts belong in GitHub Releases, not ordinary Git history. See [RELEASE.md](docs/RELEASE.md) for packaging and fresh-download verification.

## Do not declare completion until every item is verified

- [ ] The implemented task runs from a clean checkout using committed installation instructions and official asset acquisition instructions.
- [ ] Nominal, geometry, residual, combined, and the phase ablation are implemented and checked against the scientific invariants.
- [ ] All nine learned runs and the full frozen evaluation matrix are complete, with counts reconciled and deviations disclosed.
- [ ] Raw training/validation/evaluation evidence and analysis scripts regenerate the reported metrics and figures.
- [ ] Every trained run has selected and final checkpoints, normalization/configuration metadata, and supported resume state; any checkpoint-retention limits are disclosed.
- [ ] The final English report is available as Markdown and a visually checked PDF, with accurate references and actual software/AI-assistance disclosures.
- [ ] Representative success/failure videos have method, run, case, checkpoint, and playback metadata.
- [ ] Source commits and experiment tags are pushed; all required large artifacts are uploaded to a GitHub Release with manifests and SHA-256 checksums.
- [ ] Freshly downloaded release assets pass integrity checks; downloaded policies from every learned method replay in a separate process; figures regenerate from downloaded raw data.
- [ ] The release is published and its links work. README, `STATUS.json`, and the run index reflect actual results and any remaining limitations.

The initial repository intentionally contains no trained checkpoints or experimental release. Do not create empty artifacts or mark unverified checks complete. If an external blocker remains, keep the relevant completion flags false and provide its evidence and exact missing capability.

Your final response must link the source revision/experiment tag, published release, final report, result summary, checkpoint index, and video index. State the main measured findings and any unmet requirements. A list of planned future work is not the requested final delivery.

## Scope and timeline

The owner allocated approximately one month; no exact submission date or GPU specification was supplied. Prioritize a reliable scripted handover, then geometry, learning, final comparisons, and publication. Do not expand into visual perception, real-robot deployment, multi-object generalization, multi-agent RL, or five-finger hands before the required project is complete.

The platform choice is intentional. Use compatible, pinned Isaac Sim and Isaac Lab versions, with a fixed physics backend for all experiments. The [reference list](docs/REFERENCES.md) distinguishes reusable ideas from code requiring a different simulator or robot.

## Academic provenance

The proposal is a historical document and must remain unchanged. The final report must describe actual software reuse and AI assistance accurately, retain upstream attribution, and follow any course rules supplied later. No final report template, page limit, grading rubric, or AI-use policy was provided with this handoff; do not invent those requirements or claim compliance with unseen rules.
