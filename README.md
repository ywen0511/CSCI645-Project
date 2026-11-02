# Robust Bimanual Handover

**Geometric Coordination and Residual Reinforcement Learning for Robust Bimanual Handover**  
CSCI 645 Robot Manipulation, Fall 2026 · Yan Wen

## Current status

This repository initially contains a complete execution specification and handoff utilities. **The simulator environment, controllers, trained policies, and experimental results have not yet been implemented or validated.** A remote execution agent is expected to implement, run, evaluate, document, and publish the project described here. Do not interpret proposed parameters as measured results.

Everything needed to understand the assignment is in this repository. No local computer files, previous conversation, or private notes are required. Running the work does require an appropriate remote GPU environment, access to the official simulator assets, and GitHub write access. Missing external access must be reported honestly.

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

## Commands available in this initial handoff

```bash
python3 scripts/check_handoff.py
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

## Scope and timeline

The owner allocated approximately one month; no exact submission date or GPU specification was supplied. Prioritize a reliable scripted handover, then geometry, learning, final comparisons, and publication. Do not expand into visual perception, real-robot deployment, multi-object generalization, multi-agent RL, or five-finger hands before the required project is complete.

The platform choice is intentional. Use compatible, pinned Isaac Sim and Isaac Lab versions, with a fixed physics backend for all experiments. The [reference list](docs/REFERENCES.md) distinguishes reusable ideas from code requiring a different simulator or robot.

## Academic provenance

The proposal is a historical document and must remain unchanged. The final report must describe actual software reuse and AI assistance accurately, retain upstream attribution, and follow any course rules supplied later. No final report template, page limit, grading rubric, or AI-use policy was provided with this handoff; do not invent those requirements or claim compliance with unseen rules.
